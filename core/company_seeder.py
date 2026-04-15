"""Curated seed list of reputable companies organized by ATS platform.
All companies here use public ATS APIs — no auth needed."""

import httpx

# ── Greenhouse Companies ───────────────────────────────────────
# API: GET https://boards.greenhouse.io/{slug}/jobs?content=true

GREENHOUSE_COMPANIES = [
    # Big Tech / Established
    {"name": "Stripe", "domain": "stripe.com", "ats_slug": "stripe", "employee_count": "5000+", "founded_year": 2010, "tags": "fintech,payments,api", "india_friendly": "yes"},
    {"name": "Cloudflare", "domain": "cloudflare.com", "ats_slug": "cloudflare", "employee_count": "3000+", "founded_year": 2009, "tags": "infrastructure,security,cdn"},
    {"name": "Datadog", "domain": "datadoghq.com", "ats_slug": "datadog", "employee_count": "5000+", "founded_year": 2010, "tags": "monitoring,observability,saas"},
    {"name": "GitLab", "domain": "gitlab.com", "ats_slug": "gitlab", "employee_count": "2000+", "founded_year": 2014, "tags": "devops,open-source,remote-first", "india_friendly": "yes"},
    {"name": "Twilio", "domain": "twilio.com", "ats_slug": "twilio", "employee_count": "5000+", "founded_year": 2008, "tags": "communications,api,cloud"},
    {"name": "HashiCorp", "domain": "hashicorp.com", "ats_slug": "hashicorp", "employee_count": "2000+", "founded_year": 2012, "tags": "devops,infrastructure,open-source"},
    {"name": "Elastic", "domain": "elastic.co", "ats_slug": "elastic", "employee_count": "3000+", "founded_year": 2012, "tags": "search,observability,open-source", "india_friendly": "yes"},
    {"name": "MongoDB", "domain": "mongodb.com", "ats_slug": "mongodb", "employee_count": "4000+", "founded_year": 2007, "tags": "database,nosql,cloud", "india_friendly": "yes"},
    {"name": "Confluent", "domain": "confluent.io", "ats_slug": "confluent", "employee_count": "3000+", "founded_year": 2014, "tags": "kafka,streaming,data", "india_friendly": "yes"},
    {"name": "Grafana Labs", "domain": "grafana.com", "ats_slug": "grafanalabs", "employee_count": "1000+", "founded_year": 2014, "tags": "monitoring,observability,open-source", "india_friendly": "yes"},

    # Product / SaaS
    {"name": "Notion", "domain": "notion.so", "ats_slug": "notion", "employee_count": "500+", "founded_year": 2016, "tags": "saas,productivity"},
    {"name": "Figma", "domain": "figma.com", "ats_slug": "figma", "employee_count": "1000+", "founded_year": 2012, "tags": "design,saas"},
    {"name": "Airtable", "domain": "airtable.com", "ats_slug": "airtable", "employee_count": "1000+", "founded_year": 2012, "tags": "saas,database,no-code"},
    {"name": "Postman", "domain": "postman.com", "ats_slug": "postman", "employee_count": "1000+", "founded_year": 2014, "tags": "api,devtools", "india_friendly": "yes"},
    {"name": "Sentry", "domain": "sentry.io", "ats_slug": "sentry", "employee_count": "500+", "founded_year": 2012, "tags": "monitoring,error-tracking,open-source"},
    {"name": "Plaid", "domain": "plaid.com", "ats_slug": "plaid", "employee_count": "1000+", "founded_year": 2013, "tags": "fintech,api,banking"},
    {"name": "Brex", "domain": "brex.com", "ats_slug": "brex", "employee_count": "1000+", "founded_year": 2017, "tags": "fintech,corporate-cards"},
    {"name": "Ramp", "domain": "ramp.com", "ats_slug": "ramp", "employee_count": "500+", "founded_year": 2019, "tags": "fintech,expense-management"},
    {"name": "LaunchDarkly", "domain": "launchdarkly.com", "ats_slug": "launchdarkly", "employee_count": "500+", "founded_year": 2014, "tags": "devtools,feature-flags"},
    {"name": "PlanetScale", "domain": "planetscale.com", "ats_slug": "planetscale", "employee_count": "200+", "founded_year": 2018, "tags": "database,mysql,cloud"},
    {"name": "Temporal", "domain": "temporal.io", "ats_slug": "temporal", "employee_count": "200+", "founded_year": 2019, "tags": "workflow,orchestration,open-source"},
    {"name": "Retool", "domain": "retool.com", "ats_slug": "retool", "employee_count": "500+", "founded_year": 2017, "tags": "internal-tools,low-code"},

    # Remote-first / India-friendly
    {"name": "Deel", "domain": "letsdeel.com", "ats_slug": "deel", "employee_count": "3000+", "founded_year": 2019, "tags": "hr,payroll,remote-first", "india_friendly": "yes"},
    {"name": "Remote.com", "domain": "remote.com", "ats_slug": "remotecom", "employee_count": "1000+", "founded_year": 2019, "tags": "hr,remote-first,global", "india_friendly": "yes"},
    {"name": "Canonical", "domain": "canonical.com", "ats_slug": "canonical", "employee_count": "1000+", "founded_year": 2004, "tags": "ubuntu,open-source,remote-first", "india_friendly": "yes"},
    {"name": "Hotjar", "domain": "hotjar.com", "ats_slug": "hotjar", "employee_count": "500+", "founded_year": 2014, "tags": "analytics,saas,remote-first", "india_friendly": "yes"},
    {"name": "Automattic", "domain": "automattic.com", "ats_slug": "automattic", "employee_count": "2000+", "founded_year": 2005, "tags": "wordpress,open-source,remote-first", "india_friendly": "yes"},
    {"name": "Zapier", "domain": "zapier.com", "ats_slug": "zapier", "employee_count": "800+", "founded_year": 2011, "tags": "automation,saas,remote-first", "india_friendly": "yes"},
    {"name": "Miro", "domain": "miro.com", "ats_slug": "miro", "employee_count": "1800+", "founded_year": 2011, "tags": "collaboration,saas"},
    {"name": "ClickUp", "domain": "clickup.com", "ats_slug": "clickup", "employee_count": "1000+", "founded_year": 2017, "tags": "productivity,saas"},

    # E-commerce / Marketplace
    {"name": "Shopify", "domain": "shopify.com", "ats_slug": "shopify", "employee_count": "10000+", "founded_year": 2006, "tags": "ecommerce,saas"},
    {"name": "Instacart", "domain": "instacart.com", "ats_slug": "instacart", "employee_count": "3000+", "founded_year": 2012, "tags": "delivery,marketplace"},
    {"name": "DoorDash", "domain": "doordash.com", "ats_slug": "doordash", "employee_count": "10000+", "founded_year": 2013, "tags": "delivery,marketplace"},

    # Security / Infra
    {"name": "CrowdStrike", "domain": "crowdstrike.com", "ats_slug": "crowdstrike", "employee_count": "7000+", "founded_year": 2011, "tags": "cybersecurity,cloud", "india_friendly": "yes"},
    {"name": "Snyk", "domain": "snyk.io", "ats_slug": "snyk", "employee_count": "1000+", "founded_year": 2015, "tags": "security,devtools"},
    {"name": "Cockroach Labs", "domain": "cockroachlabs.com", "ats_slug": "cockroach-labs", "employee_count": "500+", "founded_year": 2015, "tags": "database,distributed-sql"},
    {"name": "Sumo Logic", "domain": "sumologic.com", "ats_slug": "sumologic", "employee_count": "1000+", "founded_year": 2010, "tags": "analytics,monitoring,cloud", "india_friendly": "yes"},

    # India-HQ / Large India presence
    {"name": "Freshworks", "domain": "freshworks.com", "ats_slug": "freshworks", "employee_count": "5000+", "founded_year": 2010, "tags": "saas,crm,india-hq", "india_friendly": "yes"},
    {"name": "Razorpay", "domain": "razorpay.com", "ats_slug": "razorpay", "employee_count": "3000+", "founded_year": 2014, "tags": "fintech,payments,india-hq", "india_friendly": "yes"},
    {"name": "Chargebee", "domain": "chargebee.com", "ats_slug": "chargebee", "employee_count": "1000+", "founded_year": 2011, "tags": "saas,billing,india-hq", "india_friendly": "yes"},
    {"name": "Hasura", "domain": "hasura.io", "ats_slug": "hasura", "employee_count": "200+", "founded_year": 2017, "tags": "graphql,database,india-hq", "india_friendly": "yes"},
    {"name": "Zerodha", "domain": "zerodha.com", "ats_slug": "zerodha", "employee_count": "1000+", "founded_year": 2010, "tags": "fintech,trading,india-hq", "india_friendly": "yes"},
    {"name": "Zoho", "domain": "zoho.com", "ats_slug": "zohocorp", "employee_count": "10000+", "founded_year": 1996, "tags": "saas,suite,india-hq", "india_friendly": "yes"},
    {"name": "PhonePe", "domain": "phonepe.com", "ats_slug": "phonepe", "employee_count": "5000+", "founded_year": 2015, "tags": "fintech,payments,india-hq", "india_friendly": "yes"},
    {"name": "Meesho", "domain": "meesho.com", "ats_slug": "meesho", "employee_count": "2000+", "founded_year": 2015, "tags": "ecommerce,social-commerce,india-hq", "india_friendly": "yes"},
    {"name": "Groww", "domain": "groww.in", "ats_slug": "groww", "employee_count": "1000+", "founded_year": 2016, "tags": "fintech,investing,india-hq", "india_friendly": "yes"},
]

