"""Bulk company discovery from multiple public sources.
Discovers 500+ companies and auto-detects their ATS platform."""

import asyncio
import httpx
from core.models import Company
from core.database import upsert_company, get_company_by_id


def log(msg):
    print(msg, flush=True)


# ── Source 1: YCombinator API ──────────────────────────────────
# Public paginated API with company data

async def discover_from_yc(min_team_size: int = 10, max_pages: int = 250) -> list[dict]:
    """Fetch companies from YC directory. Returns raw company dicts."""
    companies = []
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        for page in range(1, max_pages + 1):
            try:
                resp = await client.get(
                    "https://api.ycombinator.com/v0.1/companies",
                    params={"page": page, "per_page": 25},
                )
                if resp.status_code != 200:
                    break
                data = resp.json()
                batch = data.get("companies", [])
                if not batch:
                    break

                for c in batch:
                    team = c.get("teamSize") or 0
                    if team < min_team_size:
                        continue
                    website = c.get("website", "") or ""
                    if not website:
                        continue
                    domain = website.replace("https://", "").replace("http://", "").replace("www.", "").strip("/")

                    regions = c.get("regions", []) or []
                    india_friendly = "unknown"
                    if any("india" in r.lower() for r in regions):
                        india_friendly = "yes"
                    elif any(r.lower() in ["remote", "global", "worldwide"] for r in regions):
                        india_friendly = "maybe"

                    companies.append({
                        "name": c.get("name", ""),
                        "domain": domain,
                        "employee_count": str(team) + "+",
                        "founded_year": int(c.get("batch", "W20")[1:]) + 2000 if c.get("batch") else 0,
                        "tags": ",".join(c.get("industries", []) or []),
                        "india_friendly": india_friendly,
                        "notes": f"YC {c.get('batch', '')} | {c.get('oneLiner', '')}",
                    })

                total_pages = data.get("totalPages", 0)
                if page >= total_pages:
                    break
                log(f"  YC page {page}/{total_pages}: {len(batch)} companies (kept {len([x for x in batch if (x.get('teamSize') or 0) >= min_team_size])})")
            except Exception as e:
                log(f"  YC page {page} failed: {e}")
                break

    return companies


# ── Source 2: RemoteInTech GitHub repo ─────────────────────────
# 700+ remote-friendly companies as markdown files

async def discover_from_remoteintech() -> list[dict]:
    """Fetch company names from remoteintech/remote-jobs GitHub repo."""
    companies = []
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        resp = await client.get(
            "https://api.github.com/repos/remoteintech/remote-jobs/git/trees/main",
            params={"recursive": "1"},
        )
        if resp.status_code != 200:
            log(f"  RemoteInTech failed: {resp.status_code}")
            return []

        data = resp.json()
        for item in data.get("tree", []):
            path = item.get("path", "")
            if path.startswith("src/companies/") and path.endswith(".md"):
                slug = path.replace("src/companies/", "").replace(".md", "")
                name = slug.replace("-", " ").title()
                companies.append({
                    "name": name,
                    "domain": "",
                    "tags": "remote-friendly",
                    "india_friendly": "maybe",
                    "notes": "From remoteintech/remote-jobs",
                })

    log(f"  RemoteInTech: {len(companies)} companies")
    return companies


# ── Source 3: WeWorkRemotely ───────────────────────────────────

