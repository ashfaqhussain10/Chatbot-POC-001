"""
Handoff service (C-05 / D1-24). When a customer asks for a human, email the business's
configured address with the conversation context. The session is marked handed_off by the
flow engine; this module owns the email. (Email *content/template* polish is Dev 3's.)
"""
from django.conf import settings
from django.core.mail import send_mail

from apps.conversations.models import Message


def _conversation_path(session):
    """The trail of what the customer sent, oldest first (button labels / text)."""
    taps = (
        Message.objects.filter(session=session, direction=Message.Direction.INBOUND)
        .order_by("sent_at")
        .values_list("content", flat=True)
    )
    return " > ".join(t for t in taps if t)


def trigger_handoff(session):
    """Email the business that a customer requested a human (FR-11). Returns True if sent."""
    tenant = session.tenant
    if not tenant.handoff_email:
        return False  # nothing configured to send to

    subject = f"[{tenant.name}] A customer asked to talk to a human"
    body = (
        "A customer requested a human handoff.\n\n"
        f"Channel:  {session.channel}\n"
        f"Customer: {session.customer_identifier}\n"
        f"Time:     {session.updated_at:%Y-%m-%d %H:%M UTC}\n"
        f"Path:     {_conversation_path(session) or '(none)'}\n\n"
        f"Please follow up with the customer directly on {session.channel}."
    )
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [tenant.handoff_email])
    return True
