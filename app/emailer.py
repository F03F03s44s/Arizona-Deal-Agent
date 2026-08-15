"""SMTP email delivery for deal alerts."""

from __future__ import annotations

import logging
import os
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path

logger = logging.getLogger(__name__)

ALERT_LOG = Path(__file__).resolve().parent.parent / "data" / "alerts.log"


@dataclass
class SmtpConfig:
    host: str
    port: int
    username: str | None
    password: str | None
    sender: str
    use_tls: bool = True

    @property
    def configured(self) -> bool:
        return bool(self.host and self.sender)


def load_smtp_config() -> SmtpConfig:
    return SmtpConfig(
        host=os.getenv("SMTP_HOST", ""),
        port=int(os.getenv("SMTP_PORT", "587")),
        username=os.getenv("SMTP_USER") or None,
        password=os.getenv("SMTP_PASSWORD") or None,
        sender=os.getenv("SMTP_FROM", os.getenv("SMTP_USER", "")),
        use_tls=os.getenv("SMTP_TLS", "1") not in {"0", "false", "False"},
    )


def _append_alert_log(recipient: str, subject: str, body: str) -> None:
    ALERT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with ALERT_LOG.open("a", encoding="utf-8") as fh:
        fh.write(f"TO: {recipient}\nSUBJECT: {subject}\n{body}\n---\n")


def send_deal_alert(recipient: str, subject: str, body: str) -> str:
    """Send an alert email. Falls back to a local log when SMTP is unset.

    Returns a short status string describing how the alert was delivered.
    """
    config = load_smtp_config()
    _append_alert_log(recipient, subject, body)

    if not config.configured:
        logger.info("SMTP not configured; alert for %s written to %s", recipient, ALERT_LOG)
        return "logged"

    message = EmailMessage()
    message["From"] = config.sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(config.host, config.port, timeout=30) as smtp:
        if config.use_tls:
            smtp.starttls()
        if config.username and config.password:
            smtp.login(config.username, config.password)
        smtp.send_message(message)

    logger.info("Sent deal alert email to %s", recipient)
    return "emailed"
