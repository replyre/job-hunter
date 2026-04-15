# Job Scraper + Daily Outreach System

An automated job discovery and cold outreach system built for backend Python/Django engineers (3+ YOE). Finds fresh jobs daily, scores them for relevance, generates personalized LinkedIn outreach templates, and emails a curated list every morning.

**Target user:** Python/Django backend developers applying for jobs in India or remote-friendly roles.

---

## What It Does

```
Every day at 9:00 AM IST (automatic):

  1. Collects jobs from 4 sources + 150 company career pages
  2. Filters to relevant Python/Django backend roles (score 25+)
  3. Deduplicates + cleans up old jobs automatically
  4. For top 15 jobs:
       - Generates 7 LinkedIn search URLs per company
         (Eng Manager, Tech Lead, CTO, CEO, HR, etc.)
       - Writes a personalized DM
  5. Emails the curated list to the candidate's inbox
```

**Result:** Candidate opens email, gets 15 fresh matching jobs with ready-to-send LinkedIn DMs. Takes ~20 min/day to work through.

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
| `SENDER_EMAIL` | ✅ Required for email | Daily email won't send |
| `SENDER_APP_PASSWORD` | ✅ Required for email | Daily email won't send |
| `RECIPIENT_EMAIL` | ✅ Required for email | Daily email has no destination |
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
- **Frontend:** Vanilla JS, HTML, CSS (no framework)
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
