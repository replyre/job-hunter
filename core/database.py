import sqlite3
from typing import Optional
from config.settings import DB_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_connection()

    # Jobs table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT DEFAULT 'Remote',
            description TEXT DEFAULT '',
            url TEXT DEFAULT '',
            source TEXT DEFAULT '',
            posted_date TEXT,
            discovered_at TEXT NOT NULL,
            tech_stack TEXT DEFAULT '',
            experience_level TEXT DEFAULT '',
            relevance_score INTEGER DEFAULT 0,
            status TEXT DEFAULT 'new',
            company_domain TEXT DEFAULT '',
            salary TEXT DEFAULT '',
            job_type TEXT DEFAULT '',
            india_friendly TEXT DEFAULT 'unknown',
            location_note TEXT DEFAULT ''
        )
    """)
    # Migration for existing DBs
    for col, default in [("india_friendly", "'unknown'"), ("location_note", "''"), ("last_seen", "''")]:
        try:
            conn.execute(f"ALTER TABLE jobs ADD COLUMN {col} TEXT DEFAULT {default}")
        except sqlite3.OperationalError:
            pass
    try:
        conn.execute("ALTER TABLE jobs ADD COLUMN mark_for_email INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE jobs ADD COLUMN scored_profile_id INTEGER DEFAULT NULL")
    except sqlite3.OperationalError:
        pass

    # Companies table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            domain TEXT DEFAULT '',
            careers_url TEXT DEFAULT '',
            ats_platform TEXT DEFAULT 'unknown',
            ats_slug TEXT DEFAULT '',
            founded_year INTEGER DEFAULT 0,
            employee_count TEXT DEFAULT '',
            tags TEXT DEFAULT '',
            india_friendly TEXT DEFAULT 'unknown',
            last_crawled TEXT DEFAULT '',
            crawl_status TEXT DEFAULT 'active',
            notes TEXT DEFAULT ''
        )
    """)

    # Outreach table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS outreach (
            id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL,
            job_title TEXT,
            company TEXT,
            company_domain TEXT,
            contact_name TEXT,
            contact_position TEXT,
            contact_linkedin TEXT,
            dm_short TEXT,
            dm_long TEXT,
            status TEXT DEFAULT 'pending',
            messaged_at TEXT DEFAULT '',
            replied_at TEXT DEFAULT '',
            followed_up_at TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            notes TEXT DEFAULT '',
            emailed_at TEXT DEFAULT ''
        )
    """)
    # Migration
    try:
        conn.execute("ALTER TABLE outreach ADD COLUMN emailed_at TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE outreach ADD COLUMN profile_id INTEGER DEFAULT NULL")
    except sqlite3.OperationalError:
        pass

    # Email log table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS email_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sent_at TEXT NOT NULL,
            recipient TEXT NOT NULL,
            subject TEXT,
            items_count INTEGER DEFAULT 0,
            outreach_ids TEXT,
            status TEXT DEFAULT 'sent',
            error TEXT DEFAULT ''
        )
    """)

    # API usage tracking
    conn.execute("""
        CREATE TABLE IF NOT EXISTS api_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_name TEXT NOT NULL,
            called_at TEXT NOT NULL,
            success INTEGER DEFAULT 1,
            notes TEXT DEFAULT ''
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_api_usage_name ON api_usage(api_name, called_at)")

    # Search queries (configurable JSearch queries)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS search_queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            country TEXT DEFAULT 'IN',
            date_posted TEXT DEFAULT '3days',
            remote_jobs_only INTEGER DEFAULT 0,
            enabled INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)

    # Seed default queries only if table is empty
    count = conn.execute("SELECT COUNT(*) FROM search_queries").fetchone()[0]
    if count == 0:
        from datetime import datetime as _dt
        ts = _dt.utcnow().isoformat()
        defaults = [
            ("python django backend developer", "IN", "3days", 0),
            ("python backend engineer", "IN", "3days", 0),
            ("django developer", "IN", "3days", 0),
            ("fastapi developer", "IN", "week", 0),
            ("python backend remote", "IN", "week", 1),
            ("backend engineer python", "US", "week", 1),
        ]
        for q in defaults:
            conn.execute(
                "INSERT INTO search_queries (query, country, date_posted, remote_jobs_only, enabled, created_at) VALUES (?, ?, ?, ?, 1, ?)",
                (*q, ts),
            )

    # Profiles (per-user search/scoring/outreach config)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT DEFAULT '',
            config_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            source TEXT DEFAULT 'custom'
        )
    """)

    # Generic app-wide settings (currently holds active_profile_id)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # Indexes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_relevance ON jobs(relevance_score DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_outreach_status ON outreach(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_outreach_job ON outreach(job_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_outreach_created ON outreach(created_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_source ON jobs(source)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON jobs(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_discovered ON jobs(discovered_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_india ON jobs(india_friendly)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_company_domain ON jobs(company_domain)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_company_ats ON companies(ats_platform)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_company_status ON companies(crawl_status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_profiles_name ON profiles(name)")
    conn.commit()
    conn.close()

    # First-run seed: if no profiles exist, create "Backend Python (legacy)"
    # from current settings.py constants and set it active. Idempotent.
    try:
        from core.profile import ensure_first_run_seed
        ensure_first_run_seed()
    except Exception as e:
        # Don't block server startup on a seed failure — log and continue.
        print(f"[init_db] profile seed skipped: {e}", flush=True)