# ── Lever Companies ────────────────────────────────────────────
# API: GET https://api.lever.co/v0/postings/{slug}?mode=json

LEVER_COMPANIES = [
    {"name": "Netflix", "domain": "netflix.com", "ats_slug": "netflix", "employee_count": "10000+", "founded_year": 1997, "tags": "streaming,media,entertainment"},
    {"name": "Reddit", "domain": "reddit.com", "ats_slug": "reddit", "employee_count": "2000+", "founded_year": 2005, "tags": "social,media,community"},
    {"name": "Spotify", "domain": "spotify.com", "ats_slug": "spotify", "employee_count": "8000+", "founded_year": 2006, "tags": "music,streaming,media", "india_friendly": "yes"},
    {"name": "Auth0", "domain": "auth0.com", "ats_slug": "auth0", "employee_count": "1000+", "founded_year": 2013, "tags": "identity,security,saas"},
    {"name": "dbt Labs", "domain": "getdbt.com", "ats_slug": "dbt-labs", "employee_count": "500+", "founded_year": 2016, "tags": "data,analytics,open-source"},
    {"name": "Supabase", "domain": "supabase.com", "ats_slug": "supabase", "employee_count": "200+", "founded_year": 2020, "tags": "database,open-source,firebase-alt", "india_friendly": "yes"},
    {"name": "Linear", "domain": "linear.app", "ats_slug": "linear", "employee_count": "100+", "founded_year": 2019, "tags": "project-management,saas,remote-first", "india_friendly": "yes"},
    {"name": "Webflow", "domain": "webflow.com", "ats_slug": "webflow", "employee_count": "1000+", "founded_year": 2013, "tags": "no-code,web-design,saas"},
    {"name": "Weights & Biases", "domain": "wandb.ai", "ats_slug": "wandb", "employee_count": "200+", "founded_year": 2017, "tags": "ml,mlops,ai"},
    {"name": "Loom", "domain": "loom.com", "ats_slug": "useloom", "employee_count": "300+", "founded_year": 2015, "tags": "video,saas,collaboration"},
    {"name": "CircleCI", "domain": "circleci.com", "ats_slug": "circleci", "employee_count": "500+", "founded_year": 2011, "tags": "ci-cd,devops,saas"},
    {"name": "Kong", "domain": "konghq.com", "ats_slug": "kong", "employee_count": "500+", "founded_year": 2009, "tags": "api-gateway,open-source,cloud"},
    {"name": "Outreach", "domain": "outreach.io", "ats_slug": "outreach", "employee_count": "1000+", "founded_year": 2014, "tags": "sales,saas"},
    {"name": "ThoughtSpot", "domain": "thoughtspot.com", "ats_slug": "thoughtspot", "employee_count": "1000+", "founded_year": 2012, "tags": "analytics,bi,saas", "india_friendly": "yes"},
    {"name": "Coda", "domain": "coda.io", "ats_slug": "coda", "employee_count": "500+", "founded_year": 2014, "tags": "productivity,docs,saas"},
    {"name": "Navan", "domain": "navan.com", "ats_slug": "navan", "employee_count": "3000+", "founded_year": 2015, "tags": "travel,expense,saas", "india_friendly": "yes"},
]

