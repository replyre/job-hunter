"""Rule-based relevance scorer. No API key needed.
Scores jobs 0-100 based on title, description, and tech stack match.
Also detects whether a job is India-remote-friendly.

All preferences (keyword lists, weights, experience target, candidate core tech)
come from the active profile (see core.profile). Callers can pass `profile=`
to use a specific profile for a batch — otherwise the active one is looked up.
"""

from core.profile import get_active_profile


def extract_tech_stack(text: str, profile: dict = None) -> list[str]:
    """Extract matching tech keywords from text."""
    profile = profile or get_active_profile()
    tech_list = profile["search"].get("relevant_tech") or []
    text_lower = text.lower()
    return [tech for tech in tech_list if tech in text_lower]


def estimate_experience_level(text: str) -> str:
    """Guess experience level from description.

    These keyword lists are linguistic patterns — not user preferences — so
    they stay hardcoded. The profile decides how the detected level is
    *scored* via experience_bonuses, not how it's detected.
    """
    text_lower = text.lower()
    if any(w in text_lower for w in [
        "intern", "internship", "trainee", "entry level", "entry-level",
        "0-1 year", "0-2 years", "fresher", "new grad", "graduate",
        "campus", "freshers", "b.tech", "b.e.", "mca",
    ]):
        # Fine-grained: distinguish "junior/fresher" from "intern/trainee"
        if any(w in text_lower for w in ["intern", "internship", "trainee"]):
            return "fresher"
        return "fresher"
    if any(w in text_lower for w in [
        "senior", "sr.", "lead", "principal", "staff",
        "8+ years", "10+ years", "15+ years",
    ]):
        return "senior"
    if any(w in text_lower for w in [
        "junior", "jr.", "1+ year", "1-2 years",
    ]):
        return "junior"
    if any(w in text_lower for w in [
        "mid", "middle", "3+ years", "2+ years", "4+ years", "5+ years",
        "3-5 years", "2-4 years", "4-6 years",
    ]):
        return "mid"
    return "mid"


def check_india_friendly(location: str, description: str,
                         profile: dict = None) -> dict:
    """Determine if a remote job is accessible from India.
    Returns:
        result: 'yes' | 'no' | 'maybe'
        note: explanation string
    """
    profile = profile or get_active_profile()
    loc_cfg = profile["location"]
    india_pos = loc_cfg.get("india_positive") or []
    india_neg = loc_cfg.get("india_negative") or []
    tz_good_list = loc_cfg.get("timezone_compatible") or []
    tz_bad_list = loc_cfg.get("timezone_incompatible") or []

    full_text = f"{location} {description}".lower()
    loc_lower = location.lower()

    positive_hits = [kw for kw in india_pos if kw in full_text]
    negative_hits = [kw for kw in india_neg if kw in full_text]
    tz_good = [kw for kw in tz_good_list if kw in full_text]
    tz_bad = [kw for kw in tz_bad_list if kw in full_text]

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


def score_job(title: str, description: str, location: str = "",
              profile: dict = None) -> dict:
    """Score a job 0-100 against the active (or passed) profile."""
    profile = profile or get_active_profile()
    search = profile["search"]
    scoring = profile["scoring"]
    weights = scoring.get("weights") or {}
    w_title = int(weights.get("title", 35))
    w_tech = int(weights.get("tech", 35))
    w_exp = int(weights.get("experience", 15))
    w_signal = int(weights.get("signal", 15))

    pos_titles = search.get("title_keywords_positive") or []
    neg_titles = search.get("title_keywords_negative") or []
    core_tech_list = scoring.get("core_tech") or []
    signal_list = scoring.get("backend_signals") or []
    exp_bonuses = scoring.get("experience_bonuses") or {}
    exp_target = scoring.get("experience_target", "mid")

    score = 0
    reasons: list[str] = []
    red_flags: list[str] = []
    full_text = f"{title} {description}".lower()
    title_lower = title.lower()

    # Title relevance
    title_matches = [kw for kw in pos_titles if kw in title_lower]
    if title_matches:
        pts = min(len(title_matches) * 12, w_title)
        score += pts
        reasons.append(f"Title match: {', '.join(title_matches[:6])}")

    title_negatives = [kw for kw in neg_titles if kw in title_lower]
    if title_negatives:
        penalty = len(title_negatives) * 15
        score -= penalty
        red_flags.append(f"Title contains: {', '.join(title_negatives[:4])}")

    # Tech stack: split into core / secondary using profile-declared core_tech.
    # Budget split: ~70% of tech weight for core, ~30% for secondary.
    tech_found = extract_tech_stack(full_text, profile=profile)
    core_tech = [t for t in tech_found if t in core_tech_list]
    secondary_tech = [t for t in tech_found if t not in core_tech]

    core_budget = max(0, int(round(w_tech * 0.71)))
    secondary_budget = max(0, w_tech - core_budget)

    if core_tech:
        score += min(len(core_tech) * 12, core_budget)
        reasons.append(f"Core tech: {', '.join(core_tech)}")
    if secondary_tech:
        score += min(len(secondary_tech) * 3, secondary_budget)
        reasons.append(f"Related tech: {', '.join(secondary_tech[:8])}")

    # Experience: lookup via experience_bonuses[target][detected], scale by w_exp.
    exp_level = estimate_experience_level(full_text)
    row = exp_bonuses.get(exp_target) or {}
    # Bonus table expresses preference as -15..+15. Scale by (w_exp / 15) so a
    # profile can dial experience_weight up or down proportionally.
    raw_bonus = int(row.get(exp_level, 0))
    scaled_bonus = int(round(raw_bonus * (w_exp / 15.0)))
    if scaled_bonus > 0:
        score += scaled_bonus
        reasons.append(f"Experience match: {exp_level} (target={exp_target}) +{scaled_bonus}")
    elif scaled_bonus < 0:
        score += scaled_bonus
        red_flags.append(f"Experience mismatch: {exp_level} (target={exp_target}) {scaled_bonus}")
    else:
        reasons.append(f"Experience: {exp_level} (target={exp_target})")

    # Domain signals (profile-defined — "backend_signals" key kept for
    # migration; semantically means "positive domain keywords in description")
    signal_matches = [s for s in signal_list if s in full_text]
    if signal_matches:
        score += min(len(signal_matches) * 4, w_signal)
        reasons.append(f"Signals: {', '.join(signal_matches[:5])}")

    # India-friendly
    india_check = check_india_friendly(location, description, profile=profile)

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
