"""Rule-based relevance scorer. No API key needed.
Scores jobs 0-100 based on title, description, and tech stack match.
Also detects whether a job is India-remote-friendly."""

from config.settings import (
    RELEVANT_TECH,
    TITLE_KEYWORDS_POSITIVE,
    TITLE_KEYWORDS_NEGATIVE,
    LOCATION_INDIA_POSITIVE,
    LOCATION_INDIA_NEGATIVE,
    TIMEZONE_COMPATIBLE,
    TIMEZONE_INCOMPATIBLE,
)


def extract_tech_stack(text: str) -> list[str]:
    """Extract matching tech keywords from text."""
    text_lower = text.lower()
    return [tech for tech in RELEVANT_TECH if tech in text_lower]


def estimate_experience_level(text: str) -> str:
    """Guess experience level from description."""
    text_lower = text.lower()
    if any(w in text_lower for w in ["intern", "internship", "trainee", "entry level", "entry-level", "0-1 year"]):
        return "junior"
    if any(w in text_lower for w in ["senior", "sr.", "lead", "principal", "staff", "8+ years", "10+ years"]):
        return "senior"
    if any(w in text_lower for w in ["mid", "middle", "3+ years", "2+ years", "4+ years", "5+ years", "3-5 years", "2-4 years"]):
        return "mid"
    return "mid"


def check_india_friendly(location: str, description: str) -> dict:
    """
    Determine if a remote job is accessible from India.
    Returns:
        result: 'yes' | 'no' | 'maybe'
        note: explanation string
    """
    full_text = f"{location} {description}".lower()
    loc_lower = location.lower()

    positive_hits = [kw for kw in LOCATION_INDIA_POSITIVE if kw in full_text]
    negative_hits = [kw for kw in LOCATION_INDIA_NEGATIVE if kw in full_text]
    tz_good = [kw for kw in TIMEZONE_COMPATIBLE if kw in full_text]
    tz_bad = [kw for kw in TIMEZONE_INCOMPATIBLE if kw in full_text]

    # Strong NO signals
    if negative_hits:
        return {
            "result": "no",
            "note": f"Restricted: {', '.join(negative_hits[:3])}",
        }
    if tz_bad:
        return {
            "result": "no",
            "note": f"Timezone mismatch: {', '.join(tz_bad[:2])}",
        }

    # Strong YES signals — explicitly mentions India or global
    india_direct = any(kw in full_text for kw in [
        "india", "bangalore", "bengaluru", "mumbai", "hyderabad",
        "pune", "delhi", "chennai", "kolkata", "noida", "gurgaon",
        "gurugram", "remote - india",
    ])
    if india_direct:
        return {
            "result": "yes",
            "note": f"India mentioned: {', '.join(positive_hits[:3])}",
        }

    global_signals = any(kw in full_text for kw in [
        "worldwide", "anywhere", "global", "work from anywhere",
        "location independent", "globally distributed",
    ])
    if global_signals:
        note_parts = [h for h in positive_hits if h in [
            "worldwide", "anywhere", "global", "work from anywhere",
            "location independent", "globally distributed",
        ]]
        return {
            "result": "yes",
            "note": f"Global remote: {', '.join(note_parts[:3])}",
        }

    # MAYBE — APAC or timezone overlap without blockers
    if any(kw in full_text for kw in ["apac", "asia", "asia pacific", "asia-pacific"]):
        return {
            "result": "yes",
            "note": f"APAC region: {', '.join(positive_hits[:3])}",
        }
    if tz_good:
        return {
            "result": "maybe",
            "note": f"Compatible timezone: {', '.join(tz_good[:2])}",
        }

    # Generic "Remote" with no location clues
    if "remote" in loc_lower and not any(
        region in loc_lower for region in [
            "us", "usa", "uk", "europe", "eu", "canada",
            "germany", "france", "spain", "australia",
        ]
    ):
        return {
            "result": "maybe",
            "note": "Remote — no region specified, may accept India",
        }

    # Location specifies a non-India country
    non_india_regions = [
        "united states", "usa", "us", "canada", "uk",
        "united kingdom", "europe", "eu", "germany",
        "france", "australia", "spain", "netherlands",
    ]
    if any(r in loc_lower for r in non_india_regions):
        return {
            "result": "no",
            "note": f"Location restricted to: {location}",
        }

    return {
        "result": "maybe",
        "note": "No clear location restriction found",
    }


def score_job(title: str, description: str, location: str = "") -> dict:
    """Score a job 0-100. Returns score + metadata + india_friendly."""
    score = 0
    reasons = []
    red_flags = []
    full_text = f"{title} {description}".lower()

    # Title relevance (0-35 points)
    title_lower = title.lower()
    title_matches = [kw for kw in TITLE_KEYWORDS_POSITIVE if kw in title_lower]
    if title_matches:
        title_points = min(len(title_matches) * 12, 35)
        score += title_points
        reasons.append(f"Title match: {', '.join(title_matches)}")

    title_negatives = [kw for kw in TITLE_KEYWORDS_NEGATIVE if kw in title_lower]
    if title_negatives:
        penalty = len(title_negatives) * 15
        score -= penalty
        red_flags.append(f"Title contains: {', '.join(title_negatives)}")

    # Tech stack match (0-35 points)
    tech_found = extract_tech_stack(full_text)
    core_tech = [t for t in tech_found if t in ("python", "django", "fastapi", "flask")]
    secondary_tech = [t for t in tech_found if t not in core_tech]

    if core_tech:
        score += min(len(core_tech) * 12, 25)
        reasons.append(f"Core tech: {', '.join(core_tech)}")
    if secondary_tech:
        score += min(len(secondary_tech) * 3, 10)
        reasons.append(f"Related tech: {', '.join(secondary_tech)}")

    # Experience level (0-15 points)
    exp_level = estimate_experience_level(full_text)
    if exp_level == "mid":
        score += 15
        reasons.append("Experience level: mid (3+ years match)")
    elif exp_level == "senior":
        score += 10
        reasons.append("Experience level: senior (may be overqualified)")
    elif exp_level == "junior":
        score -= 10
        red_flags.append("Junior/entry-level role")

    # Backend signals in description (0-15 points)
    backend_signals = ["api", "backend", "back-end", "server-side", "microservice",
                       "database", "rest", "graphql", "endpoint"]
    backend_matches = [s for s in backend_signals if s in full_text]
    if backend_matches:
        score += min(len(backend_matches) * 4, 15)
        reasons.append(f"Backend signals: {', '.join(backend_matches[:5])}")

    # India-friendly check
    india_check = check_india_friendly(location, description)

    # Clamp score
    score = max(0, min(100, score))

    return {
        "score": score,
        "tech_stack": tech_found,
        "experience_level": exp_level,
        "reasons": reasons,
        "red_flags": red_flags,
        "india_friendly": india_check["result"],
        "location_note": india_check["note"],
    }