# ── Ashby Companies ────────────────────────────────────────────
# API: GET https://api.ashbyhq.com/posting-api/job-board/{slug}

ASHBY_COMPANIES = [
    {"name": "Vercel", "domain": "vercel.com", "ats_slug": "vercel", "employee_count": "500+", "founded_year": 2015, "tags": "cloud,frontend,devtools"},
    {"name": "Resend", "domain": "resend.com", "ats_slug": "resend", "employee_count": "50+", "founded_year": 2022, "tags": "email,api,devtools"},
    {"name": "Cal.com", "domain": "cal.com", "ats_slug": "cal", "employee_count": "100+", "founded_year": 2021, "tags": "scheduling,open-source,saas", "india_friendly": "yes"},
    {"name": "Neon", "domain": "neon.tech", "ats_slug": "neon", "employee_count": "200+", "founded_year": 2021, "tags": "database,postgres,serverless"},
    {"name": "Turso", "domain": "turso.tech", "ats_slug": "turso", "employee_count": "50+", "founded_year": 2022, "tags": "database,sqlite,edge"},
    {"name": "Fly.io", "domain": "fly.io", "ats_slug": "fly-io", "employee_count": "100+", "founded_year": 2017, "tags": "cloud,infrastructure,edge"},
    {"name": "Railway", "domain": "railway.app", "ats_slug": "railway", "employee_count": "50+", "founded_year": 2020, "tags": "cloud,paas,devtools"},
    {"name": "Buildkite", "domain": "buildkite.com", "ats_slug": "buildkite", "employee_count": "200+", "founded_year": 2013, "tags": "ci-cd,devtools"},
    {"name": "Airbyte", "domain": "airbyte.com", "ats_slug": "airbyte", "employee_count": "200+", "founded_year": 2020, "tags": "data,etl,open-source"},
    {"name": "Dagster", "domain": "dagster.io", "ats_slug": "dagster", "employee_count": "100+", "founded_year": 2018, "tags": "data,orchestration,open-source"},
    {"name": "Render", "domain": "render.com", "ats_slug": "render", "employee_count": "200+", "founded_year": 2018, "tags": "cloud,paas,hosting"},
]


