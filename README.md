# 🚀 JobFinder ADK — AI-Powered Cold Outreach Agent

An intelligent multi-agent system built with **Google Agent Development Kit (ADK)** that automates the entire cold outreach pipeline — from resume analysis to personalized email delivery.

> Upload your resume → AI finds matching startups → Discovers founder emails → Drafts personalized cold emails → Sends them with your approval.

---

## ✨ Features

- **📄 Resume Analysis** — Parses your PDF resume and extracts niche, skills, interests, and experience level
- **🔍 Startup Discovery** — Uses Google Search grounding to find real, active startups matching your profile
- **📧 Founder Email Discovery** — Searches for founder/CEO contact emails from public sources
- **✍️ Personalized Email Drafts** — Writes compelling, human-sounding cold emails tailored to each startup
- **📬 Gmail Integration** — Sends emails via Gmail SMTP with App Password authentication
- **🗄️ Email Tracking** — Logs all sent emails in a SQLite database with full history
- **🌐 REST API** — FastAPI server with clean endpoints for integration

---

## 🏗️ Architecture

```
root_agent (Orchestrator)
├── outreach_pipeline (SequentialAgent)
│   ├── resume_analyzer      — Extracts candidate profile from PDF
│   ├── startup_finder       — Finds matching startups via Google Search
│   ├── email_discoverer     — Discovers founder/CEO emails
│   └── email_writer         — Drafts personalized cold emails
└── email_sender_agent       — Sends approved emails via Gmail SMTP
```

The system uses a **SequentialAgent** pipeline for the research phase (steps 1–4), while email sending is handled separately at the root level — ensuring the user always reviews and approves drafts before anything is sent.

---

## 📁 Project Structure

```
jobfinder-adk/
├── my_agent/
│   ├── __init__.py            # Package init
│   ├── agent.py               # Multi-agent definitions & orchestrator
│   ├── .env                   # API keys & credentials (not tracked)
│   └── tools/
│       ├── __init__.py
│       ├── resume_parser.py   # PDF resume text extraction (pypdf)
│       └── email_sender.py    # Gmail SMTP sender with hook system
├── server.py                  # FastAPI REST API server
├── db.py                      # SQLite email tracking database
├── requirement.txt            # Python dependencies
├── .gitignore
└── README.md
```

---

## ⚙️ Setup & Installation

### 1. Clone the Repository

```bash
git clone https://github.com/pranay140612/jobfinder-adk.git
cd jobfinder-adk
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirement.txt
```

### 4. Configure Environment Variables

Create a `.env` file inside the `my_agent/` directory:

```bash
# my_agent/.env

GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY=your_google_api_key_here

GMAIL_ADDRESS=your_email@gmail.com
GMAIL_APP_PASSWORD=your_gmail_app_password
```

> **Note:** For `GMAIL_APP_PASSWORD`, you need to generate a Google App Password.
> Go to [Google App Passwords](https://myaccount.google.com/apppasswords) (requires 2FA enabled on your account).

---

## 🚀 Usage

### Option 1: Run with ADK CLI

```bash
adk run my_agent
```

Then interact with the agent in the terminal:
- *"Analyze my resume and find matching startups"*
- *"Send all emails"* or *"Send email 1 and 3"*

### Option 2: Run with ADK Web UI

```bash
adk web
```

Opens a browser-based chat interface to interact with the agent visually.

### Option 3: Run the FastAPI Server

```bash
uvicorn server:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/analyze-resume` | Upload a PDF resume → get matching startups + draft emails |
| `POST` | `/send-emails` | Send approved cold emails to selected companies |
| `GET` | `/my-emails/{user_id}` | Retrieve email history for a user |

### `POST /analyze-resume`

**Form Data:**
- `user_id` (string) — Unique user identifier
- `resume` (file) — PDF resume file

**Response:**
```json
{
  "user_id": "pranay",
  "session_id": "auto-generated",
  "resume_analysis": "...",
  "companies": "...",
  "founder_contacts": "...",
  "draft_emails": "..."
}
```

### `POST /send-emails`

**JSON Body:**
```json
{
  "user_id": "pranay",
  "session_id": "from-previous-call",
  "selected_companies": ["Company A", "Company B"]
}
```

### `GET /my-emails/{user_id}`

Returns all sent emails for the user with timestamps and delivery status.

---

## 🛠️ Tech Stack

| Technology | Purpose |
|-----------|---------|
| [Google ADK](https://google.github.io/adk-docs/) | Multi-agent orchestration framework |
| [Gemini 2.5 Flash](https://deepmind.google/technologies/gemini/) | LLM powering all agents |
| [FastAPI](https://fastapi.tiangolo.com/) | REST API server |
| [pypdf](https://pypdf.readthedocs.io/) | PDF resume text extraction |
| [SQLite](https://www.sqlite.org/) | Email tracking database |
| Gmail SMTP | Email delivery |

---

## 🔒 Security Notes

- **Never commit your `.env` file** — it contains API keys and email credentials
- The `.gitignore` is configured to exclude `.env`, `.venv/`, `__pycache__/`, and database files
- Use **Gmail App Passwords** instead of your actual Google password
- All email sending requires explicit user confirmation

---

## 📝 License

This project is for educational and personal use.

---

<p align="center">Built with ❤️ using Google ADK</p>