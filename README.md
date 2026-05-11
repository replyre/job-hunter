# Job Scraper + Daily Outreach System

An automated job discovery and cold outreach system built for software engineers. Finds fresh jobs daily, scores them against a **configurable role profile**, generates personalized LinkedIn outreach templates, and emails a curated list every morning.

**Target user:** Any developer running a job search — comes with presets for **Backend Python (3+ YOE)**, **Frontend React**, and **Fresher**. Swap profiles to retarget the entire pipeline (search queries, scoring weights, outreach copy) without editing code.

---

## What It Does

```
Every day at 9:00 AM IST (automatic):

  1. Collects jobs from 4 sources + 150 company career pages
  2. Scores each job against the ACTIVE profile (title/tech/exp/signals)
  3. Drops anything below the profile's min-score, deduplicates,
     cleans up jobs not seen in 14 days
  4. For top 15 jobs:
       - Generates LinkedIn people-search URLs per company
         (titles configured on the profile — Eng Manager, Tech Lead,
         CTO, CEO, HR, etc.)
       - Writes a personalized DM using the profile's templates
  5. Emails the curated list to the recipient configured on the profile
```

**Result:** Candidate opens email, gets 15 fresh matching jobs with ready-to-send LinkedIn DMs. Takes ~20 min/day to work through. Change roles? Switch profile — no code changes.

---

## Profiles

The pipeline is driven by an **active profile** — a single config blob that controls search queries, scoring, location preferences, and outreach copy. Switching profiles re-targets the system end-to-end without touching code.

### Built-in presets

Stored as YAML in `profiles/`. Import any of them from the Profile page (or via `POST /api/profiles/import`):

| Preset (`profiles/*.yaml`) | Who it's for |
|---|---|
| `backend_python.yaml` | Python/Django/FastAPI backend, 3+ YOE (the original target) |
| `frontend_react.yaml` | React/TypeScript frontend roles |
| `fresher_any.yaml` | Entry-level / 0-1 YOE across any stack |

### What a profile controls

A profile is one row in the `profiles` table (JSON config), with sections matching the **Profile page tabs**:

- **Search** — default search terms, positive/negative title keywords, relevant tech list, JSearch queries (country, posted-window, remote-only)
- **Scoring** — experience target (`fresher` / `junior` / `mid` / `senior` / `any`), min-score-to-show, min-score-to-store, weights for title/tech/experience/signals (sum to 100), core tech, domain signals
- **Location** — India-positive / India-negative keywords, timezone-compatible / incompatible lists
- **Outreach** — candidate name, bio, achievements, core/extra tech, short + long DM templates, LinkedIn search titles, email greeting, sender + recipient email, digest subject role word

### UI — `/profile` page

