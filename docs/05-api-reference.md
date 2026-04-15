# API Reference

All backend endpoints. Base URL: `http://127.0.0.1:8000/api`

---

## Jobs

### `GET /api/jobs`
List jobs with filters.

**Query params:**
- `source` — filter by source name (partial match)
- `status` — new / reviewed / applied / stale
- `min_score` — integer 0-100
- `search` — free text (title, company, description)
- `location` — partial match
- `tech` — partial match on tech_stack
- `india_friendly` — yes / maybe / no
- `company_domain` — exact match
- `limit` — default 50, max 500
- `offset` — pagination offset

**Response:**
```json
{
  "jobs": [{...}, ...],
  "count": 50
}
```

### `GET /api/jobs/{job_id}`
Get a single job by ID.

### `PATCH /api/jobs/{job_id}/status`
Update a job's status.

**Query param:** `status` — new / reviewed / applied / stale

### `POST /api/jobs/{job_id}/mark-for-email`
Toggle the mark-for-email flag on a job.

**Response:** `{"mark_for_email": true|false}`

### `GET /api/jobs/marked`
List all jobs currently marked for email.

### `GET /api/stats`
Aggregated stats.

**Response:**
```json
{
  "total": 880,
  "by_source": {"jsearch": 120, "greenhouse:mongodb": 143, ...},
  "by_status": {"new": 800, "applied": 10, ...},
  "by_india": {"yes": 494, "maybe": 351, "no": 35},
  "avg_score": 38.8
}
```

### `GET /api/sources`
List all distinct sources that have jobs.

### `POST /api/collect`
Trigger full collection pipeline (job boards + company crawl).

**Response:**
```json
{
  "fetched": 4357,
  "new": 574,
  "updated": 332,
  "filtered_out": 3451,
  "deleted_stale": 4151,
  "board_sources": {...},
  "companies_crawled": 150,
  "companies_failed": 0
}
```

---

## Search Queries (JSearch)

### `GET /api/search-queries`
List all configured JSearch queries.

### `POST /api/search-queries`
Add a new search query.

**Body:**
```json
{
  "query": "python backend senior",
  "country": "IN",
  "date_posted": "3days",
  "remote_jobs_only": false
}
```

### `PATCH /api/search-queries/{id}`
Update a query. Pass any subset of fields:
```json
{
  "enabled": false
}
```

### `DELETE /api/search-queries/{id}`
Delete a query.

---

## Companies (background use, no UI currently)

### `GET /api/companies`
List companies with filters (ats_platform, crawl_status, india_friendly, search).

### `POST /api/companies`
Add a company manually.

### `PATCH /api/companies/{id}`
Update a company.

### `DELETE /api/companies/{id}`
Pause a company (soft delete — sets status to paused).

### `POST /api/companies/{id}/activate`
Re-activate a paused company.

### `POST /api/companies/{id}/crawl`
Manually crawl one company.

### `POST /api/companies/crawl`
Crawl all active companies.

### `GET /api/companies/stats`
Aggregate stats.

### `POST /api/companies/seed`
Load 73 pre-built companies with known ATS slugs.

### `POST /api/companies/mega-seed`
Load 210 Indian + MNC + global companies (no ATS detection).

### `POST /api/companies/discover`
Bulk discover from YCombinator + RemoteInTech + WeWorkRemotely.

**Query params:**
- `sources` — comma-separated: yc,remoteintech,wwr
- `detect_ats` — bool (slow if true)
- `min_team_size` — integer

### `POST /api/companies/detect-ats`
Probe a domain to detect its ATS platform.

**Query param:** `domain` (e.g., `stripe.com`)

---

## Outreach

### `GET /api/outreach`
List outreach items.

**Query params:**
- `status` — pending / messaged / replied / followed_up
- `search` — free text
- `limit`, `offset`

### `GET /api/outreach/stats`
Counts by status.

### `POST /api/outreach/generate`
Generate outreach for top N jobs without existing outreach.

**Query params:**
- `min_score` — default 40
- `limit` — default 15
- `india_friendly` — default "maybe"

### `PATCH /api/outreach/{id}/status`
Update outreach status.

**Query param:** `status` — pending / messaged / replied / followed_up

### `PATCH /api/outreach/{id}/notes`
Update outreach notes.

**Query param:** `notes` — text

---

## Email Digest

### `GET /api/email/status`
Check email configuration + recent sends.

**Response:**
```json
{
  "sender_configured": true,
  "recipient": "parmanandprajapati0009@gmail.com",
  "scheduled_hour": 9,
  "timezone": "Asia/Kolkata",
  "recent_sends": [...]
}
```

### `POST /api/email/send-now`
Manually send the daily digest right now.

**Query param:** `dry_run` — if true, returns preview without sending

### `POST /api/email/run-pipeline`
Run the full daily pipeline manually (collect + outreach + email).

**Query param:** `send` — default true

---

## Google Sheets Export

### `POST /api/export/sheets`
Export filtered jobs to Google Sheet.

**Query params:** same filters as `/api/jobs` + `sheet_name`, `mode` (replace/append)

### `GET /api/export/sheets/status`
Check if Google Sheets is configured.

---

## API Usage / Monitoring

### `GET /api/jsearch/status`
JSearch usage stats.

**Response:**
```json
{
  "configured": true,
  "month": 12,
  "today": 6,
  "total": 18,
  "monthly_limit": 200,
  "remaining": 188
}
```

### `GET /api/hunter/status`
Hunter.io account stats (not actively used).

---

## UI Routes (HTML pages)

- `GET /` — Jobs dashboard
- `GET /outreach` — Outreach dashboard