# ── Jobs CRUD ──────────────────────────────────────────────────

def insert_job(job_dict: dict) -> str:
    """Upsert a job.
    Returns 'new' if new, 'updated' if existed (last_seen refreshed).
    """
    from datetime import datetime
    conn = get_connection()
    now = datetime.utcnow().isoformat()
    job_dict["last_seen"] = now

    try:
        existing = conn.execute("SELECT id FROM jobs WHERE id = ?", (job_dict["id"],)).fetchone()
        if existing:
            # Update last_seen + refreshed timestamp; keep status/notes intact
            conn.execute("UPDATE jobs SET last_seen = ? WHERE id = ?", (now, job_dict["id"]))
            conn.commit()
            return "updated"
        job_dict.setdefault("scored_profile_id", None)
        conn.execute("""
            INSERT INTO jobs (id, title, company, location, description, url,
                            source, posted_date, discovered_at, tech_stack,
                            experience_level, relevance_score, status,
                            company_domain, salary, job_type,
                            india_friendly, location_note, last_seen,
                            scored_profile_id)
            VALUES (:id, :title, :company, :location, :description, :url,
                    :source, :posted_date, :discovered_at, :tech_stack,
                    :experience_level, :relevance_score, :status,
                    :company_domain, :salary, :job_type,
                    :india_friendly, :location_note, :last_seen,
                    :scored_profile_id)
        """, job_dict)
        conn.commit()
        return "new"
    except sqlite3.IntegrityError:
        return "updated"
    finally:
        conn.close()


def cleanup_old_jobs(days: int = 14) -> int:
    """Delete jobs not seen in N days. Returns number deleted."""
    from datetime import datetime, timedelta
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    conn = get_connection()
    # Don't delete jobs user has marked applied or for_email
    cur = conn.execute(
        """DELETE FROM jobs
           WHERE (last_seen < ? OR last_seen = '' OR last_seen IS NULL)
             AND status IN ('new', 'reviewed', 'stale')
             AND (mark_for_email = 0 OR mark_for_email IS NULL)""",
        (cutoff,),
    )
    count = cur.rowcount
    conn.commit()
    conn.close()
    return count


def toggle_mark_for_email(job_id: str) -> bool:
    """Toggle mark_for_email flag. Returns new state."""
    conn = get_connection()
    row = conn.execute("SELECT mark_for_email FROM jobs WHERE id = ?", (job_id,)).fetchone()
    new_state = 0 if (row and row[0]) else 1
    conn.execute("UPDATE jobs SET mark_for_email = ? WHERE id = ?", (new_state, job_id))
    conn.commit()
    conn.close()
    return bool(new_state)


