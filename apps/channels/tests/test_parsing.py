from django.test import TestCase

from apps.channels.parsing import parse_whatsapp_events


class ParsingTests(TestCase):
    def test_parses_text_message(self):
        payload = {"entry": [{"changes": [{"value": {
            "metadata": {"phone_number_id": "PNID1"},
            "messages": [{"from": "15550001", "id": "wamid.A", "type": "text", "text": {"body": "hello"}}],
        }}]}]}
        events = parse_whatsapp_events(payload)
        self.assertEqual(len(events), 1)
        e = events[0]
        self.assertEqual(e["phone_number_id"], "PNID1")
        self.assertEqual(e["customer"], "15550001")
        self.assertEqual(e["provider_message_id"], "wamid.A")
        self.assertEqual(e["text"], "hello")
        self.assertIsNone(e["button_label"])

    def test_parses_interactive_button_reply(self):
        payload = {"entry": [{"changes": [{"value": {
            "metadata": {"phone_number_id": "PNID1"},
            "messages": [{"from": "15550001", "id": "wamid.B", "type": "interactive",
                          "interactive": {"type": "button_reply",
                                          "button_reply": {"id": "View menu", "title": "View menu"}}}],
        }}]}]}
        events = parse_whatsapp_events(payload)
        self.assertEqual(events[0]["button_label"], "View menu")
        self.assertIsNone(events[0]["text"])
