"""Email digest sender — composes and sends the daily job digest.

Candidate name, greeting, and the role word in the body copy come from the
active profile's `outreach` section.
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional
from config.settings import (
    SENDER_EMAIL, SENDER_APP_PASSWORD, RECIPIENT_EMAIL, DAILY_JOBS_COUNT,
)
from core.database import (
    get_unemailed_outreach, mark_outreach_emailed, log_email,
)
from core.profile import get_active_profile


def log(msg):
    print(msg, flush=True)


def _escape(s: str) -> str:
    if not s:
        return ""
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


def _format_date(d: str) -> str:
    if not d:
        return ""
    try:
        return datetime.fromisoformat(d.replace("Z", "")).strftime("%b %d, %Y")
    except Exception:
        return d


def _render_card(i: int, item: dict) -> str:
    """Render one outreach card as HTML."""
    import json as _json
    title = _escape(item.get("job_title", ""))
    company = _escape(item.get("company", ""))
    location = _escape(item.get("location", ""))
    salary = _escape(item.get("salary", ""))
    posted = _format_date(item.get("posted_date", ""))
    tech = _escape((item.get("tech_stack") or "")[:100])
    score = item.get("relevance_score", 0)
    india = item.get("india_friendly", "unknown")

    job_url = item.get("job_url") or "#"
    dm_short = _escape(item.get("dm_short", ""))

    # Parse LinkedIn search URLs from notes field
    searches = []
    try:
        searches = _json.loads(item.get("notes", "[]")) or []
    except Exception:
        pass
    if not searches:
        searches = [{"label": "Search", "url": item.get("contact_linkedin", "#")}]

    india_color = {"yes": "#00b894", "maybe": "#fdcb6e", "no": "#e17055"}.get(india, "#8b8fa3")

    # Group searches by category for nicer layout
    colors = {"engineering": "#0a66c2", "executive": "#6c5ce7", "hr": "#00b894"}
    labels = {"engineering": "Engineering", "executive": "C-Level", "hr": "HR / Recruiters"}

    grouped = {}
    for s in searches:
        cat = s.get("category", "engineering")
        grouped.setdefault(cat, []).append(s)

    search_buttons = ""
    for cat in ["engineering", "executive", "hr"]:
        if cat not in grouped:
            continue
        group_buttons = "".join([
            f'<a href="{_escape(s["url"])}" style="display:inline-block;background:{colors[cat]};color:#ffffff;padding:7px 12px;border-radius:5px;text-decoration:none;font-size:11px;font-weight:600;margin:2px 4px 2px 0;">🔍 {_escape(s["label"])}</a>'
            for s in grouped[cat]
        ])
        search_buttons += f'''
        <div style="margin-bottom:8px;">
            <div style="font-size:10px;color:#6b7280;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px;">{labels[cat]}</div>
            {group_buttons}
        </div>
        '''

    return f"""
    <tr><td style="padding:0 0 20px 0;">
    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#ffffff;border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;">
        <tr><td style="padding:18px 20px;background:#f9fafb;border-bottom:1px solid #e5e7eb;">
            <table width="100%"><tr>
                <td style="font-size:11px;color:#6b7280;letter-spacing:0.5px;text-transform:uppercase;">#{i}</td>
                <td align="right">
                    <span style="background:#6c5ce7;color:white;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:600;">Score {score}</span>
                    <span style="background:{india_color}22;color:{india_color};border:1px solid {india_color};padding:3px 10px;border-radius:12px;font-size:11px;font-weight:600;margin-left:4px;">{_escape(india).upper()}</span>
                </td>
            </tr></table>
            <div style="font-size:18px;font-weight:700;color:#111827;margin-top:8px;">{title}</div>
            <div style="font-size:14px;color:#6b7280;margin-top:2px;">{company} &middot; {location}</div>
            {f'<div style="font-size:12px;color:#6b7280;margin-top:4px;">{salary}</div>' if salary else ''}
            {f'<div style="font-size:11px;color:#9ca3af;margin-top:2px;">Posted: {posted}</div>' if posted else ''}
            {f'<div style="font-size:11px;color:#9ca3af;margin-top:4px;">Tech: {tech}</div>' if tech else ''}
        </td></tr>

        <tr><td style="padding:16px 20px;border-bottom:1px solid #e5e7eb;">
            <div style="font-size:11px;color:#6b7280;letter-spacing:0.5px;text-transform:uppercase;margin-bottom:8px;">Find & Message Someone at {company}</div>
            <div>{search_buttons}</div>
        </td></tr>

        <tr><td style="padding:16px 20px;border-bottom:1px solid #e5e7eb;background:#f9fafb;">
            <div style="font-size:11px;color:#6b7280;letter-spacing:0.5px;text-transform:uppercase;margin-bottom:6px;">LinkedIn DM (copy-paste this)</div>
            <div style="background:#ffffff;border:1px solid #e5e7eb;border-radius:6px;padding:12px;font-size:13px;line-height:1.6;color:#111827;font-family:monospace;">
                {dm_short}
            </div>
        </td></tr>

        <tr><td style="padding:16px 20px;text-align:center;">
            <a href="{job_url}" style="display:inline-block;background:#6c5ce7;color:#ffffff;padding:10px 20px;border-radius:6px;text-decoration:none;font-size:13px;font-weight:600;">Apply to Job →</a>
        </td></tr>
    </table>
    </td></tr>
    """


def build_email_html(items: list[dict], candidate_name: str = None,
                     profile: dict = None) -> str:
    profile = profile or get_active_profile()
    out_cfg = profile.get("outreach", {})
    if candidate_name is None:
        candidate_name = out_cfg.get("candidate_name") or "there"
    role_word = out_cfg.get("email_digest_subject_role") or "matching"
    greeting_title = out_cfg.get("email_greeting") or "Your Daily Job Digest"

    today = datetime.now().strftime("%B %d, %Y")
    cards = "".join(_render_card(i + 1, item) for i, item in enumerate(items))

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f3f4f6;padding:30px 10px;">
<tr><td align="center">

<table width="640" cellpadding="0" cellspacing="0" border="0" style="max-width:640px;">

    <tr><td style="padding-bottom:24px;text-align:center;">
        <div style="font-size:26px;font-weight:700;color:#111827;">{_escape(greeting_title)}</div>
        <div style="font-size:14px;color:#6b7280;margin-top:4px;">{today} &middot; {len(items)} opportunities</div>
    </td></tr>

    <tr><td style="padding:16px 20px;background:#eef2ff;border:1px solid #c7d2fe;border-radius:10px;margin-bottom:20px;">
        <div style="font-size:13px;color:#3730a3;line-height:1.6;">
            <strong>Hey {_escape(candidate_name)} 👋</strong><br>
            Here are {len(items)} fresh {_escape(role_word)} roles that match your profile. For each one, I've found the hiring manager's LinkedIn and written a personalized DM.<br><br>
            <strong>Your move:</strong> Click "Open LinkedIn Profile" → send connection request with the DM → apply to the job. Takes ~2 min per job.
        </div>
    </td></tr>

    <tr><td style="height:16px;"></td></tr>

    {cards}

    <tr><td style="padding:24px 20px;text-align:center;font-size:12px;color:#6b7280;border-top:1px solid #e5e7eb;">
        This is an automated daily digest. Good luck — go get them 💪
    </td></tr>

</table>

</td></tr>
</table>
</body>
</html>"""


