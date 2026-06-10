"""
Parse Meta webhook payloads into normalised inbound events.

A normalised event:
    {channel, customer, provider_message_id, text, button_label, + a routing key}
WhatsApp routing key = phone_number_id; Instagram routing key = ig_account_id.
text XOR button_label is set. Status/echo callbacks are ignored.
"""


def parse_events(payload):
    """Dispatch on Meta's `object` field to the right channel parser."""
    if payload.get("object") == "instagram":
        return parse_instagram_events(payload)
    return parse_whatsapp_events(payload)  # whatsapp_business_account (or default)


def parse_whatsapp_events(payload):
    events = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            phone_number_id = value.get("metadata", {}).get("phone_number_id")
            for msg in value.get("messages", []):
                event = {
                    "channel": "whatsapp",
                    "phone_number_id": phone_number_id,
                    "customer": msg.get("from"),
                    "provider_message_id": msg.get("id"),
                    "text": None,
                    "button_label": None,
                }
                mtype = msg.get("type")
                if mtype == "text":
                    event["text"] = (msg.get("text") or {}).get("body", "")
                elif mtype == "interactive":
                    interactive = msg.get("interactive") or {}
                    reply = interactive.get("button_reply") or interactive.get("list_reply") or {}
                    event["button_label"] = reply.get("title")
                elif mtype == "button":  # template quick-reply button
                    event["button_label"] = (msg.get("button") or {}).get("text")
                else:
                    event["text"] = ""  # unsupported type → bot re-prompts
                events.append(event)
    return events


def parse_instagram_events(payload):
    events = []
    for entry in payload.get("entry", []):
        entry_id = entry.get("id")
        for m in entry.get("messaging", []):
            message = m.get("message") or {}
            if not message or message.get("is_echo"):
                continue  # ignore our own echoed messages
            event = {
                "channel": "instagram",
                "ig_account_id": (m.get("recipient") or {}).get("id") or entry_id,
                "customer": (m.get("sender") or {}).get("id"),
                "provider_message_id": message.get("mid"),
                "text": None,
                "button_label": None,
            }
            quick_reply = message.get("quick_reply")
            if quick_reply:
                event["button_label"] = quick_reply.get("payload") or message.get("text")
            else:
                event["text"] = message.get("text", "")
            events.append(event)
    return events
