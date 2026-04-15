# Daily Usage Guide

How the candidate uses this system day-to-day.

---

## The 20-Minute Daily Workflow

### Morning (9:00-9:05 AM)

**Check email.** The daily digest has arrived with 15 matching jobs.

Each card in the email has:
- **Job title** + Company + Score + India-friendly status
- **Apply button** — direct link to apply
- **7 LinkedIn search buttons** — grouped into Engineering / C-Level / HR
- **Ready-to-copy DM** — personalized for the role

### For each of the 15 jobs (~1 min each = 15 min total):

1. **Read the job title** — is it actually a fit?
   - If yes → proceed
   - If no → skip, move to next

2. **Click "Apply to Job"** → fill out the application on the company's site

3. **Pick a LinkedIn search button** based on company size:
   - **Small startup (<50 people)** → click "CEO / Founder" or "CTO"
   - **Mid-size (50-500)** → click "Engineering Manager" or "Tech Lead"
   - **Large (500+)** → click "Tech Recruiter" or "HR Manager"

4. **LinkedIn opens** with people matching the search. Pick the best fit:
   - Recent posts
   - Active profile
   - Right role (not too junior, not too senior)

5. **Send a connection request** with the pre-written DM (already in your clipboard — just paste)

6. **Move to next job**

---

## Daily Metrics Target

| Metric | Target |
|---|---|
| Jobs reviewed | 15 |
| Applications submitted | 10-12 (some won't be relevant) |
| LinkedIn DMs sent | 8-10 |
| Time spent | ~20 min |

Expected results:
- **Week 1**: 2-3 LinkedIn responses
- **Week 2**: 5-8 interview calls
- **Week 3-4**: First offers coming in

---

## Weekly Tasks (Sunday, 15 min)

### 1. Review replies
- Open LinkedIn inbox — who replied?
- For positive replies: schedule a call
- For "not the right time": Thank them, stay connected

### 2. Follow up on sent DMs (3+ days ago, no reply)
- Open http://127.0.0.1:8000/outreach
- Filter by status = "messaged"
- For items messaged 3+ days ago, send a short follow-up:
  > "Hi [name], wanted to gently bump this — any interest in chatting?"
- Click "Mark Followed Up"

### 3. Review applications
- Open http://127.0.0.1:8000
- Filter by status = "applied"
- For ones with no response after 10 days: mark as "stale"

### 4. Check JSearch usage
- Top-right of Jobs page shows usage
- If close to 200/month, wait to next billing cycle
- Or upgrade RapidAPI plan

---

## Working Through a Job Card (Example)

Scenario: **Senior Backend Engineer @ Razorpay** (Score: 72, India Friendly)

### Step 1: Read the job description
Click the card → modal opens with full description. Quick scan:
- ✅ Python/Django/FastAPI mentioned
- ✅ 3-5 years experience required
- ✅ Bangalore (hybrid)
- ✅ Good comp

### Step 2: Apply
Click "Apply to Job" → Razorpay careers page opens. Submit resume.

### Step 3: Find a contact
In the email, click "🔍 Engineering Manager" (blue button).

LinkedIn opens with: `keywords=Razorpay Engineering Manager`

Results appear. Pick:
- **Rahul Sharma — Engineering Manager @ Razorpay** (500+ connections, active poster)

### Step 4: Connect with DM
Click "Connect" → "Add a note":

Paste the DM from the email:
> Hi there, I noticed Razorpay is hiring for Senior Backend Engineer. I have 3+ years building Python/Django backends — shipped a healthcare SaaS serving 5,000+ users with sub-200ms APIs. Would love to connect.

**But personalize it first:** Change "Hi there" → "Hi Rahul"

Click Send.

### Step 5: Mark status
Go to outreach page → find the Razorpay card → click "Mark Messaged".

---

## Best Practices

### When to send DMs
- **Weekdays, 10 AM - 6 PM IST** (recipient is in India)
- **Weekdays, 8-10 AM EST** (for US-based companies)
- **Avoid Friday evenings and weekends**

### Message tone
- Be confident, not desperate
- Reference a specific detail (tech stack, company product)
- Ask ONE clear question
- Keep it under 300 characters (LinkedIn connection note limit)

### Which contact to pick
| Company Size | Best Target |
|---|---|
| <50 people | CTO or Founder directly |
| 50-200 people | Engineering Manager or Tech Lead |
| 200-1000 people | Tech Lead or Senior Engineer on the team |
| 1000+ people | Technical Recruiter (they're actively looking) |

### When to follow up
- **3 days** after first DM — gentle bump
- **7 days** after follow-up — mark as stale, move on

---

## Using the Dashboard Directly

Besides the daily email, you can use the web UI anytime:

### Jobs Page (`http://127.0.0.1:8000`)

**Use cases:**
- Browse all jobs (not just today's 15)
- Filter by score, company, tech, India-friendly
- Mark specific jobs for email (checkbox on each card)
- Update application status

**Marking jobs for email:**
- Check the checkbox on any job card
- That job will be prioritized in tomorrow's email
- Useful for jobs you specifically want to pursue

### Outreach Page (`http://127.0.0.1:8000/outreach`)

**Use cases:**
- See all generated outreach items
- Copy DMs on demand
- Track who you messaged and when
- Manually trigger email send

---

## What NOT to Do

❌ **Don't apply to every job blindly** — read the description first
❌ **Don't send the same DM to 15 people on LinkedIn in one hour** — they'll throttle you
❌ **Don't use the regular Gmail password in `.env`** — use App Password
❌ **Don't leave old jobs in "messaged" state** — follow up or mark stale
❌ **Don't spam HR** — engineering managers have way better response rates