def build_email_text(items: list[dict], candidate_name: str = None,
                     profile: dict = None) -> str:
    """Plain text fallback."""
    profile = profile or get_active_profile()
    out_cfg = profile.get("outreach", {})
    if candidate_name is None:
        candidate_name = out_cfg.get("candidate_name") or "there"
    greeting_title = out_cfg.get("email_greeting") or "Your Daily Job Digest"
    today = datetime.now().strftime("%B %d, %Y")
    lines = [
        f"{greeting_title} - {today}",
        f"{len(items)} opportunities for {candidate_name}",
        "=" * 60,
        "",
    ]
    for i, item in enumerate(items, 1):
        lines.extend([
            f"#{i} - {item.get('job_title', '')} @ {item.get('company', '')}",
            f"Score: {item.get('relevance_score', 0)} | Location: {item.get('location', '')}",
            f"Contact: {item.get('contact_name', '')} ({item.get('contact_position', '')})",
            f"LinkedIn: {item.get('contact_linkedin', '')}",
            f"Apply: {item.get('job_url', '')}",
            f"",
            f"DM to send:",
            f"  {item.get('dm_short', '')}",
            "",
            "-" * 60,
            "",
        ])
    return "\n".join(lines)


def send_daily_digest(limit: int = None, dry_run: bool = False) -> dict:
    """Send the daily digest email with top unemailed outreach items."""
    limit = limit or DAILY_JOBS_COUNT

    profile = get_active_profile()
    out_cfg = profile.get("outreach") or {}
    # Profile overrides env defaults for both sender and recipient.
    sender = (out_cfg.get("sender_email") or "").strip() or SENDER_EMAIL
    recipient = (out_cfg.get("recipient_email") or "").strip() or RECIPIENT_EMAIL

    if not sender or not SENDER_APP_PASSWORD:
        return {"error": "Sender email or SENDER_APP_PASSWORD not configured"}
    if not recipient:
        return {"error": "Recipient email not configured (set on profile or RECIPIENT_EMAIL in .env)"}

    items = get_unemailed_outreach(limit=limit)
    if not items:
        return {"sent": 0, "message": "No new outreach items to send"}

    today = datetime.now().strftime("%b %d")
    role_word = out_cfg.get("email_digest_subject_role") or "job"
    subject = f"Daily {role_word.title()} Digest - {len(items)} opportunities ({today})"

    html = build_email_html(items, profile=profile)
    text = build_email_text(items, profile=profile)

    if dry_run:
        return {
            "dry_run": True,
            "items_count": len(items),
            "subject": subject,
            "sender": sender,
            "recipient": recipient,
            "html_length": len(html),
            "preview": [{"title": i["job_title"], "company": i["company"]} for i in items],
        }

    from email.header import Header
    msg = MIMEMultipart("alternative")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = sender
    msg["To"] = recipient
    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender, SENDER_APP_PASSWORD)
            server.send_message(msg)

        outreach_ids = [i["id"] for i in items]
        mark_outreach_emailed(outreach_ids)
        log_email(recipient, subject, len(items), outreach_ids, "sent")
        log(f"Sent daily digest: {len(items)} items from {sender} to {recipient}")

        return {"sent": len(items), "subject": subject, "sender": sender, "recipient": recipient}
    except Exception as e:
        log(f"Email send failed: {e}")
        log_email(recipient, subject, len(items),
                   [i["id"] for i in items], "failed", str(e))
        return {"error": str(e)}


