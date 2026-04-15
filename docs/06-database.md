# Database Schema

SQLite database at `jobs.db` in project root.

---

## `jobs` table

Stores all collected job postings.

| Column | Type | Default | Description |
|---|---|---|---|
| `id` | TEXT PRIMARY KEY | — | MD5 fingerprint: `hash(company\|title\|location)` |
| `title` | TEXT NOT NULL | — | Job title |
| `company` | TEXT NOT NULL | — | Company name |
| `location` | TEXT | 'Remote' | Location string |
| `description` | TEXT | '' | Full job description (can be HTML) |
| `url` | TEXT | '' | Apply URL |
| `source` | TEXT | '' | e.g., `jsearch`, `greenhouse:stripe`, `remotive` |
| `posted_date` | TEXT | NULL | ISO date when company posted |
| `discovered_at` | TEXT NOT NULL | — | ISO date when we first saw it |
| `last_seen` | TEXT | '' | ISO date of most recent collection run that saw it |
| `tech_stack` | TEXT | '' | Comma-separated: `python, django, postgres` |
| `experience_level` | TEXT | '' | junior / mid / senior |
| `relevance_score` | INTEGER | 0 | 0-100 from scorer |
| `status` | TEXT | 'new' | new / reviewed / applied / stale |
| `company_domain` | TEXT | '' | e.g., `stripe.com` |
| `salary` | TEXT | '' | Free text (format varies by source) |
| `job_type` | TEXT | '' | full-time / contract / etc. |
| `india_friendly` | TEXT | 'unknown' | yes / no / maybe / unknown |
| `location_note` | TEXT | '' | Why we classified it as india_friendly |
| `mark_for_email` | INTEGER | 0 | 1 = prioritize in daily digest |

**Indexes:**
- `idx_relevance` on `relevance_score DESC`
- `idx_source` on `source`
- `idx_status` on `status`
- `idx_discovered` on `discovered_at DESC`
- `idx_india` on `india_friendly`
- `idx_company_domain` on `company_domain`

---

## `companies` table

3,500+ companies used for ATS crawling (Track B).

| Column | Type | Default | Description |
|---|---|---|---|
| `id` | TEXT PRIMARY KEY | — | Slugified company name |
| `name` | TEXT NOT NULL | — | Company name |
| `domain` | TEXT | '' | e.g., `stripe.com` |
| `careers_url` | TEXT | '' | Custom careers page (for HTML scraper) |
| `ats_platform` | TEXT | 'unknown' | greenhouse / lever / ashby / html / unknown |
| `ats_slug` | TEXT | '' | Platform-specific slug (e.g., `stripe`) |
| `founded_year` | INTEGER | 0 | Year founded |
| `employee_count` | TEXT | '' | e.g., `500+`, `1000+` |
| `tags` | TEXT | '' | Comma-separated: `saas,fintech,india-hq` |
| `india_friendly` | TEXT | 'unknown' | yes / no / maybe / unknown |
| `last_crawled` | TEXT | '' | ISO date of last successful crawl |
| `crawl_status` | TEXT | 'active' | active / paused / failed |
| `notes` | TEXT | '' | Free text |

**Indexes:**
- `idx_company_ats` on `ats_platform`
- `idx_company_status` on `crawl_status`

---

## `outreach` table

Generated outreach items with status tracking.

