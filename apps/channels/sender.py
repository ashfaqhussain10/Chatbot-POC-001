"""
Message sender (C-04) — transmits the flow engine's outbound messages via the Meta
WhatsApp Cloud API, per tenant. Provider-agnostic interface so a BSP could be swapped in.
"""
import logging
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)
TIMEOUT = 10
# WhatsApp interactive/free-form messages are only allowed within 24h of the
# customer's last message (WA-03). 23h gives a safety margin under Meta's 24h.
WA_WINDOW = timedelta(hours=23)


def _endpoint(phone_number_id):
    return f"https://graph.facebook.com/{settings.META_GRAPH_VERSION}/{phone_number_id}/messages"


def build_whatsapp_payload(to, outbound):
    """Render an engine outbound dict into a Cloud API message body (WA-02 limits)."""
    text = outbound.get("text", "")
    buttons = outbound.get("buttons") or []
    if not buttons:
        return {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text}}
    if len(buttons) <= 3:  # reply buttons
        return {
            "messaging_product": "whatsapp", "to": to, "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": text},
                "action": {"buttons": [
                    {"type": "reply", "reply": {"id": b[:256], "title": b[:20]}} for b in buttons
                ]},
            },
        }
    # >3 → list message (≤10 rows)
    rows = [{"id": b[:200], "title": b[:24]} for b in buttons[:10]]
    return {
        "messaging_product": "whatsapp", "to": to, "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": text},
            "action": {"button": "Choose", "sections": [{"title": "Options", "rows": rows}]},
        },
    }


def _post(phone_number_id, token, payload):
    return requests.post(
        _endpoint(phone_number_id),
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=TIMEOUT,
    )


def send_whatsapp(tenant, to, outbound):
    payload = build_whatsapp_payload(to, outbound)
    resp = _post(tenant.wa_phone_number_id, tenant.wa_access_token, payload)
    if resp.status_code >= 500:          # ERR-03: retry once on 5xx
        resp = _post(tenant.wa_phone_number_id, tenant.wa_access_token, payload)
    if resp.status_code >= 400:          # ERR-03: log, do not retry 4xx. No PII in logs (SEC-04).
        logger.warning("WhatsApp send failed for tenant %s: HTTP %s", tenant.id, resp.status_code)
    return resp


# --- Instagram (Messenger Platform format; buttons → quick replies, IG-02) ---

def build_instagram_payload(to, outbound):
    text = outbound.get("text", "")
    buttons = outbound.get("buttons") or []
    message = {"text": text}
    if buttons:  # IG quick replies: up to 13, title ≤ 20 chars
        message["quick_replies"] = [
            {"content_type": "text", "title": b[:20], "payload": b[:1000]} for b in buttons[:13]
        ]
    return {"recipient": {"id": to}, "message": message}


def _post_ig(ig_account_id, token, payload):
    return requests.post(
        _endpoint(ig_account_id),  # graph.facebook.com/<ver>/<ig_id>/messages
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=TIMEOUT,
    )


def send_instagram(tenant, to, outbound):
    payload = build_instagram_payload(to, outbound)
    resp = _post_ig(tenant.ig_account_id, tenant.ig_access_token, payload)
    if resp.status_code >= 500:          # ERR-03: retry once on 5xx
        resp = _post_ig(tenant.ig_account_id, tenant.ig_access_token, payload)
    if resp.status_code >= 400:          # ERR-03: log, no 4xx retry. No PII (SEC-04).
        logger.warning("Instagram send failed for tenant %s: HTTP %s", tenant.id, resp.status_code)
    return resp


def within_wa_window(customer_message_ts):
    """True if we may still send a WhatsApp free-form/interactive message (WA-03).

    `customer_message_ts` is the customer's message time from Meta's webhook (epoch
    seconds). None (e.g. no timestamp supplied) is treated as in-window — the normal
    reactive path is always within seconds of the inbound. Measuring from Meta's
    timestamp (not our DB insert time) keeps this correct if a message is processed
    late after a queue/DLQ delay."""
    if not customer_message_ts:
        return True
    try:
        sent = datetime.fromtimestamp(int(customer_message_ts), tz=dt_timezone.utc)
    except (TypeError, ValueError):
        return True
    return timezone.now() - sent < WA_WINDOW


def send_outbounds(tenant, to, channel, outbounds, customer_message_ts=None):
    """Transmit each engine outbound. For WhatsApp, refuse the whole batch if the 24h
    window has closed (WA-03): v1 flags + logs and does not attempt templates."""
    if channel == "whatsapp" and not within_wa_window(customer_message_ts):
        # SEC-04: log tenant id only, never the customer identifier.
        logger.warning(
            "WA-03: 24h window closed for tenant %s; skipping %d outbound message(s).",
            tenant.id, len(outbounds),
        )
        return
    for ob in outbounds:
        if channel == "instagram":
            send_instagram(tenant, to, ob)
        else:
            send_whatsapp(tenant, to, ob)
