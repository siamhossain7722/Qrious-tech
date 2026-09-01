# 🤖 LinkedIn Job Application Agent

An AI-powered agent that automatically searches and applies to jobs on LinkedIn using browser automation (Playwright) and Google Gemini AI for cover letter generation. Features a beautiful dark-mode Django web dashboard.

---

## ✨ Features

- 🔍 **Smart Job Search** — Filters by title, location, experience level, date posted
- ⚡ **Easy Apply Automation** — Fills multi-step application forms automatically
- 🤖 **AI Cover Letters** — Google Gemini generates personalized cover letters
- 💡 **Smart Q&A** — AI answers screening questions automatically
- 🛡️ **Anti-Detection** — Random delays, human-like typing, session persistence
- 🔵 **Dry Run Mode** — Test safely without submitting real applications
- 📊 **Web Dashboard** — Beautiful dark-mode UI to track all applications
- 💾 **Session Persistence** — Stays logged in across runs

---

## 🚀 Quick Start

### 1. Clone & Setup

```bash
cd d:\phitron\Django\agent
pip install -r requirements.txt
python -m playwright install chromium
```

### 2. Configure Credentials

```bash
# Copy the template and fill in your details
copy .env.example .env
```

Edit `.env`:
```env
LINKEDIN_EMAIL=your@email.com
LINKEDIN_PASSWORD=yourpassword
GEMINI_API_KEY=your_gemini_key   # Optional, get free at aistudio.google.com
```

### 3. Configure Job Preferences

Edit `config/settings.yaml`:
```yaml
job_search:
  keywords: ["Python Developer", "Django Developer"]
  location: "Bangladesh"
  remote: true
  max_applications_per_run: 5

agent:
  dry_run: true    # ALWAYS start with true!
```

### 4. Run Migrations

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 5. Start Dashboard

```bash
python manage.py runserver 8001
```

Open: **http://localhost:8001**

---

## 🖥️ Dashboard

The web dashboard lets you:
- **Run the agent** with one click (Dry Run or Live mode)
- **Track all applications** with status badges
- **Update statuses** manually (Pending → Interview → Offer)
- **Filter & search** your job list
- **View statistics** (applied, interviews, offers)

---

## 💻 CLI Usage

```bash
# Dry run (safe - no applications submitted)
python manage.py run_agent

# Live mode (actually applies to jobs)
python manage.py run_agent --live

# Custom config file
python manage.py run_agent --config config/settings.yaml
```

Or run the agent directly:
```bash
python agent/main.py
```

---

## ⚙️ Configuration Guide (`config/settings.yaml`)

| Key | Description | Example |
|-----|-------------|---------|
| `job_search.keywords` | Job titles to search | `["Python Dev", "Backend Dev"]` |
| `job_search.location` | Location filter | `"Bangladesh"` |
| `job_search.remote` | Include remote jobs | `true` |
| `job_search.date_posted` | Age filter | `past_week`, `past_24_hours` |
| `job_search.max_applications_per_run` | Max applies per run | `5` |
| `job_search.blacklisted_companies` | Skip these companies | `["Company A"]` |
| `agent.headless` | Hide browser | `false` (show) / `true` (hide) |
| `agent.dry_run` | Safe mode | `true` = no real applications |
| `agent.slow_mo_ms` | Action delay (ms) | `800` |

---

## 🔒 Safety Tips

1. **Always start with `dry_run: true`** to verify the agent finds the right jobs
2. Set `max_applications_per_run` to a small number (5-10) initially
3. Check your `data/screenshots/` folder if anything goes wrong
4. LinkedIn may ask for verification on first login — complete it manually
5. Keep `headless: false` initially so you can monitor what the agent is doing

---

## 📁 Project Structure

```
linkedin-agent/
├── agent/                  # Core automation engine
│   ├── browser.py          # Playwright browser with anti-detection
│   ├── linkedin_auth.py    # Login & session management
│   ├── job_search.py       # Job search with filters
│   ├── job_apply.py        # Easy Apply automation
│   ├── ai_helper.py        # Gemini AI cover letters
│   └── main.py             # Agent orchestrator
├── dashboard/              # Django web dashboard
│   ├── models.py           # Database models
│   ├── views.py            # API endpoints
│   └── templates/          # Dark-mode UI
├── config/
│   └── settings.yaml       # Job preferences
├── data/                   # Session files, screenshots
├── .env                    # Your credentials (git-ignored)
└── requirements.txt
```

---

## ⚠️ Disclaimer

This tool is for **educational and personal productivity use only**. LinkedIn's Terms of Service prohibit automated access. Use responsibly — excessive automation may result in account restrictions.