| Column | Type | Default | Description |
|---|---|---|---|
| `id` | TEXT PRIMARY KEY | — | MD5 of `{job_id}\|{variant}` |
| `job_id` | TEXT NOT NULL | — | FK to jobs.id |
| `job_title` | TEXT | '' | Snapshotted from job |
| `company` | TEXT | '' | Snapshotted from job |
| `company_domain` | TEXT | '' | From job |
| `contact_name` | TEXT | '' | Placeholder `[Search LinkedIn]` |
| `contact_position` | TEXT | '' | Generic "Eng Manager / Tech Lead / ..." |
| `contact_linkedin` | TEXT | '' | Primary search URL (Engineering Manager) |
| `dm_short` | TEXT | '' | Short DM for connection request (<300 chars) |
| `dm_long` | TEXT | '' | Long DM for direct message after connecting |
| `status` | TEXT | 'pending' | pending / messaged / replied / followed_up |
| `messaged_at` | TEXT | '' | Timestamp when marked messaged |
| `replied_at` | TEXT | '' | Timestamp when marked replied |
| `followed_up_at` | TEXT | '' | Timestamp when marked followed up |
| `created_at` | TEXT NOT NULL | — | ISO date |
| `notes` | TEXT | '' | JSON array of all 7 LinkedIn search URLs |
| `emailed_at` | TEXT | '' | ISO date when included in daily email |

**Indexes:**
- `idx_outreach_status` on `status`
- `idx_outreach_job` on `job_id`
- `idx_outreach_created` on `created_at DESC`

---

## `search_queries` table

User-configurable JSearch queries.

| Column | Type | Default | Description |
|---|---|---|---|
| `id` | INTEGER PRIMARY KEY AUTOINCREMENT | — | |
| `query` | TEXT NOT NULL | — | e.g., `python django backend developer` |
| `country` | TEXT | 'IN' | 2-letter code |
| `date_posted` | TEXT | '3days' | today / 3days / week / month / all |
| `remote_jobs_only` | INTEGER | 0 | 1 = only remote |
| `enabled` | INTEGER | 1 | 0 = disabled (skipped in collection) |
| `created_at` | TEXT NOT NULL | — | |

Seeded with 6 default queries on first run.

---

## `email_log` table

History of sent daily digest emails.

| Column | Type | Default | Description |
|---|---|---|---|
| `id` | INTEGER PRIMARY KEY AUTOINCREMENT | — | |
| `sent_at` | TEXT NOT NULL | — | ISO timestamp |
| `recipient` | TEXT NOT NULL | — | Email address |
| `subject` | TEXT | '' | |
| `items_count` | INTEGER | 0 | Number of jobs included |
| `outreach_ids` | TEXT | '' | Comma-separated IDs |
| `status` | TEXT | 'sent' | sent / failed |
| `error` | TEXT | '' | Error message if failed |

---

## `api_usage` table

Tracks external API call counts (JSearch, Hunter).

| Column | Type | Default | Description |
|---|---|---|---|
| `id` | INTEGER PRIMARY KEY AUTOINCREMENT | — | |
| `api_name` | TEXT NOT NULL | — | jsearch / hunter |
| `called_at` | TEXT NOT NULL | — | ISO timestamp |
| `success` | INTEGER | 1 | 1 = success, 0 = failure |
| `notes` | TEXT | '' | Usually the query used |

**Indexes:**
- `idx_api_usage_name` on `(api_name, called_at)`

---

## Dedup Logic

Each job gets an MD5 fingerprint:
```python
hashlib.md5(f"{company.lower()}|{title.lower()}|{location.lower()}".encode()).hexdigest()
```

**On collection:**
- If fingerprint **doesn't exist** → INSERT + `discovered_at = now`, `last_seen = now`
- If fingerprint **exists** → UPDATE `last_seen = now` only

**On cleanup** (every collection run):
- Delete jobs where `last_seen < 14 days ago`
- **Protected**: jobs with `status = 'applied'` or `mark_for_email = 1` are never deleted

---

## Data Retention

| Data | Kept |
|---|---|
| Active jobs | Forever (while still being posted) |
| Stale jobs | 14 days after last_seen, then deleted |
| Applied jobs | Forever (protected) |
| Marked jobs | Forever (protected) |
| Outreach items | Forever (independent of job lifecycle) |
| Email log | Forever |
| API usage | Forever (for monthly stats) |

---

## Backup

SQLite file is `jobs.db`. To back up:
```bash
cp jobs.db jobs.db.backup-$(date +%Y%m%d)
```

Or export specific data:
```bash
sqlite3 jobs.db ".dump jobs" > jobs-backup.sql
```
