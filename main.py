import uvicorn
from fastapi import FastAPI, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from pydantic import BaseModel
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from core.database import (
    init_db, get_jobs, get_job_by_id, update_job_status, get_stats, get_sources,
    upsert_company, get_companies, get_company_by_id,
    update_company_crawl_status, get_company_stats,
    insert_outreach, get_outreach, update_outreach_status, update_outreach_notes,
    outreach_exists_for_job, get_outreach_stats,
    get_search_queries, add_search_query, update_search_query, delete_search_query,
    toggle_mark_for_email, get_marked_jobs,
)
from core.collector import run_collection, run_company_crawl
from core.sheets import export_to_sheet
from core.emailer import run_daily_pipeline, send_daily_digest
from config.settings import (
    HOST, PORT, GOOGLE_SHEETS_CREDS, GOOGLE_SHEET_ID, HUNTER_API_KEY,
    DAILY_EMAIL_HOUR, DAILY_EMAIL_TIMEZONE, SENDER_EMAIL,
)

app = FastAPI(title="Job Scraper", version="2.0.0")
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


scheduler = AsyncIOScheduler(timezone=DAILY_EMAIL_TIMEZONE)


@app.on_event("startup")
async def startup():
    init_db()

    # Schedule daily digest at configured hour IST
    if SENDER_EMAIL:
        scheduler.add_job(
            run_daily_pipeline,
            CronTrigger(hour=DAILY_EMAIL_HOUR, minute=0),
            id="daily_digest",
            replace_existing=True,
            kwargs={"send": True},
        )
        scheduler.start()
        print(f"Scheduled daily digest at {DAILY_EMAIL_HOUR}:00 IST", flush=True)
    else:
        print("SENDER_EMAIL not set — daily digest disabled", flush=True)


@app.on_event("shutdown")
async def shutdown():
    if scheduler.running:
        scheduler.shutdown()


# ── Jobs API ───────────────────────────────────────────────────

