# Architecture

## High-Level Flow

```
┌────────────────────────────────────────────────────────────────┐
│                      Job Sources (Track A)                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │ Remotive │ │ RemoteOK │ │Arbeitnow │ │ JSearch (RapidAPI│  │
│  │  (free)  │ │  (free)  │ │  (free)  │ │ LinkedIn/Indeed/ │  │
│  │          │ │          │ │          │ │ Glassdoor agg.)  │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘  │
└────────────────────────────────────────────────────────────────┘
                              │
┌────────────────────────────────────────────────────────────────┐
│                 Company ATS Crawl (Track B)                    │
│  150 active companies × their Greenhouse/Lever/Ashby APIs      │
│  (e.g., MongoDB, Stripe, Twilio, Airbnb, Instacart, etc.)     │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                      Scoring & Filtering                       │
│  • Title keywords (backend, python, django) → +points          │
│  • Tech stack match (python/django/fastapi) → +points          │
│  • Experience level (mid/3+ yrs) → +points                     │
│  • India-friendly check (location + timezone)                  │
│  • Jobs scoring < 25 are DROPPED (not stored)                  │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                    SQLite Database (jobs.db)                   │
│  • jobs: deduplicated by fingerprint (MD5 of company+title+loc)│
│  • Existing jobs get last_seen refreshed                       │
│  • Jobs not seen in 14 days auto-deleted                       │
│  • Protected: jobs marked "applied" or "for_email" never dropped│
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                   Outreach Generation                          │
│  For top 15 scoring jobs:                                      │
│  • Build 7 LinkedIn people-search URLs per company:            │
│    Eng Manager, Tech Lead, Head of Eng,                        │
│    CTO, CEO/Founder,                                           │
│    Tech Recruiter, HR Manager                                  │
│  • Generate personalized DM (short + long versions)            │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                 Daily Email at 9:00 AM IST                     │
│  • APScheduler triggers pipeline                               │
│  • 15 job cards in HTML email                                  │
│  • Each card: job info + 7 search buttons + DM + apply link    │
│  • Sent via Gmail SMTP (app password)                          │
│  • Marked as emailed — won't resend next day                   │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                  parmanandprajapati0009@gmail.com
```

---

## Components

### Backend (`main.py`, `core/`, `sources/`)
- **FastAPI server** serves UI + exposes REST API
- **APScheduler** runs the daily pipeline at 9 AM IST
- **Collector** (`core/collector.py`) orchestrates fetching, scoring, deduplication
- **Scorer** (`core/scorer.py`) rates jobs 0-100 based on rules
- **Emailer** (`core/emailer.py`) composes HTML email, sends via SMTP
- **Sources** (`sources/*.py`) pluggable fetchers — one per job board / ATS platform

### Frontend (`templates/`, `static/`)
- Two pages: Jobs (`/`) and Outreach (`/outreach`)
- Vanilla JavaScript, no build step
- Talks to backend via `/api/*` endpoints

### Database (SQLite — `jobs.db`)
- `jobs` — deduplicated job listings
- `companies` — 3,500+ companies (150 active for crawling)
- `outreach` — generated outreach items with status tracking
- `search_queries` — user-configurable JSearch queries
- `email_log` — history of sent emails
- `api_usage` — tracks JSearch API call count
- `outreach_usage` — (not used currently)

See [06-database.md](06-database.md) for schema details.

---

## Two Tracks of Job Collection

### Track A: Job Boards
Runs on every "Collect Jobs" click. Fetches from 4 sources in parallel:

| Source | Type | What it returns |
|---|---|---|
| Remotive | Public API | Remote tech jobs |
| RemoteOK | Public API | Remote tech jobs |
| Arbeitnow | Public API | European remote |
| JSearch | RapidAPI (paid tier free) | LinkedIn + Indeed + Glassdoor aggregated |

JSearch runs 6 configurable queries (user can edit via UI), covering India + remote + US.

### Track B: Company ATS Crawl
For each active company in `companies` table:
- If `ats_platform = greenhouse` → hit `boards-api.greenhouse.io/v1/boards/{slug}/jobs`
- If `ats_platform = lever` → hit `api.lever.co/v0/postings/{slug}`
- If `ats_platform = ashby` → hit `api.ashbyhq.com/posting-api/job-board/{slug}`

150 companies currently active. Contributes ~500-1000 jobs per run.

---

## Deduplication Logic

Each job gets a **fingerprint**:
```python
hashlib.md5(f"{company}|{title}|{location}".encode()).hexdigest()
```

When collecting:
- **New fingerprint** → INSERT the job
- **Existing fingerprint** → UPDATE `last_seen` timestamp (confirms job still posted)
- **Not seen in 14 days** → DELETE (but `applied` / `marked_for_email` jobs are protected)

This keeps the DB lean — only currently-active jobs remain.

---

## Scoring Algorithm

Score out of 100:

| Category | Points | Logic |
|---|---|---|
| Title match | 0-35 | +12 per keyword (backend, python, django, fastapi); -15 per negative (frontend, mobile, intern) |
| Tech stack | 0-35 | +12 per core tech (python/django/fastapi/flask); +3 per related (redis/docker/aws) |
| Experience | 0-15 | +15 mid, +10 senior, -10 junior |
| Backend signals | 0-15 | +4 per signal (api, rest, graphql, microservice, database) |

**Filter:** Jobs scoring < 25 are dropped before storage. Keeps DB focused.

---

## Outreach Generation (LinkedIn Searches)

Instead of paying for Apollo/Hunter to find specific contacts, we generate **LinkedIn people-search URLs**.

For each company, 7 search URLs are built:

```
https://www.linkedin.com/search/results/people/?keywords={Company}+{Title}
```

Grouped by category:
- **Engineering**: Eng Manager, Tech Lead, Head of Eng
- **C-Level**: CTO, CEO/Founder
- **HR**: Tech Recruiter, HR Manager

User clicks a button → LinkedIn opens with relevant people listed → they pick who to message.

**Cost: $0** (vs $50+/month for paid contact APIs).

---

## Email Delivery

- **SMTP:** Gmail (smtp.gmail.com:465, SSL)
- **Auth:** App Password (not regular Gmail password)
- **Format:** HTML with inline CSS + plain text fallback
- **Size:** ~80KB per email (well under Gmail's 25MB limit)
- **Rate:** 1 email/day → no spam concerns

Daily at 9 AM IST, the `run_daily_pipeline` function:
1. Calls `run_collection()` — fetch new jobs
2. Auto-generates outreach for top 15 new jobs
3. Sends email
4. Logs it to `email_log` table

---

## Why This Architecture?

- **No paid APIs** — only free tiers, ~$0/month
- **SQLite** — zero setup, portable, handles 10k+ jobs easily
- **Pluggable sources** — add a new job board by creating a class that inherits `BaseSource`
- **Scoring decoupled** — one scorer handles all sources consistently
- **Dedup by fingerprint** — automatic, no manual work
- **LinkedIn search URLs** — bypasses expensive contact-finding APIs
