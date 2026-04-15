# Customization Guide

How to adapt the system for different candidates, roles, or markets.

---

## Change the Candidate Profile

The DM templates currently reference Parmanand's specific experience. To customize:

### Edit `core/hunter.py` → `generate_dm_template()`

Replace these hardcoded details:
- **"healthcare SaaS serving 5,000+ users with sub-200ms APIs"**
- **"DoctusTech"**
- **"multitenant SaaS + Stripe integrations"**

Example for a different candidate (say, an ML engineer):
```python
long = (
    f"{greeting},\n\n"
    f"Noticed {company} is hiring for {title}. The stack caught my eye — "
    f"I've been shipping {stack_phrase} ML pipelines for 3+ years.\n\n"
    f"Current role: Senior ML Engineer at CompanyX. I built a recommendation "
    f"system serving 100M+ daily users, achieving 15% CTR uplift.\n\n"
    # ... rest of template
)
```

### Update the candidate name
In `core/hunter.py`:
```python
def generate_dm_template(job: dict, contact: dict = None, candidate_name: str = "Parmanand") -> dict:
```

Change `"Parmanand"` to the actual first name. It's passed to the long DM's signature.

### Update the email greeting
In `core/emailer.py` → `build_email_html()`:
```python
def build_email_html(items: list[dict], candidate_name: str = "Parmanand") -> str:
```

---

## Change Target Role / Stack

The system is currently tuned for **Python/Django backend**. To target other roles, edit `config/settings.py`.

### For frontend developers:
```python
TITLE_KEYWORDS_POSITIVE = [
    "frontend", "front-end", "react", "vue", "angular",
    "software engineer", "ui engineer", "full stack",
]

TITLE_KEYWORDS_NEGATIVE = [
    "backend", "devops", "data", "ml engineer", "mobile",
    "qa", "intern", "trainee", "junior",
]

RELEVANT_TECH = [
    "react", "vue", "angular", "typescript", "javascript",
    "nextjs", "redux", "tailwind", "css", "html",
    "graphql", "webpack", "vite", "jest",
]
```

### For data engineers:
```python
TITLE_KEYWORDS_POSITIVE = [
    "data engineer", "data", "etl", "analytics engineer",
    "pipeline", "warehouse",
]

RELEVANT_TECH = [
    "python", "sql", "dbt", "airflow", "spark",
    "kafka", "snowflake", "bigquery", "redshift",
    "pandas", "databricks", "aws", "gcp",
]
```

### For ML engineers:
```python
TITLE_KEYWORDS_POSITIVE = [
    "machine learning", "ml engineer", "ai engineer",
    "mlops", "data scientist",
]

RELEVANT_TECH = [
    "pytorch", "tensorflow", "transformers", "langchain",
    "huggingface", "numpy", "pandas", "sklearn",
    "mlflow", "kubeflow", "sagemaker",
]
```

---

## Change JSearch Queries

Use the UI (Search Queries modal) — no code changes needed.

Default queries are in `core/database.py` → `init_db()`:
```python
defaults = [
    ("python django backend developer", "IN", "3days", 0),
    ...
]
```

First-run seed only. After that, use UI.

---

## Change Geography

### Target a different country
Update `config/settings.py`:

```python
# For US jobs only
LOCATION_POSITIVE = [
    "united states", "us", "usa", "remote us",
    "worldwide", "global", "anywhere",
]

LOCATION_NEGATIVE = [
    "india only", "emea only", "uk only",
]
```

Also update JSearch queries via UI to use `country=US`.

### Remove India filter entirely
In `core/scorer.py`, set `check_india_friendly()` to always return "yes".

Or in API calls, don't pass `india_friendly` filter.

---

## Change Score Threshold

### Store more jobs (lower bar)
`core/collector.py`:
```python
MIN_SCORE_TO_STORE = 15  # default: 25
```

### Show only top-quality jobs in email
`core/emailer.py` → `run_daily_pipeline()`:
```python
top_jobs = get_jobs(min_score=60, ...)  # default: 40
```

---

## Change Email Schedule