- Sidebar lists all saved profiles and shows the currently-active one
- Import any YAML preset, edit it, then **Save** or **Save & Activate**
- **Re-score All Jobs** — recomputes every stored job's relevance against the active profile (optionally drops anything that now falls below min-score-to-store)
- **Export YAML** — download the active profile as YAML (round-trips back into `profiles/`)
- **Duplicate / Delete** — fork a profile to tweak, or remove an unused one (the active profile can't be deleted — activate another first)

### Per-profile email settings

Email digest fields live on the profile: `sender_email`, `recipient_email`, `email_greeting`, `email_digest_subject_role`. These **override** the corresponding `.env` values, so different profiles can send to different inboxes. The Gmail app password still comes from `SENDER_APP_PASSWORD` in `.env` — it must match whichever sender address the active profile uses.

### Profile API (summary)

| Method + path | Purpose |
|---|---|
| `GET /api/profiles` | List all profiles + presets available for import |
| `GET /api/profiles/active` | Get the currently-active profile's full config |
| `GET /api/profiles/{id}` | Get one profile by id |
| `POST /api/profiles` | Create a new profile from a JSON body |
| `PUT /api/profiles/{id}` | Update name / description / config |
| `POST /api/profiles/{id}/activate` | Make this profile active (cache invalidated immediately) |
| `POST /api/profiles/{id}/duplicate` | Fork an existing profile |
| `DELETE /api/profiles/{id}` | Delete (rejected if active) |
| `POST /api/profiles/import` | Import a YAML preset by slug; optional `activate` + `overwrite` flags |
| `GET /api/profiles/{id}/export` | Export profile back to YAML |
| `POST /api/profiles/rescore-all` | Re-score every stored job against the active profile (`delete_below_min=true` to prune) |

On first run, if no profile exists, the system seeds a `Backend Python (legacy)` profile from the pre-profile hardcoded settings and activates it — so existing installs keep working.

---

## Documentation

| Doc | What's in it |
|---|---|
| [docs/01-architecture.md](docs/01-architecture.md) | How the system works — data flow, components |
| [docs/02-setup.md](docs/02-setup.md) | Installation, API keys, environment setup |
| [docs/03-usage.md](docs/03-usage.md) | Daily workflow for the candidate |
| [docs/04-features.md](docs/04-features.md) | What each page and feature does |
| [docs/05-api-reference.md](docs/05-api-reference.md) | All API endpoints |
| [docs/06-database.md](docs/06-database.md) | Database schema |
| [docs/07-customization.md](docs/07-customization.md) | How to adapt for other candidates / roles |
| [docs/job-scraper.postman_collection.json](docs/job-scraper.postman_collection.json) | Postman collection (import + the env file alongside it) for every endpoint, including the profile APIs |

---

## Quick Start

```bash
# 1. Install Python deps
pip install -r requirements.txt

# 2. Copy env template and fill in API keys
cp .env.example .env
# Edit .env with your API keys (see Environment Variables below)

# 3. Run the server
python -m uvicorn main:app --host 127.0.0.1 --port 8000

# 4. Open http://127.0.0.1:8000 in browser
```

---

## Environment Variables (`.env`)

Create a `.env` file in the project root with the following:

```bash
# ─── Required for JSearch (LinkedIn/Indeed/Glassdoor aggregator) ───
# Sign up: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
# Free tier: 200 requests/month
RAPIDAPI_KEY=your_rapidapi_key_here

# ─── Required for Daily Email Digest ───
# Must use Gmail App Password, NOT your regular password
# Generate at: https://myaccount.google.com/apppasswords
# (Requires 2-Step Verification enabled first)
SENDER_EMAIL=your-gmail@gmail.com
SENDER_APP_PASSWORD=abcdefghijklmnop
RECIPIENT_EMAIL=candidate@gmail.com

# ─── Daily Digest Timing (IST timezone) ───
DAILY_EMAIL_HOUR=9                  # 24-hour format (9 = 9:00 AM IST)
DAILY_JOBS_COUNT=15                 # Number of jobs per email

# ─── Optional: Hunter.io (not actively used — LinkedIn search replaces it) ───
# Sign up: https://hunter.io
HUNTER_API_KEY=

# ─── Optional: Google Sheets Export ───
# For n8n / external automation pipelines
# Setup: Create Google Cloud service account → download credentials.json
GOOGLE_SHEETS_CREDS=credentials.json
GOOGLE_SHEET_ID=
```

### Required vs Optional

| Variable | Required | What happens without it |
|---|---|---|
| `RAPIDAPI_KEY` | ⚠️ Strongly recommended | JSearch source won't run; loses ~60 fresh jobs/day |
| `SENDER_EMAIL` | ✅ Required for email | Daily email won't send (the active profile can override this) |
| `SENDER_APP_PASSWORD` | ✅ Required for email | Daily email won't send — must match whichever sender the profile uses |
| `RECIPIENT_EMAIL` | ✅ Required for email | Daily email has no destination (the active profile can override this) |
| `DAILY_EMAIL_HOUR` | Optional (defaults to 9) | Email sends at 9 AM IST |
| `DAILY_JOBS_COUNT` | Optional (defaults to 15) | 15 jobs per email |
| `HUNTER_API_KEY` | Optional | Currently unused — LinkedIn search URLs replaced Hunter |
| `GOOGLE_SHEETS_CREDS` | Optional | Sheets export disabled |
| `GOOGLE_SHEET_ID` | Optional | Sheets export disabled |

### How to get each key

1. **RapidAPI key** (5 min)
   - Sign up at [rapidapi.com](https://rapidapi.com)
   - Subscribe to [JSearch](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch) (Free Basic plan)
   - Copy `X-RapidAPI-Key` from dashboard

2. **Gmail App Password** (3 min)
   - Go to [myaccount.google.com/security](https://myaccount.google.com/security)
   - Enable **2-Step Verification** (required)
   - Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
   - App name: `Job Scraper` → Create
   - Copy the 16-character password (ignore spaces)

3. **Google Sheets** (optional, 10 min)
   - See [docs/02-setup.md](docs/02-setup.md) for full walkthrough

See [docs/02-setup.md](docs/02-setup.md) for complete setup instructions.

---

## Tech Stack

- **Backend:** Python 3.13, FastAPI, SQLite, APScheduler
- **Frontend:** Vanilla JS, HTML, CSS (no framework) — three pages: Jobs, Outreach, Profile
- **Config:** YAML presets in `profiles/` for role configurations; runtime config lives in the `profiles` SQLite table
- **External APIs:** JSearch (RapidAPI), Greenhouse, Lever, Ashby, Remotive, RemoteOK, Arbeitnow
- **Email:** Gmail SMTP with App Password

---

## Cost

Everything free or near-free:

| Service | Cost | What for |
|---|---|---|
| JSearch (RapidAPI) | Free 200 calls/month | Aggregated LinkedIn/Indeed/Glassdoor jobs |
| Greenhouse/Lever/Ashby | Free, unlimited | Company career pages |
| Gmail SMTP | Free | Sending daily email |
| Server hosting | $0 (local) or ~$5/mo (VPS) | Keep it running 24/7 |

**Total: $0–$5/month**

---

## License / Usage

Built for personal job search automation. Adapt freely for your own use.