def get_marked_jobs(limit: int = 50) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM jobs WHERE mark_for_email = 1 ORDER BY relevance_score DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_jobs(
    source: Optional[str] = None,
    status: Optional[str] = None,
    min_score: int = 0,
    search: Optional[str] = None,
    location: Optional[str] = None,
    tech: Optional[str] = None,
    india_friendly: Optional[str] = None,
    company_domain: Optional[str] = None,
    seen_after: Optional[str] = None,     # ISO timestamp; only jobs refreshed at/after this
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    conn = get_connection()
    query = "SELECT * FROM jobs WHERE relevance_score >= ?"
    params: list = [min_score]

    if source:
        query += " AND source LIKE ?"
        params.append(f"%{source}%")
    if status:
        query += " AND status = ?"
        params.append(status)
    if search:
        query += " AND (title LIKE ? OR company LIKE ? OR description LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s, s])
    if location:
        query += " AND location LIKE ?"
        params.append(f"%{location}%")
    if tech:
        query += " AND tech_stack LIKE ?"
        params.append(f"%{tech}%")
    if india_friendly:
        if india_friendly == "yes":
            query += " AND india_friendly = 'yes'"
        elif india_friendly == "no":
            query += " AND india_friendly = 'no'"
        elif india_friendly == "maybe":
            query += " AND india_friendly IN ('yes', 'maybe')"
    if company_domain:
        query += " AND company_domain = ?"
        params.append(company_domain)
    if seen_after:
        query += " AND last_seen >= ?"
        params.append(seen_after)

    query += " ORDER BY relevance_score DESC, discovered_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_job_by_id(job_id: str) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_job_status(job_id: str, status: str):
    conn = get_connection()
    conn.execute("UPDATE jobs SET status = ? WHERE id = ?", (status, job_id))
    conn.commit()
    conn.close()


def get_stats() -> dict:
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    by_source = conn.execute(
        "SELECT source, COUNT(*) as count FROM jobs GROUP BY source"
    ).fetchall()
    by_status = conn.execute(
        "SELECT status, COUNT(*) as count FROM jobs GROUP BY status"
    ).fetchall()
    by_india = conn.execute(
        "SELECT india_friendly, COUNT(*) as count FROM jobs GROUP BY india_friendly"
    ).fetchall()
    avg_score = conn.execute(
        "SELECT AVG(relevance_score) FROM jobs WHERE relevance_score > 0"
    ).fetchone()[0]
    conn.close()
    return {
        "total": total,
        "by_source": {row["source"]: row["count"] for row in by_source},
        "by_status": {row["status"]: row["count"] for row in by_status},
        "by_india": {row["india_friendly"]: row["count"] for row in by_india},
        "avg_score": round(avg_score, 1) if avg_score else 0,
    }


def get_sources() -> list[str]:
    conn = get_connection()
    rows = conn.execute("SELECT DISTINCT source FROM jobs ORDER BY source").fetchall()
    conn.close()
    return [row["source"] for row in rows]


# ── Companies CRUD ─────────────────────────────────────────────

def upsert_company(company_dict: dict) -> bool:
    conn = get_connection()
    try:
        conn.execute("""
            INSERT OR REPLACE INTO companies
                (id, name, domain, careers_url, ats_platform, ats_slug,
                 founded_year, employee_count, tags, india_friendly,
                 last_crawled, crawl_status, notes)
            VALUES (:id, :name, :domain, :careers_url, :ats_platform, :ats_slug,
                    :founded_year, :employee_count, :tags, :india_friendly,
                    :last_crawled, :crawl_status, :notes)
        """, company_dict)
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def get_companies(
    ats_platform: Optional[str] = None,
    crawl_status: Optional[str] = None,
    india_friendly: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
) -> list[dict]:
    conn = get_connection()
    query = "SELECT * FROM companies WHERE 1=1"
    params: list = []

    if ats_platform:
        query += " AND ats_platform = ?"
        params.append(ats_platform)
    if crawl_status:
        query += " AND crawl_status = ?"
        params.append(crawl_status)
    if india_friendly:
        query += " AND india_friendly = ?"
        params.append(india_friendly)
    if search:
        query += " AND (name LIKE ? OR domain LIKE ? OR tags LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s, s])

    query += " ORDER BY name ASC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_company_by_id(company_id: str) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM companies WHERE id = ?", (company_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_company_crawl_status(company_id: str, status: str, last_crawled: str = ""):
    conn = get_connection()
    if last_crawled:
        conn.execute(
            "UPDATE companies SET crawl_status = ?, last_crawled = ? WHERE id = ?",
            (status, last_crawled, company_id),
        )
    else:
        conn.execute(
            "UPDATE companies SET crawl_status = ? WHERE id = ?",
            (status, company_id),
        )
    conn.commit()
    conn.close()


# ── Outreach CRUD ──────────────────────────────────────────────

def insert_outreach(item: dict) -> bool:
    conn = get_connection()
    try:
        item.setdefault("profile_id", None)
        conn.execute("""
            INSERT OR REPLACE INTO outreach
                (id, job_id, job_title, company, company_domain,
                 contact_name, contact_position, contact_linkedin,
                 dm_short, dm_long, status, messaged_at, replied_at,
                 followed_up_at, created_at, notes, profile_id)
            VALUES (:id, :job_id, :job_title, :company, :company_domain,
                    :contact_name, :contact_position, :contact_linkedin,
                    :dm_short, :dm_long, :status, :messaged_at, :replied_at,
                    :followed_up_at, :created_at, :notes, :profile_id)
        """, item)
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def get_outreach(
    status: Optional[str] = None,
    search: Optional[str] = None,
    batch: Optional[str] = None,   # "new" | "old" | None
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    conn = get_connection()
    query = """
        SELECT o.*, j.url as job_url, j.relevance_score, j.tech_stack,
               j.location, j.salary, j.india_friendly
        FROM outreach o
        LEFT JOIN jobs j ON j.id = o.job_id
        WHERE 1=1
    """
    params: list = []
    if status:
        query += " AND o.status = ?"
        params.append(status)
    if search:
        query += " AND (o.company LIKE ? OR o.job_title LIKE ? OR o.contact_name LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s, s])
    if batch in ("new", "old"):
        batch_at = get_last_outreach_batch_at()
        if batch_at:
            op = ">=" if batch == "new" else "<"
            query += f" AND o.created_at {op} ?"
            params.append(batch_at)
        elif batch == "new":
            # No recorded batch yet — treat the most recent generation as "new"
            # by returning nothing until a generation actually runs.
            query += " AND 0"
    query += " ORDER BY o.created_at DESC, j.relevance_score DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_outreach_bulk(ids: list[str]) -> int:
    if not ids:
        return 0
    conn = get_connection()
    try:
        placeholders = ",".join(["?"] * len(ids))
        cur = conn.execute(
            f"DELETE FROM outreach WHERE id IN ({placeholders})", ids,
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def delete_all_outreach() -> int:
    conn = get_connection()
    try:
        cur = conn.execute("DELETE FROM outreach")
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def set_last_outreach_batch_at(ts: str) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO app_settings (key, value, updated_at) "
            "VALUES ('last_outreach_batch_at', ?, ?)",
            (ts, ts),
        )
        conn.commit()
    finally:
        conn.close()


def get_last_outreach_batch_at() -> Optional[str]:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT value FROM app_settings WHERE key = 'last_outreach_batch_at'"
        ).fetchone()
    except sqlite3.OperationalError:
        return None
    finally:
        conn.close()
    return row["value"] if row else None


def update_outreach_status(outreach_id: str, status: str, field: str = None):
    from datetime import datetime
    conn = get_connection()
    ts = datetime.utcnow().isoformat()
    if field == "messaged":
        conn.execute("UPDATE outreach SET status=?, messaged_at=? WHERE id=?", (status, ts, outreach_id))
    elif field == "replied":
        conn.execute("UPDATE outreach SET status=?, replied_at=? WHERE id=?", (status, ts, outreach_id))
    elif field == "followed_up":
        conn.execute("UPDATE outreach SET status=?, followed_up_at=? WHERE id=?", (status, ts, outreach_id))
    else:
        conn.execute("UPDATE outreach SET status=? WHERE id=?", (status, outreach_id))
    conn.commit()
    conn.close()


def update_outreach_notes(outreach_id: str, notes: str):
    conn = get_connection()
    conn.execute("UPDATE outreach SET notes = ? WHERE id = ?", (notes, outreach_id))
    conn.commit()
    conn.close()


def outreach_exists_for_job(job_id: str) -> bool:
    conn = get_connection()
    row = conn.execute("SELECT id FROM outreach WHERE job_id = ? LIMIT 1", (job_id,)).fetchone()
    conn.close()
    return row is not None


def get_outreach_stats() -> dict:
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) FROM outreach").fetchone()[0]
    by_status = conn.execute(
        "SELECT status, COUNT(*) as count FROM outreach GROUP BY status"
    ).fetchall()
    conn.close()
    return {
        "total": total,
        "by_status": {r["status"]: r["count"] for r in by_status},
    }


def get_unemailed_outreach(limit: int = 15, only_marked: bool = False) -> list[dict]:
    """Get outreach items that haven't been emailed yet.
    If only_marked=True, only returns items for jobs marked for email.
    Otherwise prefers marked jobs but falls back to highest score."""
    conn = get_connection()
    where = "(o.emailed_at = '' OR o.emailed_at IS NULL) AND o.status = 'pending'"
    if only_marked:
        where += " AND j.mark_for_email = 1"

    rows = conn.execute(f"""
        SELECT o.*, j.relevance_score, j.url AS job_url, j.description AS job_description,
               j.tech_stack, j.salary, j.location, j.posted_date, j.india_friendly,
               j.mark_for_email
        FROM outreach o
        LEFT JOIN jobs j ON j.id = o.job_id
        WHERE {where}
        ORDER BY j.mark_for_email DESC, j.relevance_score DESC, o.created_at DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_outreach_emailed(outreach_ids: list[str]):
    """Flip sent items from pending → emailed so they drop out of the
    'ready to send' queue. Items already in messaged/replied/followed_up
    keep their current status (we only update ones still 'pending')."""
    from datetime import datetime
    conn = get_connection()
    ts = datetime.utcnow().isoformat()
    for oid in outreach_ids:
        conn.execute(
            "UPDATE outreach SET emailed_at = ?, "
            "status = CASE WHEN status = 'pending' THEN 'emailed' ELSE status END "
            "WHERE id = ?",
            (ts, oid),
        )
    conn.commit()
    conn.close()


def log_email(recipient: str, subject: str, items_count: int,
              outreach_ids: list[str], status: str = "sent", error: str = ""):
    from datetime import datetime
    conn = get_connection()
    conn.execute("""
        INSERT INTO email_log (sent_at, recipient, subject, items_count, outreach_ids, status, error)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (datetime.utcnow().isoformat(), recipient, subject, items_count,
          ",".join(outreach_ids), status, error))
    conn.commit()
    conn.close()


def get_search_queries(enabled_only: bool = False) -> list[dict]:
    conn = get_connection()
    if enabled_only:
        rows = conn.execute("SELECT * FROM search_queries WHERE enabled = 1 ORDER BY id").fetchall()
    else:
        rows = conn.execute("SELECT * FROM search_queries ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_search_query(query: str, country: str = "IN", date_posted: str = "3days",
                      remote_jobs_only: bool = False) -> int:
    from datetime import datetime
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO search_queries (query, country, date_posted, remote_jobs_only, enabled, created_at) VALUES (?, ?, ?, ?, 1, ?)",
        (query, country, date_posted, 1 if remote_jobs_only else 0, datetime.utcnow().isoformat()),
    )
    qid = cur.lastrowid
    conn.commit()
    conn.close()
    return qid


