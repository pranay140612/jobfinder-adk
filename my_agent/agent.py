"""
Automated Cold Outreach Pipeline
=================================
A Google ADK multi-agent system that runs a cold outreach pipeline:
  Resume → Niche → Startups → Founder Emails → Draft Emails → Send (with confirmation)

Architecture:
  root_agent (orchestrator)
    └── outreach_pipeline      — SequentialAgent for cold outreach
          ├── resume_analyzer
          ├── startup_finder     (uses google_search)
          ├── email_discoverer   (uses google_search)
          ├── email_writer
          └── email_sender_agent
"""

import os
from dotenv import load_dotenv

from google.adk.agents import Agent, SequentialAgent
from google.adk.tools import google_search

from .tools.resume_parser import parse_resume
from .tools.email_sender import send_email

# ── Load environment variables ──
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))



# ══════════════════════════════════════════════════
#  OUTREACH PIPELINE (SequentialAgent)
# ══════════════════════════════════════════════════

# ── Step 1: Resume Analyzer ──
resume_analyzer = Agent(
    model="gemini-2.5-flash",
    name="resume_analyzer",
    description="Analyzes a resume to extract the candidate's niche, skills, and interests.",
    instruction="""
You are a career analyst. Your job is to analyze a resume and extract key information.

Steps:
1. Use the `parse_resume` tool to extract text from the resume PDF.
2. Analyze the extracted text thoroughly.
3. Produce a structured analysis with:

**NICHE:** The candidate's primary professional niche/domain (e.g., "AI/ML Engineering", "Full-Stack Web Development", "Data Science & Analytics")

**KEY SKILLS:** List of top technical and professional skills

**INTERESTS:** Areas of interest mentioned or implied

**EXPERIENCE LEVEL:** Junior / Mid / Senior based on experience

**IDEAL STARTUP FIT:** What types of startups would benefit from this candidate's skills
(e.g., "Early-stage AI startups", "B2B SaaS companies", "HealthTech startups")

**SEARCH QUERIES:** Generate 3 specific Google search queries to find startups that match
this candidate's profile (e.g., "AI startups hiring ML engineers in India 2025")

Be specific and actionable. This analysis will be used by the next agent to find matching startups.
""",
    tools=[parse_resume],
    output_key="resume_analysis",
)

# ── Step 2: Startup Finder ──
startup_finder = Agent(
    model="gemini-2.5-flash",
    name="startup_finder",
    description="Finds startups that match the candidate's niche using Google Search.",
    instruction="""
You are a startup research specialist. Based on the resume analysis provided below,
find real startups that would be a great fit for this candidate.

**Resume Analysis:**
{resume_analysis}

Steps:
1. Use the `google_search` tool with targeted queries to find startups matching the candidate's niche.
2. Search for early-stage and growth-stage startups that are actively hiring or building teams.
3. Focus on startups that align with the candidate's skills and interests.

For each startup found, provide:
- **Company Name**
- **Website/Domain** (exact domain like "example.com")
- **What they do** (1-2 sentences)
- **Why they're a match** (how the candidate's skills align)
- **Stage** (Seed, Series A, etc. if available)

Find at least 5 real, active startups. Make sure they are REAL companies, not made-up ones.
Present them in a numbered list format.
""",
    tools=[google_search],
    output_key="startup_list",
)

# ── Step 3: Email Discoverer ──
email_discoverer = Agent(
    model="gemini-2.5-flash",
    name="email_discoverer",
    description="Finds founder/CEO email addresses for the identified startups using Google Search.",
    instruction="""
You are a contact researcher. Your job is to find the founders' or CEOs' contact emails
for the startups identified in the previous step.

**Startups Found:**
{startup_list}

Steps:
1. For EACH startup in the list, use `google_search` to search for the founder/CEO's email.
   Try queries like:
   - "[Company Name] founder email"
   - "[Company Name] CEO contact"
   - "[Founder Name] email [Company Name]"
   - "site:[company-domain] contact"
2. Look for publicly available emails from LinkedIn, Twitter/X, company websites, press releases, etc.
3. If you cannot find a direct email, try to find:
   - The founder's name + company domain to construct a likely email (e.g., firstname@company.com)
   - A general contact email (hello@, info@, founders@)

Present your findings as a structured list:
For each startup:
- **Company:** [Name]
- **Founder/CEO:** [Name]
- **Email:** [email address] (or "Not found" if unavailable)
- **Source:** Where you found the email
- **Confidence:** High / Medium / Low

Only include startups where you found at least a likely email address.
""",
    tools=[google_search],
    output_key="founder_contacts",
)

