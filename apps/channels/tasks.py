"""
Async processing (C-02) — runs in the django-q2 worker, off the webhook request path.
Resolves the tenant, dedups, drives the flow engine, and sends the replies.
"""
import logging

from apps.channels.sender import send_outbounds
from apps.conversations.models import Message
from apps.flows.engine import handle_inbound
from apps.tenants.models import Tenant

logger = logging.getLogger(__name__)


def process_inbound(event):
    """Process one normalised inbound event (see parsing.py)."""
    pmid = event.get("provider_message_id")

    # D-104 idempotency: Meta retries webhooks — skip an already-seen message.
    if pmid and Message.objects.filter(provider_message_id=pmid).exists():
        return

    if event["channel"] == "instagram":
        tenant = Tenant.objects.filter(ig_account_id=event.get("ig_account_id")).first()
    else:
        tenant = Tenant.objects.filter(wa_phone_number_id=event.get("phone_number_id")).first()
    if tenant is None:
        logger.info("No tenant for inbound %s event; discarding", event["channel"])
        return

    outbounds = handle_inbound(
        tenant,
        event["channel"],
        event["customer"],
        text=event.get("text"),
        button_label=event.get("button_label"),
        provider_message_id=pmid,
    )
    send_outbounds(
        tenant, event["customer"], event["channel"], outbounds,
        customer_message_ts=event.get("timestamp"),  # WA-03 24h window check
    )
