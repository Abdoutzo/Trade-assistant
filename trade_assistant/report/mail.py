"""Sends the e-mail through SMTP (Gmail with an app password, or any other server such as Brevo)."""
from __future__ import annotations

import smtplib
from email.message import EmailMessage

from ..config import Settings, get_settings


class NotConfigured(RuntimeError):
    pass


def send(subject: str, text: str, html: str, settings: Settings | None = None) -> str:
    """Returns the recipient. Raises NotConfigured without SMTP_USER / SMTP_PASSWORD."""
    s = settings or get_settings()
    if not s.smtp_user or not s.smtp_password:
        raise NotConfigured("E-mail non configuré : ajoute SMTP_USER et SMTP_PASSWORD (mot de passe "
                            "d'application Gmail) dans les secrets GitHub.")
    recipient = s.mail_to or s.smtp_user
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"Trade Assistant <{s.smtp_user}>"
    message["To"] = recipient
    message.set_content(text)
    message.add_alternative(html, subtype="html")
    with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=30) as server:
        server.starttls()
        server.login(s.smtp_user, s.smtp_password)
        server.send_message(message)
    return recipient