async def discover_from_wwr() -> list[dict]:
    """Scrape company list from WeWorkRemotely."""
    from bs4 import BeautifulSoup
    companies = []
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        resp = await client.get("https://weworkremotely.com/remote-companies")
        if resp.status_code != 200:
            log(f"  WWR failed: {resp.status_code}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("/company/"):
                slug = href.split("/company/")[1].strip("/")
                if slug:
                    name = slug.replace("-", " ").title()
                    companies.append({
                        "name": name,
                        "domain": "",
                        "tags": "remote-friendly",
                        "india_friendly": "maybe",
                        "notes": "From WeWorkRemotely",
                    })

    # Deduplicate
    seen = set()
    unique = []
    for c in companies:
        key = c["name"].lower()
        if key not in seen:
            seen.add(key)
            unique.append(c)

    log(f"  WeWorkRemotely: {len(unique)} companies")
    return unique


# ── ATS Auto-Detection (batch) ────────────────────────────────

async def batch_detect_ats(companies: list[dict], concurrency: int = 10) -> list[dict]:
    """For each company, try to detect Greenhouse/Lever/Ashby slug."""
    semaphore = asyncio.Semaphore(concurrency)
    detected = 0

    async def detect_one(company: dict) -> dict:
        nonlocal detected
        domain = company.get("domain", "")
        name = company.get("name", "")

        # Generate possible slugs
        slugs = set()
        if domain:
            slugs.add(domain.split(".")[0])
        name_slug = Company.make_id(name)
        slugs.add(name_slug)
        slugs.add(name_slug.replace("-", ""))
        slugs.discard("")

        async with semaphore:
            async with httpx.AsyncClient(timeout=8) as client:
                for slug in slugs:
                    # Try Greenhouse
                    try:
                        resp = await client.get(
                            f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            if "jobs" in data:
                                company["ats_platform"] = "greenhouse"
                                company["ats_slug"] = slug
                                detected += 1
                                return company
                    except Exception:
                        pass

                    # Try Lever
                    try:
                        resp = await client.get(
                            f"https://api.lever.co/v0/postings/{slug}",
                            params={"mode": "json"},
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            if isinstance(data, list):
                                company["ats_platform"] = "lever"
                                company["ats_slug"] = slug
                                detected += 1
                                return company
                    except Exception:
                        pass

                    # Try Ashby
                    try:
                        resp = await client.get(
                            f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
                        )
                        if resp.status_code == 200:
                            try:
                                data = resp.json()
                                if "jobs" in data:
                                    company["ats_platform"] = "ashby"
                                    company["ats_slug"] = slug
                                    detected += 1
                                    return company
                            except Exception:
                                pass
                    except Exception:
                        pass

        company["ats_platform"] = "unknown"
        company["ats_slug"] = ""
        return company

    log(f"  Detecting ATS for {len(companies)} companies (this takes a while)...")
    tasks = [detect_one(c) for c in companies]

    # Process in chunks to show progress
    results = []
    chunk_size = 50
    for i in range(0, len(tasks), chunk_size):
        chunk = tasks[i:i + chunk_size]
        chunk_results = await asyncio.gather(*chunk)
        results.extend(chunk_results)
        log(f"  Progress: {len(results)}/{len(tasks)} checked, {detected} ATS detected")

    return results


# ── Main Discovery Pipeline ───────────────────────────────────

async def run_bulk_discovery(
    sources: list[str] = None,
    detect_ats: bool = True,
    min_team_size: int = 10,
) -> dict:
    """
    Discover companies from multiple sources, detect their ATS, and store.

    Args:
        sources: list of source names to use. Default: all.
            Options: 'yc', 'remoteintech', 'wwr'
        detect_ats: whether to auto-detect ATS platform
        min_team_size: minimum team size for YC filter

    Returns: stats dict
    """
    if sources is None:
        sources = ["yc", "remoteintech", "wwr"]

    stats = {"discovered": 0, "new": 0, "ats_detected": 0, "by_source": {}}

    all_companies = []

    # Fetch from sources
    log("=== Bulk Company Discovery ===")

    if "yc" in sources:
        log("\n--- YCombinator ---")
        yc_companies = await discover_from_yc(min_team_size=min_team_size)
        stats["by_source"]["yc"] = len(yc_companies)
        all_companies.extend(yc_companies)

    if "remoteintech" in sources:
        log("\n--- RemoteInTech ---")
        rit_companies = await discover_from_remoteintech()
        stats["by_source"]["remoteintech"] = len(rit_companies)
        all_companies.extend(rit_companies)

    if "wwr" in sources:
        log("\n--- WeWorkRemotely ---")
        wwr_companies = await discover_from_wwr()
        stats["by_source"]["wwr"] = len(wwr_companies)
        all_companies.extend(wwr_companies)

    # Deduplicate by name
    seen_names = set()
    unique = []
    for c in all_companies:
        key = c["name"].lower().strip()
        if key not in seen_names and len(key) > 1:
            seen_names.add(key)
            unique.append(c)

    stats["discovered"] = len(unique)
    log(f"\nTotal unique companies: {len(unique)}")

    # Skip companies we already have
    new_companies = []
    for c in unique:
        company_id = Company.make_id(c["name"])
        if not get_company_by_id(company_id):
            new_companies.append(c)

    log(f"New companies (not in DB yet): {len(new_companies)}")

    if not new_companies:
        log("No new companies to add.")
        return stats

    # Auto-detect ATS
    if detect_ats and new_companies:
        log("\n--- ATS Detection ---")
        new_companies = await batch_detect_ats(new_companies)
        ats_count = sum(1 for c in new_companies if c.get("ats_platform", "unknown") != "unknown")
        stats["ats_detected"] = ats_count
        log(f"ATS detected for {ats_count}/{len(new_companies)} companies")

    # Store in database
    log("\n--- Storing ---")
    for c in new_companies:
        company_id = Company.make_id(c["name"])
        entry = {
            "id": company_id,
            "name": c["name"],
            "domain": c.get("domain", ""),
            "careers_url": c.get("careers_url", ""),
            "ats_platform": c.get("ats_platform", "unknown"),
            "ats_slug": c.get("ats_slug", ""),
            "founded_year": c.get("founded_year", 0),
            "employee_count": c.get("employee_count", ""),
            "tags": c.get("tags", ""),
            "india_friendly": c.get("india_friendly", "unknown"),
            "last_crawled": "",
            "crawl_status": "active" if c.get("ats_platform", "unknown") != "unknown" else "paused",
            "notes": c.get("notes", ""),
        }
        if upsert_company(entry):
            stats["new"] += 1

    log(f"\nStored {stats['new']} new companies")
    log(f"ATS detected: {stats['ats_detected']} (these are crawlable)")
    log("=== Discovery Complete ===")
    return stats
