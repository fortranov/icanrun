"""
Email service — async SMTP sending via aiosmtplib.

Provides a single send_confirmation_email() helper and a test_connection()
utility used by the admin "Test Connection" button.

HTML and plain-text templates are defined inline to avoid template-engine
dependencies. They are intentionally minimal and easy to customise.
"""
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import aiosmtplib

from app.core.config import settings as app_settings

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Email templates                                                              #
# --------------------------------------------------------------------------- #

_CONFIRM_SUBJECT = "Подтвердите ваш email — ICanRun"

_CONFIRM_HTML = """\
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <title>Подтверждение email</title>
</head>
<body style="font-family: Arial, sans-serif; background: #f5f5f5; padding: 32px;">
  <div style="max-width: 480px; margin: 0 auto; background: #ffffff;
              border-radius: 8px; padding: 40px; border: 1px solid #e5e7eb;">
    <h1 style="font-size: 22px; color: #1e40af; margin-top: 0;">ICanRun</h1>
    <h2 style="font-size: 18px; color: #111827;">Подтвердите ваш email</h2>
    <p style="color: #374151; line-height: 1.6;">
      Привет, <strong>{name}</strong>!<br>
      Нажмите на кнопку ниже, чтобы активировать аккаунт.
      Ссылка действительна {hours} часов.
    </p>
    <a href="{link}"
       style="display: inline-block; margin: 24px 0; padding: 12px 28px;
              background: #2563eb; color: #ffffff; text-decoration: none;
              border-radius: 6px; font-weight: bold; font-size: 15px;">
      Подтвердить email
    </a>
    <p style="color: #6b7280; font-size: 13px;">
      Если кнопка не работает, скопируйте ссылку в браузер:<br>
      <a href="{link}" style="color: #2563eb;">{link}</a>
    </p>
    <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 24px 0;">
    <p style="color: #9ca3af; font-size: 12px;">
      Если вы не регистрировались на ICanRun — просто проигнорируйте это письмо.
    </p>
  </div>
</body>
</html>
"""

_CONFIRM_TEXT = """\
Привет, {name}!

Подтвердите ваш email, перейдя по ссылке (действует {hours} часов):

{link}

Если вы не регистрировались на ICanRun — просто проигнорируйте это письмо.
"""

_TEST_SUBJECT = "ICanRun — тест SMTP подключения"
_TEST_HTML = """\
<!DOCTYPE html>
<html lang="ru">
<body style="font-family: Arial, sans-serif; padding: 32px;">
  <h2 style="color: #1e40af;">ICanRun — тест SMTP</h2>
  <p>SMTP подключение работает корректно.</p>
</body>
</html>
"""


# --------------------------------------------------------------------------- #
# Core send helper                                                              #
# --------------------------------------------------------------------------- #

async def _send(
    *,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    from_email: str,
    from_name: str,
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str,
) -> None:
    """
    Low-level async SMTP send.

    Uses STARTTLS when port != 465, SSL otherwise.

    Raises:
        aiosmtplib.SMTPException on any SMTP error.
        Exception on connection failure.
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = to_email

    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    use_tls = smtp_port == 465

    await aiosmtplib.send(
        msg,
        hostname=smtp_host,
        port=smtp_port,
        username=smtp_user,
        password=smtp_password,
        use_tls=use_tls,
        start_tls=not use_tls,
    )


# --------------------------------------------------------------------------- #
# Public API                                                                   #
# --------------------------------------------------------------------------- #

async def send_confirmation_email(
    *,
    to_email: str,
    to_name: str,
    confirmation_token: str,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    from_email: str,
    from_name: str,
    token_hours: int,
    frontend_url: Optional[str] = None,
) -> None:
    """
    Send an email confirmation link to a newly registered user.

    Args:
        to_email: Recipient email address.
        to_name: Recipient display name (used in the greeting).
        confirmation_token: Raw JWT token (NOT hashed) — goes into the URL.
        smtp_*: SMTP connection parameters from DB settings.
        from_*: Sender identity.
        token_hours: How many hours the link is valid (shown in email text).
        frontend_url: Override for the base URL (defaults to settings.frontend_url).
    """
    base_url = (frontend_url or app_settings.frontend_url).rstrip("/")
    link = f"{base_url}/confirm-email?token={confirmation_token}"

    html = _CONFIRM_HTML.format(name=to_name, hours=token_hours, link=link)
    text = _CONFIRM_TEXT.format(name=to_name, hours=token_hours, link=link)

    await _send(
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_user=smtp_user,
        smtp_password=smtp_password,
        from_email=from_email,
        from_name=from_name,
        to_email=to_email,
        subject=_CONFIRM_SUBJECT,
        html_body=html,
        text_body=text,
    )
    logger.info(f"Confirmation email sent to {to_email}")


async def send_test_email(
    *,
    to_email: str,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    from_email: str,
    from_name: str,
) -> None:
    """
    Send a test email to verify SMTP settings.
    Used by the admin "Test Connection" button.
    """
    await _send(
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_user=smtp_user,
        smtp_password=smtp_password,
        from_email=from_email,
        from_name=from_name,
        to_email=to_email,
        subject=_TEST_SUBJECT,
        html_body=_TEST_HTML,
        text_body="ICanRun — SMTP подключение работает корректно.",
    )
    logger.info(f"Test email sent to {to_email}")
