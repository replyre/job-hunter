# Feature Reference

Every page, button, and feature explained.

---

## Jobs Page (`/`)

### Header
- **Nav tabs**: Jobs | Outreach
- **JSearch usage counter**: Shows `X/200` requests used this month
- **Search Queries button**: Opens modal to manage JSearch search terms
- **Export to Sheets button**: Export filtered jobs to Google Sheet (requires setup)
- **Collect Jobs button**: Runs the full collection pipeline

### Stats Bar (live)
Shows counts for:
- Total jobs in DB
- Avg relevance score
- India-friendly breakdown (yes/maybe/no)
- Top sources

### Filters Row
| Filter | Purpose |
|---|---|
| Search | Free text (title, company, description) |
| Source | greenhouse:stripe, jsearch, remotive, etc. |
| Status | new / reviewed / applied / stale |
| Min Score | 30+ / 50+ / 60+ / 70+ |
| India Remote | India Friendly / India + Maybe / Not India |
| Location | Free text (Bangalore, Remote, etc.) |
| Tech | Filter by tech stack keyword (python, django) |

### Job Cards
Each card shows:

```
[☑]  [Score]   Title
               Company · Location · Source · Salary · Posted date · [India badge] · Last seen
               [tech tags]
                                                            [status badge] [📧 Marked]
```

**Checkbox (leftmost)**: Mark job for email — prioritized in next daily digest
**Score circle (color)**:
- Green (60+) — strong match
- Yellow (35-59) — partial match
- Red (<35) — weak match

**Click card** (anywhere except checkbox) → opens detail modal

### Job Detail Modal
- Full job description (scrollable)
- All metadata + India-friendly explanation
- Buttons:
  - **Mark Reviewed** — you've looked at it
  - **Mark Applied** — submitted application (protects from auto-delete)
  - **Mark Stale** — not worth pursuing
  - **Apply** — opens job URL in new tab
  - **Close** — dismiss modal

---

## Search Queries Modal

Click **"Search Queries"** button on Jobs page.

Shows all JSearch queries. Each row:
- **On/Off toggle** — disable queries to save API credits
- **Query text** — editable inline
- **Country** — IN / US / GB / CA / DE / SG
- **Posted** — today / 3days / week / month / all
- **Remote only** — checkbox
- **Delete** — removes the query

**Add New Query section:**
- Query input (e.g., "python backend senior")
- Country dropdown
- Posted timeframe
- Remote-only checkbox
- **Add** button

**How it works:**
- Every time "Collect Jobs" runs, all enabled queries fire
- Each query = 1 JSearch credit
- Default 6 queries = 6 credits per run (about 30 runs/month with free tier)

---

## Outreach Page (`/outreach`)

### Header
- **Nav tabs**: Jobs | **Outreach** (active)
- **Hunter status**: Shows API configuration (not currently used)
- **Email status**: Shows where daily digest will be sent + time
- **Preview Email button**: Dry-run what the next email would contain
- **Send Email Now button**: Manually trigger the daily email
- **Find Contacts for Top Jobs button**: Generate outreach for top 15 jobs

### Stats Bar
- Total outreach items
- Pending (not yet messaged)
- Messaged (DM sent)
- Replied (got a reply)
- Followed Up

### Outreach Cards
Each card shows:

```
Senior Backend Engineer @ Razorpay                              [Pending]
Created Apr 14, 10:30 AM

Find someone at Razorpay:
  Engineering
    [🔍 Eng Manager] [🔍 Tech Lead] [🔍 Head of Eng]
  C-Level
    [🔍 CTO] [🔍 CEO / Founder]
  HR / Recruiters
    [🔍 Tech Recruiter] [🔍 HR Manager]

LinkedIn DM (copy-paste this):
┌──────────────────────────────────────────────┐
│ Hi there, I noticed Razorpay is hiring for   │
│ Senior Backend Engineer. I have 3+ years...  │
└──────────────────────────────────────────────┘

▸ Show long version (for direct message)

[Apply to Job] [Copy Short DM] [Copy Long DM] [Mark Messaged]
```

**Button colors:**
- 🔵 Blue = Engineering roles (best response rate)
- 🟣 Purple = C-Level (good for small companies)
- 🟢 Green = HR / Recruiters (gatekeepers but respond)

### Status Workflow
```
pending → messaged → replied
             ↓
       followed_up
```

Click status buttons as you progress. Timestamps auto-recorded.

---

## Daily Email

Sent automatically at **9:00 AM IST** every day.

### Email subject
`Daily Job Digest - 15 opportunities (Apr 15)`

### Email body (HTML)
```
┌─────────────────────────────────────────────┐
│        Your Daily Job Digest                │
│   April 15, 2026 · 15 opportunities         │
│                                             │
│   Hey Parmanand 👋                          │
│   Here are 15 fresh backend roles...        │
├─────────────────────────────────────────────┤
│  #1                          [Score 72][IN]│
│  Senior Backend Engineer                    │
│  Razorpay · Bangalore                       │
│  ₹25-40 LPA · Posted Apr 13                │
│  Tech: python, django, redis, aws          │
├─────────────────────────────────────────────┤
│  Find someone at Razorpay:                  │
│   Engineering                               │
│     [🔍 Eng Manager] [🔍 Tech Lead]         │
│   C-Level                                   │
│     [🔍 CTO] [🔍 CEO/Founder]              │
│   HR/Recruiters                            │
│     [🔍 Tech Recruiter] [🔍 HR Manager]    │
├─────────────────────────────────────────────┤
│  LinkedIn DM:                               │
│  "Hi there, I noticed Razorpay is..."       │
├─────────────────────────────────────────────┤
│          [Apply to Job →]                   │
└─────────────────────────────────────────────┘
```

15 cards like this, one per job. Scrollable.

---

## Google Sheets Export (Optional)

If configured (requires `GOOGLE_SHEETS_CREDS` + `GOOGLE_SHEET_ID` in `.env`):

Click **Export to Sheets** on Jobs page. Modal lets you:
- Set sheet tab name
- Min score filter
- India-friendly filter
- Mode: Replace (clear + rewrite) or Append (add rows)

Pushes all matching jobs to your Google Sheet. Useful for:
- n8n automation pipelines
- Manual tracking across multiple candidates
- Backup / archive

See `core/sheets.py` for implementation.

---

## Auto-Cleanup

Runs automatically on every "Collect Jobs":
- Jobs not seen in **14 days** get deleted
- **Exception**: Jobs marked `applied` or `mark_for_email` are never deleted
- Keeps DB focused on actively-posted jobs

---

## Score-Based Filtering

Jobs scoring below **25** are dropped before storage:
- Saves DB space
- Prevents noise in the UI
- Configurable in `core/collector.py` → `MIN_SCORE_TO_STORE`

---

## Protected Data

- `applied` jobs never deleted (for record-keeping)
- `for_email` jobs never deleted (user marked them)
- `outreach` items tracked independently — survive even if job deleted
