"""LinkedIn search URL builder + DM generator.

All candidate-specific text (name, bio, achievements) lives in the active
profile's `outreach` section. See core/profile.py.
"""

import urllib.parse

from core.profile import get_active_profile


def build_linkedin_searches(company: str, profile: dict = None) -> list[dict]:
    """Build LinkedIn people search URLs using the profile's search titles."""
    profile = profile or get_active_profile()
    titles = profile["outreach"].get("linkedin_search_titles") or []

    base = "https://www.linkedin.com/search/results/people/"
    searches = []
    for entry in titles:
        title = entry.get("title", "")
        if not title:
            continue
        label = entry.get("label") or title
        category = entry.get("category") or "engineering"
        keywords = f"{company} {title}"
        url = f"{base}?keywords={urllib.parse.quote(keywords)}"
        searches.append({
            "label": label,
            "title": title,
            "category": category,
            "url": url,
        })
    return searches


def build_linkedin_search_url(first_name: str, last_name: str, company: str) -> str:
    """Legacy: Build LinkedIn search from a specific person's name."""
    query = f"{first_name} {last_name} {company}".strip()
    return f"https://www.linkedin.com/search/results/people/?keywords={urllib.parse.quote(query)}"


def _safe_format(template: str, tokens: dict) -> str:
    """.format() that tolerates missing tokens — unknown placeholders render empty."""
    class _Silent(dict):
        def __missing__(self, key):
            return ""
    try:
        return template.format_map(_Silent(tokens))
    except (IndexError, KeyError, ValueError):
        return template


def generate_dm_template(job: dict, contact: dict = None,
                        profile: dict = None) -> dict:
    """Generate a short + long LinkedIn DM using the profile's templates."""
    profile = profile or get_active_profile()
    out_cfg = profile["outreach"]

    candidate_name = out_cfg.get("candidate_name") or "[Your Name]"
    candidate_core = [t.lower() for t in (out_cfg.get("candidate_core_tech") or [])]
    candidate_extra = [t.lower() for t in (out_cfg.get("candidate_extra_tech") or [])]
    bio_short_template = out_cfg.get("bio_short") or ""
    achievements = out_cfg.get("achievements") or []
    dm_short_template = out_cfg.get("dm_short_template") or ""
    dm_long_template = out_cfg.get("dm_long_template") or ""

    first_name = ""
    if contact and contact.get("first_name"):
        first_name = contact["first_name"]
    greeting = f"Hi {first_name}" if first_name else "Hi there"

    title = (job.get("title") or "this role").strip()
    if " - " in title:
        title = title.split(" - ")[0]
    company = (job.get("company") or "your team").strip()

    tech_stack_str = job.get("tech_stack", "") or ""
    tech_bits = [t.strip().lower() for t in tech_stack_str.split(",") if t.strip()]
    matched_core = [t for t in tech_bits if t in candidate_core]

    if matched_core:
        stack_phrase = "/".join(matched_core[:2]).title()
    elif candidate_core:
        stack_phrase = "/".join(candidate_core[:2]).title()
    elif candidate_extra:
        stack_phrase = "/".join(candidate_extra[:2]).title()
    else:
        stack_phrase = "the stack"

    bio_short = _safe_format(bio_short_template, {"stack": stack_phrase})
    achievements_block = "\n\n".join(achievements)

    tokens = {
        "greeting": greeting,
        "company": company,
        "title": title,
        "stack": stack_phrase,
        "bio_short": bio_short,
        "achievements": achievements_block,
        "candidate_name": candidate_name,
    }

    short = _safe_format(dm_short_template, tokens).strip()
    long_ = _safe_format(dm_long_template, tokens).strip()

    # Hard cap short DM (LinkedIn connection note limit = 300 chars)
    if len(short) > 300:
        short = short[:297].rstrip() + "..."

    return {"short": short, "long": long_}


# ── Deprecated: Hunter API (kept for backward-compatible imports) ──

async def find_engineering_contacts(domain: str, api_key: str = None, limit: int = 20) -> dict:
    """DEPRECATED. No longer used — we use LinkedIn search URLs instead."""
    return {"contacts": [], "total_found": 0, "credits_used": 0,
            "note": "Hunter deprecated — using LinkedIn searches"}
