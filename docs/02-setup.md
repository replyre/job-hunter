# Setup Guide

Complete setup from scratch to a running daily email system.

---

## Prerequisites

- **Python 3.11+** installed
- A **Gmail account** for sending emails (prefer a secondary one, not your main)
- 10 minutes to get API keys

---

## Step 1: Install Python Dependencies

```bash
cd "D:/VSCode/job scraper"
pip install -r requirements.txt
```

Or with explicit Python path (Windows):
```bash
"C:/Users/you/AppData/Local/Programs/Python/Python313/python.exe" -m pip install -r requirements.txt
```

---

## Step 2: Get API Keys

### 2a. RapidAPI Key (for JSearch)

JSearch aggregates LinkedIn + Indeed + Glassdoor. **Free tier: 200 requests/month.**

1. Sign up at **https://rapidapi.com**
2. Subscribe to **JSearch**: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
3. Pick the **Free (Basic)** plan
4. Copy your `X-RapidAPI-Key` from the dashboard

### 2b. Hunter.io (optional — currently not used)

Was used for finding contact emails. Replaced with LinkedIn search URLs.
Key stays in `.env` for future use but can be empty.

### 2c. Gmail App Password

Required for sending the daily digest email.

1. Go to **https://myaccount.google.com/security**
2. Enable **2-Step Verification** (required for app passwords)
3. Go to **https://myaccount.google.com/apppasswords**
4. App name: `Job Scraper`
5. Click **Create** — copy the 16-character password
6. **Don't save the Gmail password — save only the app password**

---

## Step 3: Create `.env` File

```bash
cp .env.example .env
```

Edit `.env`:

```bash
# JSearch (RapidAPI) — required
RAPIDAPI_KEY=your_rapidapi_key_here

# Hunter.io — optional, not currently used
HUNTER_API_KEY=

# Gmail SMTP — required for daily email
SENDER_EMAIL=your-secondary-gmail@gmail.com
SENDER_APP_PASSWORD=abcdefghijklmnop
RECIPIENT_EMAIL=candidate@gmail.com

# Daily digest timing (IST timezone)
DAILY_EMAIL_HOUR=9
DAILY_JOBS_COUNT=15

# Google Sheets export — optional
GOOGLE_SHEETS_CREDS=credentials.json
GOOGLE_SHEET_ID=
```

**Important:**
- `SENDER_APP_PASSWORD` is the 16-character App Password, **not** your Gmail login password
- `SENDER_EMAIL` is the sender. It can be any Gmail you control.
- `RECIPIENT_EMAIL` is where the daily digest gets delivered (the job seeker)

---

## Step 4: Initialize Database (auto on first run)

Not needed manually — the database auto-initializes when you start the server. Tables created:
- `jobs`
- `companies`
- `outreach`
- `search_queries` (seeded with 6 default queries)
- `email_log`
- `api_usage`

---

## Step 5: Start the Server

```bash
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
Scheduled daily digest at 9:00 IST
```

---

## Step 6: Open Dashboard

Open browser: **http://127.0.0.1:8000**

You'll see the Jobs page with 0 jobs.

---

## Step 7: First Run — Collect Jobs

Click **"Collect Jobs"** button (top right).

Wait 1-2 minutes. You should see ~500-1000 new jobs appear.

---

## Step 8: Generate Outreach

Navigate to **http://127.0.0.1:8000/outreach**

Click **"Find Contacts for Top Jobs"**. You'll see 15 outreach cards created.

---

## Step 9: Send Test Email

Click **"Send Email Now"** on the outreach page.

Check `RECIPIENT_EMAIL` inbox. Email should arrive in 10-30 seconds.

---

## Step 10: Let the Daily Schedule Run

From now on, the system auto-runs every day at 9:00 AM IST:
1. Collects fresh jobs
2. Generates outreach for new top-scoring ones
3. Sends email

**Just keep the server running.** For 24/7 uptime, deploy to a small VPS (see below).

---

## Running on a Server (Optional)

To keep the daily schedule active, run on a VPS instead of your laptop.

### Option A: DigitalOcean / Hetzner VPS (~$5/mo)

```bash
# On the VPS
git clone <your-repo> job-scraper
cd job-scraper
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your keys

# Run as a systemd service
sudo cp deploy/job-scraper.service /etc/systemd/system/
sudo systemctl enable --now job-scraper
```

### Option B: Railway / Render (free tier)

Both offer free tier small apps. Create `Procfile`:

```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

Add env vars in their dashboard.

### Option C: Keep your laptop on

If laptop is always on, leave the server running. Add to startup if needed.

---

## Troubleshooting

### "SENDER_EMAIL or SENDER_APP_PASSWORD not configured"

- Check `.env` has both values
- Restart the server after editing `.env`

### "Authentication unsuccessful" when sending email

- You're using your regular Gmail password, not an App Password
- App Password is exactly 16 characters, no spaces
- Delete old App Password and create a new one

### Email lands in Spam folder

- First email from a new sender often does
- Tell recipient to mark as "Not Spam" once
- Future emails go to inbox

### JSearch returns 403 / 429

- Rate limit hit. Free tier = 200/month.
- Check usage: `http://127.0.0.1:8000/api/jsearch/status`
- Wait until next month or upgrade RapidAPI plan ($30/mo = 10,000 requests)

### No jobs appearing after "Collect Jobs"

- Check `.env` has `RAPIDAPI_KEY` (otherwise only free sources run)
- Score threshold is 25 — jobs below are dropped
- Check server logs for error messages
