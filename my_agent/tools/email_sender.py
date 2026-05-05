"""
Email Sender Tool
Sends emails via Gmail SMTP using App Password authentication.
"""

import os
import smtplib
from email.message import EmailMessage


# ── Hook system for tracking sent emails ──
_post_send_hooks: list = []


def register_send_hook(hook):
    """Register a callback that fires after every send_email call.

    Signature: hook(to_email: str, subject: str, body: str, result: dict)
    """
    _post_send_hooks.append(hook)


def send_email(to_email: str, subject: str, body: str) -> dict:
    """
    Send an email via Gmail SMTP.

    Requires GMAIL_ADDRESS and GMAIL_APP_PASSWORD to be set in
    environment variables (loaded from .env).

    Args:
        to_email: Recipient's email address.
        subject:  Email subject line.
        body:     Email body content (plain text).

    Returns:
        A dict with 'status' on success, or 'error' on failure.
    """
    result = _send_email_core(to_email, subject, body)
    # Notify hooks (silently catches hook errors)
    for hook in _post_send_hooks:
        try:
            hook(to_email, subject, body, result)
        except Exception:
            pass
    return result


def _send_email_core(to_email: str, subject: str, body: str) -> dict:
    """Internal implementation — sends the email via SMTP."""
    try:
        sender_email = os.environ.get("GMAIL_ADDRESS", "")
        app_password = os.environ.get("GMAIL_APP_PASSWORD", "")

        if not sender_email or not app_password:
            return {
                "error": "Gmail credentials not configured. "
                "Please set GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env file."
            }

        if not to_email or not subject or not body:
            return {"error": "Missing required fields: to_email, subject, and body are all required."}

        # Build the email message
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = to_email
        msg.set_content(body)

        # Send via Gmail SMTP with SSL
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
            smtp.login(sender_email, app_password)
            smtp.send_message(msg)

        return {
            "status": "success",
            "message": f"Email sent successfully to {to_email}",
            "subject": subject,
            "from": sender_email,
            "to": to_email,
        }

    except smtplib.SMTPAuthenticationError:
        return {
            "error": "Gmail authentication failed. "
            "Make sure you're using a valid App Password (not your regular password). "
            "Generate one at: https://myaccount.google.com/apppasswords"
        }
    except smtplib.SMTPException as e:
        return {"error": f"SMTP error: {str(e)}"}
    except Exception as e:
        return {"error": f"Failed to send email: {str(e)}"}
