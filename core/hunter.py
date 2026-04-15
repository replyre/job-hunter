"""LinkedIn search URL builder + DM generator.
Previously used Hunter.io — now uses LinkedIn people search directly (free, unlimited)."""

import urllib.parse


# Title filters we build search URLs for (ranked priority)
SEARCH_TITLES = [
    ("Engineering Manager", "eng-manager"),
    ("Tech Lead", "tech-lead"),
    ("Head of Engineering", "head-eng"),
    ("Engineering Director", "eng-director"),
    ("Backend", "backend"),
    ("CTO", "cto"),
    ("VP Engineering", "vp-eng"),
]


def build_linkedin_searches(company: str) -> list[dict]:
    """Build multiple LinkedIn people search URLs for a company.
    Covers engineering decision makers + HR/recruiters + C-level."""
    base = "https://www.linkedin.com/search/results/people/"

    # All search angles — grouped by category
    search_configs = [
        # Engineering leadership (best response rate)
        ("Engineering Manager", "Eng Manager", "engineering"),
        ("Tech Lead", "Tech Lead", "engineering"),
        ("Head of Engineering", "Head of Eng", "engineering"),
        # C-level (small companies)
        ("CTO", "CTO", "executive"),
        ("CEO Founder", "CEO / Founder", "executive"),
        # HR / Recruiters (gatekeepers but worth trying)
        ("Technical Recruiter", "Tech Recruiter", "hr"),
        ("HR Manager", "HR Manager", "hr"),
    ]

    searches = []
    for title, short_label, category in search_configs:
        keywords = f"{company} {title}"
        url = f"{base}?keywords={urllib.parse.quote(keywords)}"
        searches.append({
            "label": short_label,
            "title": title,
            "category": category,
            "url": url,
        })

    return searches


def build_linkedin_search_url(first_name: str, last_name: str, company: str) -> str:
    """Legacy: Build LinkedIn search from a specific person's name.
    Kept for backwards compatibility."""
    query = f"{first_name} {last_name} {company}".strip()
    return f"https://www.linkedin.com/search/results/people/?keywords={urllib.parse.quote(query)}"


def generate_dm_template(job: dict, contact: dict = None, candidate_name: str = "Parmanand") -> dict:
    """Generate a personalized LinkedIn DM.
    Works without a specific contact name (uses 'Hi there' / 'Hi [name]' if known).
    """
    first_name = ""
    if contact and contact.get("first_name"):
        first_name = contact["first_name"]

    greeting = f"Hi {first_name}" if first_name else "Hi there"

    title = (job.get("title") or "this role").strip()
    if " - " in title:
        title = title.split(" - ")[0]
    company = (job.get("company") or "your team").strip()

    # Match Parmanand's tech stack against job
    tech_stack = job.get("tech_stack", "")
    tech_bits = [t.strip() for t in tech_stack.split(",") if t.strip()]

    candidate_core = ["python", "django", "fastapi", "drf"]
    candidate_extra = ["postgresql", "redis", "aws", "docker", "microservices"]

    matched_core = [t for t in tech_bits if t.lower() in candidate_core]

    if matched_core:
        stack_phrase = "/".join(matched_core[:2]).title()
    else:
        stack_phrase = "Python/Django"

    # Short DM for connection note (under 300 chars)
    short = (
        f"{greeting}, I noticed {company} is hiring for {title}. "
        f"I have 3+ years building {stack_phrase} backends — shipped a healthcare "
        f"SaaS serving 5,000+ users with sub-200ms APIs. Would love to connect."
    )
    if len(short) > 300:
        short = (
            f"{greeting}, saw {title} opening at {company}. "
            f"3+ yrs {stack_phrase} backend experience, shipped healthcare SaaS. "
            f"Would love to connect."
        )

    # Long DM for direct messages
    long = (
        f"{greeting},\n\n"
        f"Noticed {company} is hiring for {title}. The stack caught my eye — "
        f"I've been shipping {stack_phrase} backends for 3+ years.\n\n"
        f"Current role: Backend Developer at DoctusTech, a healthcare SaaS serving "
        f"5,000+ US medical professionals. I architected the Django/DRF platform, "
        f"integrated 3 microservices, and cut API response times 50% with Redis caching.\n\n"
        f"Previously built multitenant SaaS + Stripe integrations processing 2,000+ "
        f"monthly transactions.\n\n"
        f"Open to a 15-min chat to see if there's a fit?\n\n"
        f"Thanks,\n{candidate_name}"
    )

    return {"short": short[:300], "long": long}


# ── Deprecated: Hunter API (kept for reference, no longer used) ──

async def find_engineering_contacts(domain: str, api_key: str = None, limit: int = 20) -> dict:
    """DEPRECATED. No longer used — we use LinkedIn search URLs instead."""
    return {"contacts": [], "total_found": 0, "credits_used": 0,
            "note": "Hunter deprecated — using LinkedIn searches"}