# ── Step 4: Email Writer ──
email_writer = Agent(
    model="gemini-2.5-flash",
    name="email_writer",
    description="Writes personalized cold emails based on resume analysis and founder contacts.",
    instruction="""
You are an expert cold email copywriter. Write personalized, compelling cold emails
for the candidate to send to startup founders.

**Candidate's Profile:**
{resume_analysis}

**Founder Contacts:**
{founder_contacts}

For EACH founder contact that has an email address, write a personalized cold email:

Guidelines:
1. **Subject line:** Short, specific, and curiosity-provoking (not generic)
2. **Opening:** Reference something specific about the startup (what they're building, recent news)
3. **Value prop:** Connect the candidate's specific skills to what the startup needs
4. **Social proof:** Mention relevant projects or achievements from the resume
5. **CTA:** A soft ask — suggest a quick call or coffee chat, not "hire me"
6. **Length:** Keep it under 150 words. Founders are busy.
7. **Tone:** Professional but human. No corporate jargon.

Format each email clearly:
---
**TO:** [founder email]
**SUBJECT:** [subject line]

[email body]

---

IMPORTANT: These are DRAFTS for the user to review. Do NOT send them yet.
Present ALL drafts and explicitly ask: "Would you like me to send any of these emails?
Please confirm which ones to send by number, or say 'send all' to send them all."
""",
    output_key="draft_emails",
)

# ══════════════════════════════════════════════════
#  STANDALONE: Email Sender (NOT in pipeline)
#  Lives at the root level so user can confirm first
# ══════════════════════════════════════════════════

email_sender_agent = Agent(
    model="gemini-2.5-flash",
    name="email_sender_agent",
    description="Sends cold emails via Gmail SMTP. Use this when the user confirms they want to send emails.",
    instruction="""
You are an email delivery assistant.

The user has already seen draft emails from the outreach pipeline and is now
telling you which ones to send.

**Previously drafted emails are stored in session state under 'draft_emails':**
{draft_emails}

How to handle user requests:
- "send all" → use `send_email` tool for EACH email in the drafts
- "send 1, 3" → send only the specified email numbers
- "send none" / "don't send" → acknowledge and skip
- "edit 2" → help modify email #2, then confirm before sending

For each email to send, call `send_email` with:
  - to_email: the recipient's email address
  - subject: the email subject line
  - body: the full email body text

After sending, report results (success/failure) for each email.
""",
    tools=[send_email],
    output_key="send_results",
)

# ── Assemble the Sequential Pipeline (Steps 1-4 only) ──
# Email sending is handled separately by email_sender_agent at the root level
outreach_pipeline = SequentialAgent(
    name="outreach_pipeline",
    description=(
        "An automated cold outreach pipeline that analyzes the user's resume, "
        "finds matching startups, discovers founder emails, and writes personalized "
        "cold email drafts for user review."
    ),
    sub_agents=[
        resume_analyzer,
        startup_finder,
        email_discoverer,
        email_writer,
    ],
)


# ══════════════════════════════════════════════════
#  ROOT AGENT  (Orchestrator)
# ══════════════════════════════════════════════════

root_agent = Agent(
    model="gemini-2.5-flash",
    name="orchestrator",
    description="The main agent that routes requests to outreach or email sending.",
    instruction="""
You are a smart personal assistant with two capabilities:

📬 **Cold Outreach Pipeline** — When the user asks about:
   - Finding startups
   - Analyzing their resume
   - Starting cold outreach
   - Job outreach or networking
   - "Start outreach" or "find me startups"
   Delegate to the `outreach_pipeline`. This will analyze the resume, find startups,
   discover founder emails, and write draft cold emails for review.

✉️ **Send Emails** — When the user confirms they want to send emails (after seeing drafts),
   such as:
   - "send all"
   - "send email 1 and 3"
   - "yes, send them"
   - "send the emails"
   Delegate to the `email_sender_agent`.

Routing rules:
- Start outreach / find startups / analyze resume → outreach_pipeline
- Send / confirm / approve emails → email_sender_agent
- If unclear, ask the user what they'd like to do

Be friendly, helpful, and proactive.
""",
    sub_agents=[outreach_pipeline, email_sender_agent],
)
