"""Email the BRD pack (Word, PDF, Excel) through any SMTP account, for example Gmail with an app password.

backend/.env:
  SMTP_HOST=smtp.gmail.com
  SMTP_PORT=587
  SMTP_USER=you@gmail.com
  SMTP_PASS=<16-character app password>
  SMTP_FROM=VAANI <you@gmail.com>
Without these the route answers 503 and the UI hides the email form.
"""
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from services import config


def enabled() -> bool:
    return bool(config.SMTP_HOST and config.SMTP_USER and config.SMTP_PASS)


def send(to: list[str], subject: str, body: str, attachments: list[tuple[str, bytes, str]]) -> dict:
    """attachments: [(filename, bytes, mime like 'application/pdf')]. Returns {sent_to, attachments}."""
    if not enabled():
        raise RuntimeError("SMTP is not configured")
    msg = EmailMessage()
    msg["Subject"] = subject[:200]
    msg["From"] = config.SMTP_FROM or formataddr(("VAANI", config.SMTP_USER))
    msg["To"] = ", ".join(to)
    msg.set_content(body)
    for name, data, mime in attachments:
        main, _, sub = mime.partition("/")
        msg.add_attachment(data, maintype=main or "application", subtype=sub or "octet-stream", filename=name)
    port = int(config.SMTP_PORT or 587)
    if port == 465:
        with smtplib.SMTP_SSL(config.SMTP_HOST, port, timeout=30) as s:
            s.login(config.SMTP_USER, config.SMTP_PASS)
            s.send_message(msg)
    else:
        with smtplib.SMTP(config.SMTP_HOST, port, timeout=30) as s:
            s.ehlo()
            s.starttls()
            s.login(config.SMTP_USER, config.SMTP_PASS)
            s.send_message(msg)
    return {"sent_to": to, "attachments": [a[0] for a in attachments]}