def get_all_seed_companies() -> list[dict]:
    """Return all seed companies with ats_platform and defaults set."""
    from core.models import Company

    result = []
    for platform, companies in [
        ("greenhouse", GREENHOUSE_COMPANIES),
        ("lever", LEVER_COMPANIES),
        ("ashby", ASHBY_COMPANIES),
    ]:
        for c in companies:
            entry = {
                "id": Company.make_id(c["name"]),
                "name": c["name"],
                "domain": c.get("domain", ""),
                "careers_url": c.get("careers_url", ""),
                "ats_platform": platform,
                "ats_slug": c.get("ats_slug", ""),
                "founded_year": c.get("founded_year", 0),
                "employee_count": c.get("employee_count", ""),
                "tags": c.get("tags", ""),
                "india_friendly": c.get("india_friendly", "unknown"),
                "last_crawled": "",
                "crawl_status": "active",
                "notes": "",
            }
            result.append(entry)
    return result


async def detect_ats_platform(domain: str) -> dict:
    """Probe a domain to auto-detect which ATS they use."""
    slug = domain.split(".")[0]
    results = {"domain": domain, "slug": slug, "ats_platform": "unknown", "ats_slug": ""}

    async with httpx.AsyncClient(timeout=10) as client:
        # Try Greenhouse
        try:
            resp = await client.get(f"https://boards.greenhouse.io/{slug}/jobs")
            if resp.status_code == 200:
                data = resp.json()
                if "jobs" in data:
                    results.update({"ats_platform": "greenhouse", "ats_slug": slug})
                    return results
        except Exception:
            pass

        # Try Lever
        try:
            resp = await client.get(f"https://api.lever.co/v0/postings/{slug}?mode=json")
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    results.update({"ats_platform": "lever", "ats_slug": slug})
                    return results
        except Exception:
            pass

        # Try Ashby
        try:
            resp = await client.get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
            if resp.status_code == 200:
                data = resp.json()
                if "jobs" in data:
                    results.update({"ats_platform": "ashby", "ats_slug": slug})
                    return results
        except Exception:
            pass

    return results
