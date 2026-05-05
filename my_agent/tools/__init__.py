"""Tools package for the multi-agent outreach pipeline."""

from .resume_parser import parse_resume
from .email_sender import send_email

__all__ = ["parse_resume", "send_email"]
