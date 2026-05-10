"""Orchestrates fetching from all sources, scoring, dedup, and storage.
Two tracks: job boards (existing) + company ATS crawling (new)."""

import asyncio
from datetime import datetime
from core.models import Job
from core.database import (
    insert_job, init_db, get_companies, update_company_crawl_status,
    cleanup_old_jobs,
)
from core.scorer import score_job
from core.profile import get_active_profile
from sources.remotive import RemotiveSource
from sources.remoteok import RemoteOKSource
from sources.arbeitnow import ArbeitnowSource
from sources.jsearch import JSearchSource
from sources.greenhouse import GreenhouseSource
from sources.lever import LeverSource
from sources.ashby import AshbySource
from sources.html_scraper import HTMLCareerSource
from config.settings import RAPIDAPI_KEY

# Days before a job not re-seen gets deleted (cleanup). Could be profile-driven
# in the future, but it's a storage-cost concern, not a user preference.
STALE_JOB_DAYS = 14


def log(msg):
    print(msg, flush=True)


def _build_job_board_sources() -> list:
    """Build the list of sources fresh each run so JSearch uses current queries."""
    sources = [
        RemotiveSource(),
        RemoteOKSource(),
        ArbeitnowSource(),
    ]
    if RAPIDAPI_KEY:
        # Queries come from the active profile (single source of truth).
        profile = get_active_profile()
        profile_queries = (profile.get("search") or {}).get("jsearch_default_queries") or []
        queries = [
            {
                "query": q["query"],
                "country": q.get("country", "IN"),
                "date_posted": q.get("date_posted", "3days"),
                **({"remote_jobs_only": "true"} if q.get("remote_jobs_only") else {}),
            }
            for q in profile_queries
            if q.get("query") and q.get("enabled", True)
        ]
        if queries:
            sources.append(JSearchSource(queries=queries))
    return sources

COMPANY_CRAWL_CONCURRENCY = 5


def _make_ats_source(company: dict):
    """Factory: return the right source class for a company's ATS."""
    platform = company.get("ats_platform", "unknown")
    if platform == "greenhouse":
        return GreenhouseSource(company)
    elif platform == "lever":
        return LeverSource(company)
    elif platform == "ashby":
        return AshbySource(company)
    elif platform == "html":
        return HTMLCareerSource(company)
    return None


async def _fetch_from_source(source) -> list[Job]:
    """Fetch jobs from a single source with error handling."""
    try:
        jobs = await source.fetch()
        log(f"  [OK] {source.name}: {len(jobs)} jobs fetched")
        return jobs
    except Exception as e:
        log(f"  [FAIL] {source.name}: {e}")
        return []


def _score_and_store(jobs: list[Job], stats: dict, profile: dict = None):
    """Score, filter, deduplicate, and store jobs. Shared by both tracks."""
    stats.setdefault("filtered_out", 0)
    profile = profile or get_active_profile()
    profile_id = profile.get("_id")
    min_store = int((profile.get("scoring") or {}).get("min_score_to_store", 25))

    for job in jobs:
        result = score_job(job.title, job.description, job.location, profile=profile)

        # Filter: drop irrelevant jobs before storing (saves DB space)
        if result["score"] < min_store:
            stats["filtered_out"] += 1
            continue

        job.relevance_score = result["score"]
        job.experience_level = result["experience_level"]
        job.india_friendly = result["india_friendly"]
        job.location_note = result["location_note"]

        existing_tech = set(t.strip() for t in job.tech_stack.split(",") if t.strip())
        existing_tech.update(result["tech_stack"])
        job.tech_stack = ", ".join(sorted(existing_tech))

        if not job.company_domain:
            job.company_domain = job.extract_domain()

        job_dict = job.model_dump()
        job_dict["id"] = job.fingerprint
        job_dict["discovered_at"] = datetime.utcnow().isoformat()
        job_dict["scored_profile_id"] = profile_id

        result_status = insert_job(job_dict)
        if result_status == "new":
            stats["new"] += 1
        else:
            stats["updated"] = stats.get("updated", 0) + 1


