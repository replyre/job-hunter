"""Google Sheets integration — push jobs to a sheet for n8n / outreach workflows."""

import gspread
from google.oauth2.service_account import Credentials
from core.database import get_jobs

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Column headers that go into the sheet
HEADERS = [
    "Title", "Company", "Location", "India Friendly", "Location Note",
    "Relevance Score", "Tech Stack", "Experience Level", "Salary",
    "Job URL", "Source", "Posted Date", "Status", "Company Domain",
]


def _get_client(creds_file: str) -> gspread.Client:
    creds = Credentials.from_service_account_file(creds_file, scopes=SCOPES)
    return gspread.authorize(creds)


def _job_to_row(job: dict) -> list:
    return [
        job.get("title", ""),
        job.get("company", ""),
        job.get("location", ""),
        job.get("india_friendly", "unknown"),
        job.get("location_note", ""),
        job.get("relevance_score", 0),
        job.get("tech_stack", ""),
        job.get("experience_level", ""),
        job.get("salary", ""),
        job.get("url", ""),
        job.get("source", ""),
        job.get("posted_date", ""),
        job.get("status", "new"),
        job.get("company_domain", ""),
    ]


def export_to_sheet(
    creds_file: str,
    spreadsheet_id: str,
    sheet_name: str = "Jobs",
    min_score: int = 0,
    india_friendly: str = None,
    source: str = None,
    search: str = None,
    tech: str = None,
    mode: str = "replace",
) -> dict:
    """
    Export filtered jobs to a Google Sheet.

    Args:
        creds_file: path to service account JSON
        spreadsheet_id: the Google Sheet ID (from the URL)
        sheet_name: worksheet tab name
        min_score: minimum relevance score
        india_friendly: 'yes', 'maybe', 'no', or None
        source: filter by source
        search: search query
        tech: tech filter
        mode: 'replace' (clear + rewrite) or 'append' (add new rows)

    Returns:
        dict with export stats
    """
    client = _get_client(creds_file)
    spreadsheet = client.open_by_key(spreadsheet_id)

    # Get or create worksheet
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=len(HEADERS))

    # Fetch jobs from DB with filters
    jobs = get_jobs(
        min_score=min_score,
        india_friendly=india_friendly,
        source=source,
        search=search,
        tech=tech,
        limit=500,
    )

    rows = [_job_to_row(j) for j in jobs]

    if mode == "replace":
        worksheet.clear()
        worksheet.update(values=[HEADERS] + rows, range_name="A1")
    else:
        # Append mode — check if headers exist
        existing = worksheet.get_all_values()
        if not existing:
            worksheet.update(values=[HEADERS], range_name="A1")
        worksheet.append_rows(rows, value_input_option="USER_ENTERED")

    # Auto-format header row bold
    worksheet.format("A1:N1", {
        "textFormat": {"bold": True},
        "backgroundColor": {"red": 0.15, "green": 0.15, "blue": 0.2},
    })

    return {
        "exported": len(rows),
        "sheet_name": sheet_name,
        "spreadsheet_id": spreadsheet_id,
        "mode": mode,
    }
