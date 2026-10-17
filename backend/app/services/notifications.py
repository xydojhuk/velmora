import smtplib
from email.message import EmailMessage

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Order
from app.services.store import get_or_create_store_settings


def _order_text(order: Order) -> str:
    lines = [
        f"New order {order.order_number}",
        f"Customer: {order.customer_name}",
        f"Phone: {order.customer_phone}",
        f"Total: {order.total_minor / 100:.2f} {order.currency}",
        f"Source: {order.source}",
    ]
    if order.shipping_city:
        lines.append(f"City: {order.shipping_city}")
    if order.shipping_branch:
        lines.append(f"Branch: {order.shipping_branch}")
    lines.append("")
    lines.extend(f"{item.title} × {item.quantity}" for item in order.items)
    return "\n".join(lines)


def _send_email(recipient: str, text: str, order_number: str) -> None:
    if not settings.smtp_host or not settings.smtp_from_email:
        return
    message = EmailMessage()
    message["Subject"] = f"VELMORA: new order {order_number}"
    message["From"] = settings.smtp_from_email
    message["To"] = recipient
    message.set_content(text)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as client:
        if settings.smtp_starttls:
            client.starttls()
        if settings.smtp_username:
            client.login(settings.smtp_username, settings.smtp_password)
        client.send_message(message)


def _send_telegram(chat_id: str, text: str) -> None:
    if not settings.telegram_bot_token:
        return
    response = httpx.post(
        f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=10,
    )
    response.raise_for_status()


def dispatch_order_notifications(db: Session, order: Order) -> None:
    config = get_or_create_store_settings(db)
    text = _order_text(order)
    if config.notification_email_enabled and config.notification_email_to:
        try:
            _send_email(config.notification_email_to, text, order.order_number)
        except Exception:
            pass
    if config.notification_telegram_enabled and config.notification_telegram_chat_id:
        try:
            _send_telegram(config.notification_telegram_chat_id, text)
        except Exception:
            pass