### Different time of day
Edit `.env`:
```
DAILY_EMAIL_HOUR=7   # 7 AM IST instead of 9 AM
```

### Different timezone
Edit `config/settings.py`:
```python
DAILY_EMAIL_TIMEZONE = "America/New_York"  # or any valid TZ
```

### Multiple emails per day
Edit `main.py` startup — add more scheduler jobs:
```python
scheduler.add_job(run_daily_pipeline, CronTrigger(hour=9), id="morning_digest")
scheduler.add_job(run_daily_pipeline, CronTrigger(hour=17), id="evening_digest")
```

### Change number of jobs in email
Edit `.env`:
```
DAILY_JOBS_COUNT=20   # default: 15
```

---

## Add a New Job Source

### Example: Add LinkedIn Jobs via their RSS feed

Create `sources/linkedin_rss.py`:

```python
import httpx
from sources.base import BaseSource
from core.models import Job
from xml.etree import ElementTree as ET

class LinkedInRSSSource(BaseSource):
    name = "linkedin"
    
    async def fetch(self) -> list[Job]:
        # LinkedIn's public RSS URL per saved search
        url = "https://www.linkedin.com/jobs/python-developer-jobs-india/rss"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url)
            resp.raise_for_status()
        
        root = ET.fromstring(resp.text)
        jobs = []
        for item in root.findall(".//item"):
            job = Job(
                title=item.findtext("title", ""),
                company="LinkedIn Listing",  # parse from description
                location="",
                description=item.findtext("description", ""),
                url=item.findtext("link", ""),
                source=self.name,
                posted_date=item.findtext("pubDate", ""),
            )
            jobs.append(job)
        return jobs
```

Register in `core/collector.py`:

```python
from sources.linkedin_rss import LinkedInRSSSource

def _build_job_board_sources():
    sources = [
        RemotiveSource(),
        RemoteOKSource(),
        ArbeitnowSource(),
        LinkedInRSSSource(),   # ADD HERE
    ]
    ...
```

That's it. All scoring, dedup, filtering still applies.

---

## Multi-Candidate Support

To run for multiple candidates, easiest approach is **separate instances**:

### Option A: Multiple databases

```bash
# Candidate 1
DB_PATH=candidate1.db python -m uvicorn main:app --port 8000

# Candidate 2
DB_PATH=candidate2.db python -m uvicorn main:app --port 8001
```

But `DB_PATH` is currently hardcoded in `config/settings.py`. Make it env-driven:

```python
DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "jobs.db"))
```

Then run multiple with different ports + DBs.

### Option B: Multi-tenant (bigger rewrite)

Add `candidate_id` to all tables. Switch context via URL or login. Not currently built.

---

## Disable Features

### Disable daily email
Set `SENDER_EMAIL=` (empty) in `.env`. Scheduler skips.

### Disable company crawling
Comment out in `core/collector.py`:
```python
# if include_companies:
#     log("\n--- Company Crawl ---")
#     company_stats = await run_company_crawl()
```

### Disable JSearch
Remove `RAPIDAPI_KEY` from `.env`. Only free sources run.

---

## Change DM Tone

Current templates are professional but casual. For different tones, edit `core/hunter.py` → `generate_dm_template()`.

### Formal:
```python
short = (
    f"Dear {first_name if first_name else 'Sir/Madam'},\n"
    f"I am writing regarding the {title} role at {company}. "
    f"With 3+ years of experience in {stack_phrase}, I would like to..."
)
```

### Bold / Confident:
```python
short = (
    f"{greeting} — {title} at {company} looks like a perfect fit. "
    f"I've shipped {stack_phrase} systems at scale. "
    f"Can we talk?"
)
```

---

## Integrate with n8n / Zapier

Use the Google Sheets export endpoint:
```
POST /api/export/sheets?min_score=50&india_friendly=yes
```

Then in n8n:
1. Google Sheets trigger (new row)
2. Hunter.io node (find email)
3. Gmail node (send cold email)

See [02-setup.md](02-setup.md) for Google Sheets config.