def generate_outreach_for_top_jobs(limit: int = 15, min_score: int = 40,
                                   india_friendly: str = "maybe",
                                   seen_after: Optional[str] = None) -> int:
    """Create outreach items for the highest-scoring jobs that don't have one yet.
    If `seen_after` is given, only jobs refreshed at/after that timestamp qualify —
    use this to scope generation to a specific collection run.
    Returns the count generated. Stamps a batch timestamp so the UI can
    separate 'new' vs 'old' outreach."""
    from core.database import (
        get_jobs, outreach_exists_for_job, insert_outreach,
        set_last_outreach_batch_at,
    )
    from core.hunter import build_linkedin_searches, generate_dm_template
    import hashlib, json

    profile = get_active_profile()
    profile_id = profile.get("_id")

    top_jobs = get_jobs(min_score=min_score, india_friendly=india_friendly,
                         seen_after=seen_after, limit=limit * 5)
    candidates = [j for j in top_jobs if not outreach_exists_for_job(j["id"])][:limit]

    # All items in this run share the same timestamp so batch filtering is
    # exact ("new" = created_at >= this timestamp).
    batch_ts = datetime.utcnow().isoformat()
    generated = 0
    for job in candidates:
        try:
            searches = build_linkedin_searches(job["company"], profile=profile)
            dms = generate_dm_template(job, profile=profile)
            primary_url = searches[0]["url"] if searches else ""

            outreach_id = hashlib.md5(f"{job['id']}|linkedin".encode()).hexdigest()
            insert_outreach({
                "id": outreach_id,
                "job_id": job["id"],
                "job_title": job["title"],
                "company": job["company"],
                "company_domain": job.get("company_domain", ""),
                "contact_name": "[Search LinkedIn]",
                "contact_position": "Engineering Manager / Tech Lead / Head of Eng",
                "contact_linkedin": primary_url,
                "dm_short": dms["short"],
                "dm_long": dms["long"],
                "status": "pending",
                "messaged_at": "", "replied_at": "", "followed_up_at": "",
                "created_at": batch_ts,
                "notes": json.dumps(searches),
                "emailed_at": "",
                "profile_id": profile_id,
            })
            generated += 1
        except Exception as e:
            log(f"  Skipped {job.get('company')}: {e}")
            continue

    if generated > 0:
        set_last_outreach_batch_at(batch_ts)
    return generated


async def run_daily_pipeline(send: bool = True) -> dict:
    """Full daily pipeline: collect jobs → generate outreach → send email."""
    from core.collector import run_collection

    log("=== Daily Pipeline Start ===")

    log("Step 1: Collecting jobs...")
    collect_stats = await run_collection(include_companies=True)
    log(f"  Fetched: {collect_stats.get('fetched', 0)}, New: {collect_stats.get('new', 0)}")

    log("Step 2: Generating outreach...")
    generated = generate_outreach_for_top_jobs()
    log(f"  Generated {generated} new outreach items")

    email_result = {"skipped": True}
    if send:
        log("Step 3: Sending email...")
        email_result = send_daily_digest()
        log(f"  Email: {email_result}")

    log("=== Daily Pipeline Complete ===")
    return {
        "collection": {"new": collect_stats.get("new", 0)},
        "outreach_generated": generated,
        "email": email_result,
    }
