import smtplib
from email.message import EmailMessage

from app.config import settings


def try_send_email(*, to_email: str, subject: str, body: str) -> bool:
    """Best-effort email. Returns True if sent, False if skipped/fails."""
    host = (settings.SMTP_HOST or "").strip()
    port = int(settings.SMTP_PORT or 0)
    if not host or not port:
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"clinique@{host}"
    msg["To"] = to_email
    msg.set_content(body)

    try:
        with smtplib.SMTP(host, port, timeout=10) as s:
            s.starttls()
            s.send_message(msg)
        return True
    except Exception:
        return False