async def run_company_crawl(company_ids: list[str] = None) -> dict:
    """Track B: crawl jobs from companies in the DB."""
    init_db()
    log("Starting company crawl...")
    stats = {"fetched": 0, "new": 0, "updated": 0, "filtered_out": 0, "sources": {},
             "companies_crawled": 0, "companies_failed": 0}

    companies = get_companies(crawl_status="active")
    if company_ids:
        companies = [c for c in companies if c["id"] in company_ids]

    if not companies:
        log("  No active companies to crawl. Seed first with /api/companies/seed")
        return stats

    log(f"  Crawling {len(companies)} companies...")
    semaphore = asyncio.Semaphore(COMPANY_CRAWL_CONCURRENCY)

    async def crawl_one(company: dict) -> list[Job]:
        source = _make_ats_source(company)
        if not source:
            return []
        async with semaphore:
            try:
                jobs = await source.fetch()
                update_company_crawl_status(
                    company["id"], "active", datetime.utcnow().isoformat()
                )
                log(f"  [OK] {company['name']} ({company['ats_platform']}): {len(jobs)} jobs")
                stats["companies_crawled"] += 1
                stats["sources"][f"{company['ats_platform']}:{company['ats_slug']}"] = len(jobs)
                return jobs
            except Exception as e:
                update_company_crawl_status(
                    company["id"], "failed", datetime.utcnow().isoformat()
                )
                log(f"  [FAIL] {company['name']}: {e}")
                stats["companies_failed"] += 1
                return []

    tasks = [crawl_one(c) for c in companies]
    results = await asyncio.gather(*tasks)

    all_jobs = [job for batch in results for job in batch]
    stats["fetched"] = len(all_jobs)

    log(f"  Total from companies: {len(all_jobs)}")
    profile = get_active_profile()
    _score_and_store(all_jobs, stats, profile=profile)

    log(f"  Companies crawled: {stats['companies_crawled']}")
    log(f"  Companies failed: {stats['companies_failed']}")
    log(f"  New: {stats['new']} | Updated: {stats.get('updated', 0)} | Filtered out: {stats.get('filtered_out', 0)}")
    return stats


async def run_job_boards() -> dict:
    """Track A: fetch from existing job boards."""
    stats = {"fetched": 0, "new": 0, "updated": 0, "filtered_out": 0, "sources": {}}

    sources = _build_job_board_sources()
    tasks = [_fetch_from_source(src) for src in sources]
    results = await asyncio.gather(*tasks)

    all_jobs: list[Job] = []
    for source, jobs in zip(sources, results):
        stats["sources"][source.name] = len(jobs)
        all_jobs.extend(jobs)

    stats["fetched"] = len(all_jobs)
    profile = get_active_profile()
    _score_and_store(all_jobs, stats, profile=profile)
    return stats


async def run_collection(include_companies: bool = True) -> dict:
    """Run full collection: job boards + company crawl."""
    init_db()
    log("=" * 50)
    log("Starting full collection...")

    # Track A: job boards
    log("\n--- Job Boards ---")
    board_stats = await run_job_boards()

    # Track B: company crawl
    company_stats = {"fetched": 0, "new": 0, "updated": 0, "filtered_out": 0,
                     "companies_crawled": 0, "companies_failed": 0}
    if include_companies:
        log("\n--- Company Crawl ---")
        company_stats = await run_company_crawl()

    # Cleanup: delete jobs not re-seen in last N days
    log(f"\n--- Cleanup (jobs older than {STALE_JOB_DAYS} days) ---")
    deleted = cleanup_old_jobs(days=STALE_JOB_DAYS)
    log(f"  Deleted {deleted} stale jobs")

    # Merge stats
    total = {
        "fetched": board_stats["fetched"] + company_stats["fetched"],
        "new": board_stats["new"] + company_stats["new"],
        "updated": board_stats.get("updated", 0) + company_stats.get("updated", 0),
        "filtered_out": board_stats.get("filtered_out", 0) + company_stats.get("filtered_out", 0),
        "deleted_stale": deleted,
        "board_sources": board_stats["sources"],
        "companies_crawled": company_stats.get("companies_crawled", 0),
        "companies_failed": company_stats.get("companies_failed", 0),
    }

    log(f"\n--- Summary ---")
    log(f"  Total fetched: {total['fetched']}")
    log(f"  New: {total['new']} | Updated (already existed): {total['updated']}")
    log(f"  Filtered out (low score): {total['filtered_out']}")
    log(f"  Deleted (stale): {total['deleted_stale']}")
    log("Collection complete!")
    log("=" * 50)
    return total