def update_search_query(qid: int, query: str = None, country: str = None,
                         date_posted: str = None, remote_jobs_only: bool = None,
                         enabled: bool = None):
    conn = get_connection()
    updates = []
    params = []
    if query is not None:
        updates.append("query = ?"); params.append(query)
    if country is not None:
        updates.append("country = ?"); params.append(country)
    if date_posted is not None:
        updates.append("date_posted = ?"); params.append(date_posted)
    if remote_jobs_only is not None:
        updates.append("remote_jobs_only = ?"); params.append(1 if remote_jobs_only else 0)
    if enabled is not None:
        updates.append("enabled = ?"); params.append(1 if enabled else 0)
    if updates:
        params.append(qid)
        conn.execute(f"UPDATE search_queries SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
    conn.close()


def delete_search_query(qid: int):
    conn = get_connection()
    conn.execute("DELETE FROM search_queries WHERE id = ?", (qid,))
    conn.commit()
    conn.close()


def log_api_call(api_name: str, success: bool = True, notes: str = ""):
    from datetime import datetime
    conn = get_connection()
    conn.execute(
        "INSERT INTO api_usage (api_name, called_at, success, notes) VALUES (?, ?, ?, ?)",
        (api_name, datetime.utcnow().isoformat(), 1 if success else 0, notes),
    )
    conn.commit()
    conn.close()


def get_api_usage(api_name: str) -> dict:
    """Returns usage stats for a given API — monthly count."""
    from datetime import datetime
    conn = get_connection()
    # Month start ISO string
    now = datetime.utcnow()
    month_start = datetime(now.year, now.month, 1).isoformat()
    month = conn.execute(
        "SELECT COUNT(*) FROM api_usage WHERE api_name=? AND called_at >= ?",
        (api_name, month_start),
    ).fetchone()[0]
    # Today
    today_start = datetime(now.year, now.month, now.day).isoformat()
    today = conn.execute(
        "SELECT COUNT(*) FROM api_usage WHERE api_name=? AND called_at >= ?",
        (api_name, today_start),
    ).fetchone()[0]
    total = conn.execute(
        "SELECT COUNT(*) FROM api_usage WHERE api_name=?", (api_name,),
    ).fetchone()[0]
    conn.close()
    return {"month": month, "today": today, "total": total}


def get_email_logs(limit: int = 30) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM email_log ORDER BY sent_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_company_stats() -> dict:
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
    by_platform = conn.execute(
        "SELECT ats_platform, COUNT(*) as count FROM companies GROUP BY ats_platform"
    ).fetchall()
    by_status = conn.execute(
        "SELECT crawl_status, COUNT(*) as count FROM companies GROUP BY crawl_status"
    ).fetchall()
    by_india = conn.execute(
        "SELECT india_friendly, COUNT(*) as count FROM companies GROUP BY india_friendly"
    ).fetchall()
    conn.close()
    return {
        "total": total,
        "by_platform": {row["ats_platform"]: row["count"] for row in by_platform},
        "by_status": {row["crawl_status"]: row["count"] for row in by_status},
        "by_india": {row["india_friendly"]: row["count"] for row in by_india},
    }
