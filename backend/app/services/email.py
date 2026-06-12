"""Gmail SMTP email sender for verification and password-reset links.

When Gmail credentials are not configured (dev mode), the raw token is
logged to stdout so flows can be tested locally without SMTP.
"""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_SMTP_HOST = "smtp.gmail.com"
_SMTP_PORT = 465


def _send(*, to: str, subject: str, body_text: str, body_html: str) -> None:
    """Send an email via Gmail SMTP.  No-op when credentials are empty."""
    settings = get_settings()

    if not settings.gmail_address or not settings.gmail_app_password:
        logger.warning(
            "Gmail credentials not configured — email to %s skipped. "
            "Body: %s",
            to,
            body_text,
        )
        return

    msg = MIMEMultipart("alternative")
    msg["From"] = settings.gmail_address
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body_text, "plain"))
    msg.attach(MIMEText(body_html, "html"))

    try:
        with smtplib.SMTP_SSL(_SMTP_HOST, _SMTP_PORT) as server:
            server.login(settings.gmail_address, settings.gmail_app_password)
            server.sendmail(settings.gmail_address, to, msg.as_string())
        logger.info("Email sent to %s: %s", to, subject)
    except Exception:
        logger.exception("Failed to send email to %s", to)
        raise


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------
def send_verification_email(to_email: str, raw_token: str) -> None:
    """Send an email-verification link."""
    settings = get_settings()
    link = f"{settings.frontend_url}/verify-email?token={raw_token}"

    send_kwargs = dict(
        to=to_email,
        subject="Verify your Trading Simulator account",
        body_text=(
            "Welcome to Trading Simulator!\n\n"
            f"Please verify your email by visiting:\n{link}\n\n"
            "This link expires in 48 hours.\n\n"
            "If you did not create an account, ignore this email."
        ),
        body_html=(
            "<h2>Welcome to Trading Simulator!</h2>"
            "<p>Please verify your email by clicking the link below:</p>"
            f'<p><a href="{link}">Verify Email</a></p>'
            "<p>This link expires in 48 hours.</p>"
            "<p><small>If you did not create an account, ignore this email.</small></p>"
        ),
    )

    # In dev mode without SMTP, also log the raw token for convenience
    if not settings.gmail_address or not settings.gmail_app_password:
        logger.info("DEV verification token for %s: %s", to_email, raw_token)

    _send(**send_kwargs)


def send_password_reset_email(to_email: str, raw_token: str) -> None:
    """Send a password-reset link."""
    settings = get_settings()
    link = f"{settings.frontend_url}/reset-password?token={raw_token}"

    send_kwargs = dict(
        to=to_email,
        subject="Reset your Trading Simulator password",
        body_text=(
            "You requested a password reset for your Trading Simulator account.\n\n"
            f"Reset your password by visiting:\n{link}\n\n"
            "This link expires in 1 hour.\n\n"
            "If you did not request this, ignore this email."
        ),
        body_html=(
            "<h2>Password Reset</h2>"
            "<p>You requested a password reset for your Trading Simulator account.</p>"
            f'<p><a href="{link}">Reset Password</a></p>'
            "<p>This link expires in 1 hour.</p>"
            "<p><small>If you did not request this, ignore this email.</small></p>"
        ),
    )

    if not settings.gmail_address or not settings.gmail_app_password:
        logger.info("DEV password-reset token for %s: %s", to_email, raw_token)

    _send(**send_kwargs)
