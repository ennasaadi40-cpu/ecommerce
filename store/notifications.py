"""Send an email to the store owner whenever a new order is placed."""
import logging
from django.conf import settings
from django.core.mail import send_mail
from .models import SiteConfig

logger = logging.getLogger(__name__)


def send_order_notification(order):
    """
    Email the order details to the owner. Returns True if an email was sent,
    False if no recipient is configured. Never raises — a mail failure must
    not break the customer's checkout.
    """
    cfg = SiteConfig.get()
    recipient = cfg.notify_email or cfg.email
    if not recipient:
        logger.warning("No notification email set in Site configuration; order #%s not emailed.", order.id)
        return False

    lines = [
        f"New order #{order.id} on {cfg.store_name}",
        "",
        "Customer details",
        f"  Name:    {order.full_name}",
        f"  Email:   {order.email}",
        f"  Phone:   {order.phone}",
        f"  Address: {order.address}, {order.city}",
        f"  Payment: {order.get_payment_method_display()}",
    ]
    if order.note:
        lines.append(f"  Note:    {order.note}")
    lines += ["", "Items"]
    for item in order.items.all():
        lines.append(f"  - {item.quantity} x {item.product.name}  (${item.price} each)  = ${item.subtotal}")
    lines += ["", f"TOTAL: ${order.total}"]
    body = "\n".join(lines)
    subject = f"[{cfg.store_name}] New order #{order.id} — ${order.total}"

    try:
        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [recipient],
            # reply-to the customer so the owner can answer them directly
            fail_silently=False,
        )
        return True
    except Exception:
        logger.exception("Failed to send order notification for order #%s", order.id)
        return False