@app.get("/api/jobs")
async def api_get_jobs(
    source: Optional[str] = None,
    status: Optional[str] = None,
    min_score: int = Query(0, ge=0, le=100),
    search: Optional[str] = None,
    location: Optional[str] = None,
    tech: Optional[str] = None,
    india_friendly: Optional[str] = None,
    company_domain: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    jobs = get_jobs(
        source=source, status=status, min_score=min_score,
        search=search, location=location, tech=tech,
        india_friendly=india_friendly, company_domain=company_domain,
        limit=limit, offset=offset,
    )
    return {"jobs": jobs, "count": len(jobs)}


@app.get("/api/jobs/{job_id}")
async def api_get_job(job_id: str):
    job = get_job_by_id(job_id)
    if not job:
        return {"error": "Job not found"}
    return job


@app.patch("/api/jobs/{job_id}/status")
async def api_update_status(job_id: str, status: str = Query(...)):
    update_job_status(job_id, status)
    return {"ok": True}


@app.get("/api/stats")
async def api_stats():
    return get_stats()


@app.get("/api/sources")
async def api_sources():
    return {"sources": get_sources()}


@app.post("/api/collect")
async def api_collect():
    stats = await run_collection()
    return stats


# ── Companies API ──────────────────────────────────────────────

@app.get("/api/companies")
async def api_get_companies(
    ats_platform: Optional[str] = None,
    crawl_status: Optional[str] = None,
    india_friendly: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    companies = get_companies(
        ats_platform=ats_platform, crawl_status=crawl_status,
        india_friendly=india_friendly, search=search,
        limit=limit, offset=offset,
    )
    return {"companies": companies, "count": len(companies)}


class CompanyInput(BaseModel):
    name: str
    domain: str = ""
    careers_url: str = ""
    ats_platform: str = "unknown"
    ats_slug: str = ""
    founded_year: int = 0
    employee_count: str = ""
    tags: str = ""
    india_friendly: str = "unknown"
    notes: str = ""


@app.post("/api/companies")
async def api_add_company(body: CompanyInput):
    from core.models import Company
    data = body.model_dump()
    data["id"] = Company.make_id(data["name"])
    data["last_crawled"] = ""
    data["crawl_status"] = "active"
    upsert_company(data)
    return {"ok": True, "id": data["id"]}


@app.patch("/api/companies/{company_id}")
async def api_update_company(company_id: str, body: CompanyInput):
    existing = get_company_by_id(company_id)
    if not existing:
        return {"error": "Not found"}
    data = body.model_dump()
    data["id"] = company_id
    data["last_crawled"] = existing.get("last_crawled", "")
    data["crawl_status"] = existing.get("crawl_status", "active")
    upsert_company(data)
    return {"ok": True}


@app.delete("/api/companies/{company_id}")
async def api_pause_company(company_id: str):
    from datetime import datetime
    update_company_crawl_status(company_id, "paused", datetime.utcnow().isoformat())
    return {"ok": True}


@app.post("/api/companies/{company_id}/activate")
async def api_activate_company(company_id: str):
    update_company_crawl_status(company_id, "active")
    return {"ok": True}


@app.get("/api/companies/stats")
async def api_company_stats():
    return get_company_stats()


@app.post("/api/companies/seed")
async def api_seed_companies():
    from core.company_seeder import get_all_seed_companies
    companies = get_all_seed_companies()
    added = 0
    for c in companies:
        if upsert_company(c):
            added += 1
    return {"seeded": len(companies), "added": added}


@app.post("/api/companies/mega-seed")
async def api_mega_seed():
    """Load 250+ Indian + MNC + Global remote companies."""
    from core.mega_companies import get_all_mega_companies
    companies = get_all_mega_companies()
    added = 0
    for c in companies:
        if upsert_company(c):
            added += 1
    return {"total_in_list": len(companies), "added": added}


@app.post("/api/companies/{company_id}/crawl")
async def api_crawl_company(company_id: str):
    stats = await run_company_crawl(company_ids=[company_id])
    return stats


@app.post("/api/companies/crawl")
async def api_crawl_all_companies():
    stats = await run_company_crawl()
    return stats


@app.post("/api/companies/detect-ats")
async def api_detect_ats(domain: str = Query(...)):
    from core.company_seeder import detect_ats_platform
    result = await detect_ats_platform(domain)
    return result


@app.post("/api/companies/discover")
async def api_discover_companies(
    sources: str = Query("yc,remoteintech,wwr"),
    detect_ats: bool = Query(True),
    min_team_size: int = Query(10, ge=1),
):
    """Bulk discover companies from YC, RemoteInTech, WeWorkRemotely."""
    from core.bulk_discover import run_bulk_discovery
    source_list = [s.strip() for s in sources.split(",") if s.strip()]
    stats = await run_bulk_discovery(
        sources=source_list, detect_ats=detect_ats, min_team_size=min_team_size,
    )
    return stats


# ── Google Sheets Export ───────────────────────────────────────

@app.post("/api/export/sheets")
async def api_export_sheets(
    min_score: int = Query(0, ge=0, le=100),
    india_friendly: Optional[str] = None,
    source: Optional[str] = None,
    search: Optional[str] = None,
    tech: Optional[str] = None,
    mode: str = Query("replace"),
    sheet_name: str = Query("Jobs"),
):
    import os
    creds = GOOGLE_SHEETS_CREDS
    sheet_id = GOOGLE_SHEET_ID
    if not sheet_id:
        return {"error": "GOOGLE_SHEET_ID not set in .env"}
    if not os.path.exists(creds):
        return {"error": f"Credentials file not found: {creds}"}
    try:
        result = export_to_sheet(
            creds_file=creds, spreadsheet_id=sheet_id, sheet_name=sheet_name,
            min_score=min_score, india_friendly=india_friendly,
            source=source, search=search, tech=tech, mode=mode,
        )
        return result
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/export/sheets/status")
async def api_sheets_status():
    import os
    return {
        "configured": bool(GOOGLE_SHEET_ID) and os.path.exists(GOOGLE_SHEETS_CREDS),
        "sheet_id": GOOGLE_SHEET_ID[:10] + "..." if GOOGLE_SHEET_ID else "",
        "creds_exists": os.path.exists(GOOGLE_SHEETS_CREDS),
    }


# ── Outreach API ───────────────────────────────────────────────

@app.get("/api/outreach")
async def api_get_outreach(
    status: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    items = get_outreach(status=status, search=search, limit=limit, offset=offset)
    return {"outreach": items, "count": len(items)}


@app.get("/api/outreach/stats")
async def api_outreach_stats():
    return get_outreach_stats()


@app.post("/api/outreach/generate")
async def api_generate_outreach(
    min_score: int = Query(40, ge=0, le=100),
    limit: int = Query(15, ge=1, le=50),
    india_friendly: Optional[str] = "maybe",
):
    """For top N high-scoring jobs without existing outreach,
    build LinkedIn search URLs + generate DMs. No API credits used."""
    import hashlib
    import json
    from datetime import datetime
    from core.hunter import build_linkedin_searches, generate_dm_template

    # Get top jobs — India-friendly, high score
    all_top = get_jobs(min_score=min_score, india_friendly=india_friendly, limit=200)
    candidates = []
    for j in all_top:
        if outreach_exists_for_job(j["id"]):
            continue
        candidates.append(j)
        if len(candidates) >= limit:
            break

    if not candidates:
        return {"generated": 0, "message": "No new jobs eligible for outreach"}

    generated = 0
    for job in candidates:
        try:
            searches = build_linkedin_searches(job["company"])
            dms = generate_dm_template(job)

            # Primary search URL = first one (Engineering Manager)
            primary_url = searches[0]["url"] if searches else ""

            # Store all search URLs as JSON in contact_linkedin field
            all_searches_json = json.dumps(searches)

            outreach_id = hashlib.md5(f"{job['id']}|linkedin".encode()).hexdigest()
            insert_outreach({
                "id": outreach_id,
                "job_id": job["id"],
                "job_title": job["title"],
                "company": job["company"],
                "company_domain": job.get("company_domain", ""),
                "contact_name": "[Search LinkedIn]",
                "contact_position": "Engineering Manager / Tech Lead / Head of Eng",
                "contact_linkedin": primary_url,
                "dm_short": dms["short"],
                "dm_long": dms["long"],
                "status": "pending",
                "messaged_at": "", "replied_at": "", "followed_up_at": "",
                "created_at": datetime.utcnow().isoformat(),
                "notes": all_searches_json,  # store all 3 search URLs
                "emailed_at": "",
            })
            generated += 1
        except Exception as e:
            print(f"Error for {job.get('company')}: {e}")
            continue

    return {"generated": generated, "candidates": len(candidates)}


@app.patch("/api/outreach/{outreach_id}/status")
async def api_update_outreach(outreach_id: str, status: str = Query(...)):
    field_map = {"messaged": "messaged", "replied": "replied", "followed_up": "followed_up"}
    update_outreach_status(outreach_id, status, field=field_map.get(status))
    return {"ok": True}


@app.patch("/api/outreach/{outreach_id}/notes")
async def api_update_outreach_notes(outreach_id: str, notes: str = Query("")):
    update_outreach_notes(outreach_id, notes)
    return {"ok": True}


# ── Search Queries (JSearch config) ────────────────────────────

@app.get("/api/search-queries")
async def api_get_queries():
    return {"queries": get_search_queries()}


class QueryInput(BaseModel):
    query: str
    country: str = "IN"
    date_posted: str = "3days"
    remote_jobs_only: bool = False


@app.post("/api/search-queries")
async def api_add_query(body: QueryInput):
    qid = add_search_query(body.query, body.country, body.date_posted, body.remote_jobs_only)
    return {"id": qid, "ok": True}


class QueryPatch(BaseModel):
    query: Optional[str] = None
    country: Optional[str] = None
    date_posted: Optional[str] = None
    remote_jobs_only: Optional[bool] = None
    enabled: Optional[bool] = None


@app.patch("/api/search-queries/{qid}")
async def api_update_query(qid: int, body: QueryPatch):
    update_search_query(qid, **body.model_dump(exclude_none=True))
    return {"ok": True}


@app.delete("/api/search-queries/{qid}")
async def api_delete_query(qid: int):
    delete_search_query(qid)
    return {"ok": True}


# ── Mark Job for Email ─────────────────────────────────────────

@app.post("/api/jobs/{job_id}/mark-for-email")
async def api_mark_for_email(job_id: str):
    new_state = toggle_mark_for_email(job_id)
    return {"mark_for_email": new_state}


@app.get("/api/jobs/marked")
async def api_get_marked():
    return {"jobs": get_marked_jobs()}


# ── Email Digest API ───────────────────────────────────────────

@app.post("/api/email/send-now")
async def api_send_email_now(dry_run: bool = Query(False)):
    """Manually trigger the daily digest email."""
    result = send_daily_digest(dry_run=dry_run)
    return result


@app.post("/api/email/run-pipeline")
async def api_run_pipeline(send: bool = Query(True)):
    """Manually run the full daily pipeline: collect → outreach → email."""
    result = await run_daily_pipeline(send=send)
    return result


@app.get("/api/email/status")
async def api_email_status():
    from core.database import get_email_logs
    import os
    logs = get_email_logs(limit=10)
    return {
        "sender_configured": bool(SENDER_EMAIL) and bool(os.getenv("SENDER_APP_PASSWORD")),
        "recipient": os.getenv("RECIPIENT_EMAIL", ""),
        "scheduled_hour": DAILY_EMAIL_HOUR,
        "timezone": DAILY_EMAIL_TIMEZONE,
        "recent_sends": logs,
    }


@app.get("/api/jsearch/status")
async def api_jsearch_status():
    from core.database import get_api_usage
    import os
    usage = get_api_usage("jsearch")
    # Free tier: 200 requests/month
    monthly_limit = 200
    return {
        "configured": bool(os.getenv("RAPIDAPI_KEY")),
        "month": usage["month"],
        "today": usage["today"],
        "total": usage["total"],
        "monthly_limit": monthly_limit,
        "remaining": max(0, monthly_limit - usage["month"]),
    }


@app.get("/api/hunter/status")
async def api_hunter_status():
    import httpx
    if not HUNTER_API_KEY:
        return {"configured": False}
    try:
        resp = httpx.get(
            "https://api.hunter.io/v2/account",
            params={"api_key": HUNTER_API_KEY}, timeout=10,
        )
        data = resp.json()
        if "data" in data:
            return {
                "configured": True,
                "plan": data["data"].get("plan_name", ""),
                "used": data["data"].get("requests", {}).get("used", 0),
                "available": data["data"].get("requests", {}).get("available", 0),
            }
        return {"configured": True, "error": "could not fetch stats"}
    except Exception as e:
        return {"configured": True, "error": str(e)}


# ── UI Routes ──────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/outreach", response_class=HTMLResponse)
async def outreach_page(request: Request):
    return templates.TemplateResponse("outreach.html", {"request": request})


if __name__ == "__main__":
    print(f"Starting Job Scraper at http://{HOST}:{PORT}")
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
