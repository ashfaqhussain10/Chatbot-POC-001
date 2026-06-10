from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.channels.parsing import parse_events
from apps.channels.sender import build_instagram_payload, send_instagram
from apps.channels.tasks import process_inbound
from apps.conversations.models import Session
from apps.flows.models import FlowOption, FlowStep
from apps.tenants.models import Tenant


class InstagramParsingTests(TestCase):
    def test_parse_text_via_dispatcher(self):
        payload = {"object": "instagram", "entry": [{"id": "IGACC", "messaging": [
            {"sender": {"id": "cust1"}, "recipient": {"id": "IGACC"},
             "message": {"mid": "ig.1", "text": "hello"}}
        ]}]}
        e = parse_events(payload)[0]
        self.assertEqual(e["channel"], "instagram")
        self.assertEqual(e["ig_account_id"], "IGACC")
        self.assertEqual(e["customer"], "cust1")
        self.assertEqual(e["text"], "hello")

    def test_parse_quick_reply(self):
        payload = {"object": "instagram", "entry": [{"id": "IGACC", "messaging": [
            {"sender": {"id": "cust1"}, "recipient": {"id": "IGACC"},
             "message": {"mid": "ig.2", "text": "View menu", "quick_reply": {"payload": "View menu"}}}
        ]}]}
        e = parse_events(payload)[0]
        self.assertEqual(e["button_label"], "View menu")

    def test_echo_is_ignored(self):
        payload = {"object": "instagram", "entry": [{"id": "IGACC", "messaging": [
            {"sender": {"id": "IGACC"}, "recipient": {"id": "cust1"},
             "message": {"mid": "ig.3", "text": "bot echo", "is_echo": True}}
        ]}]}
        self.assertEqual(parse_events(payload), [])


class InstagramSenderTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Acme", ig_account_id="IGACC", ig_access_token="tok")

    def test_buttons_become_quick_replies(self):
        p = build_instagram_payload("cust1", {"text": "pick", "buttons": ["A", "B"]})
        self.assertEqual(p["recipient"]["id"], "cust1")
        self.assertEqual(len(p["message"]["quick_replies"]), 2)
        self.assertEqual(p["message"]["quick_replies"][0]["content_type"], "text")

    @patch("apps.channels.sender.requests.post")
    def test_send_posts_once(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        send_instagram(self.tenant, "cust1", {"text": "hi", "buttons": []})
        self.assertEqual(mock_post.call_count, 1)


class InstagramPipelineTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Acme", ig_account_id="IGACC", greeting_message="Hi!")
        start = FlowStep.objects.create(tenant=self.tenant, label="start", message_text="?", is_start=True)
        self.menu = FlowStep.objects.create(tenant=self.tenant, label="menu", message_text="menu")
        FlowOption.objects.create(step=start, button_label="View menu", next_step=self.menu)

    def _event(self, mid, text=None, button=None):
        return {"channel": "instagram", "ig_account_id": "IGACC", "customer": "cust1",
                "provider_message_id": mid, "text": text, "button_label": button}

    @patch("apps.channels.tasks.send_outbounds")
    def test_numeric_reply_selects_option(self, mock_send):
        process_inbound(self._event("ig.a", text="hi"))      # greeting + start
        process_inbound(self._event("ig.b", text="1"))       # IG-02: "1" → first option
        s = Session.objects.get(tenant=self.tenant, customer_identifier="cust1")
        self.assertEqual(s.current_step_id, self.menu.id)    # advanced to menu
