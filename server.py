"""
FastAPI server wrapping the ADK Resume Outreach Pipeline.

Endpoints:
    POST /analyze-resume   — upload PDF + user_id → matching companies
    POST /send-emails      — user_id + session_id + companies → send cold emails
    GET  /my-emails/{uid}  — email history for a user

Run:
    uvicorn server:app --reload
"""

import os
import sys
import contextvars
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# ── Ensure project root is importable ──
sys.path.insert(0, os.path.dirname(__file__))

from my_agent.agent import root_agent
from my_agent.tools.email_sender import register_send_hook
from db import init_db, log_email, get_emails

# ══════════════════════════════════════════════════
#  APP SETUP
# ══════════════════════════════════════════════════

app = FastAPI(
    title="Resume Outreach API",
    description="Wraps the ADK cold-outreach pipeline in a REST API.",
    version="0.1.0",
)

APP_NAME = "outreach_api"

session_service = InMemorySessionService()

runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=session_service,
)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ── Context var to track who is sending ──
_ctx_user_id = contextvars.ContextVar("user_id", default="unknown")
_ctx_session_id = contextvars.ContextVar("session_id", default="unknown")


# ── Register email-send hook for DB logging ──
def _email_hook(to_email: str, subject: str, body: str, result: dict):
    """Called automatically after every send_email invocation."""
    status = "sent" if result.get("status") == "success" else "failed"
    error = result.get("error")
    log_email(
        user_id=_ctx_user_id.get(),
        session_id=_ctx_session_id.get(),
        to_email=to_email,
        subject=subject,
        body=body,
        status=status,
        error_message=error,
    )


register_send_hook(_email_hook)


# ── Init DB on startup ──
@app.on_event("startup")
def on_startup():
    init_db()


# ══════════════════════════════════════════════════
#  REQUEST / RESPONSE MODELS
# ══════════════════════════════════════════════════

class SendEmailsRequest(BaseModel):
    user_id: str
    session_id: str
    selected_companies: list[str]


# ══════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════

async def _run_agent(user_id: str, session_id: str, message_text: str) -> list:
    """Send a user message to the root orchestrator and collect all events."""
    message = types.Content(
        role="user",
        parts=[types.Part(text=message_text)],
    )
    events = []
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=message,
    ):
        events.append(event)
    return events


async def _get_state(user_id: str, session_id: str) -> dict:
    """Read current session state (all output_key values)."""
    session = await session_service.get_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )
    if session and session.state:
        return dict(session.state)
    return {}


# ══════════════════════════════════════════════════
#  ENDPOINTS
# ══════════════════════════════════════════════════

@app.post("/analyze-resume")
async def analyze_resume(
    user_id: str = Form(...),
    resume: UploadFile = File(...),
):
    """
    Upload a resume PDF and get matching companies + draft emails.

    The full pipeline runs: parse resume → find startups → find founder
    emails → write draft cold emails.  Returns everything so far.
    """
    # ── Validate ──
    if not resume.filename or not resume.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    # ── Save uploaded PDF ──
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{user_id}_{ts}.pdf"
    filepath = os.path.join(UPLOAD_DIR, filename)

    try:
        content = await resume.read()
        with open(filepath, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    # ── Point the resume parser at the uploaded file ──
    os.environ["RESUME_PATH"] = filepath

    # ── Create a fresh ADK session ──
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
    )

    # ── Run the outreach pipeline (steps 1-4) ──
    try:
        await _run_agent(
            user_id=user_id,
            session_id=session.id,
            message_text="Analyze my resume and find matching startups for cold outreach.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent pipeline failed: {e}")

    # ── Read results from session state ──
    state = await _get_state(user_id, session.id)

    return {
        "user_id": user_id,
        "session_id": session.id,
        "resume_analysis": state.get("resume_analysis", "No analysis produced."),
        "companies": state.get("startup_list", "No companies found."),
        "founder_contacts": state.get("founder_contacts", "No contacts found."),
        "draft_emails": state.get("draft_emails", "No drafts generated."),
    }


@app.post("/send-emails")
async def send_emails(request: SendEmailsRequest):
    """
    Send cold emails to selected companies.

    Requires a session_id from a prior /analyze-resume call (which
    populated draft_emails in session state).
    """
    # ── Verify session exists and has drafts ──
    state = await _get_state(request.user_id, request.session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found. Call /analyze-resume first.")

    if not state.get("draft_emails"):
        raise HTTPException(status_code=400, detail="No draft emails in this session. Call /analyze-resume first.")

    # ── Set context vars for the DB hook ──
    _ctx_user_id.set(request.user_id)
    _ctx_session_id.set(request.session_id)

    # ── Ask the orchestrator to send the selected emails ──
    companies_str = ", ".join(request.selected_companies)
    try:
        await _run_agent(
            user_id=request.user_id,
            session_id=request.session_id,
            message_text=(
                f"Send the cold emails for these companies only: {companies_str}. "
                f"Use the drafts you already wrote. Send them now."
            ),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email sending failed: {e}")

    # ── Read send results from session state ──
    state = await _get_state(request.user_id, request.session_id)

    return {
        "user_id": request.user_id,
        "session_id": request.session_id,
        "selected_companies": request.selected_companies,
        "results": state.get("send_results", "No results available."),
    }


@app.get("/my-emails/{user_id}")
async def my_emails(user_id: str):
    """Return every email sent by this user, newest first."""
    emails = get_emails(user_id)
    return {
        "user_id": user_id,
        "total": len(emails),
        "emails": emails,
    }
