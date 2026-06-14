import time
from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.channels.sender import build_whatsapp_payload, send_outbounds, send_whatsapp
from apps.tenants.models import Tenant


class PayloadBuildTests(TestCase):
    def test_text_payload(self):
        p = build_whatsapp_payload("1555", {"text": "hi", "buttons": []})
        self.assertEqual(p["type"], "text")
        self.assertEqual(p["text"]["body"], "hi")

    def test_reply_buttons_for_3_or_fewer(self):
        p = build_whatsapp_payload("1555", {"text": "pick", "buttons": ["A", "B", "C"]})
        self.assertEqual(p["interactive"]["type"], "button")
        self.assertEqual(len(p["interactive"]["action"]["buttons"]), 3)

    def test_list_for_more_than_3(self):
        p = build_whatsapp_payload("1555", {"text": "pick", "buttons": ["A", "B", "C", "D"]})
        self.assertEqual(p["interactive"]["type"], "list")


class SendTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Acme", wa_phone_number_id="PN1", wa_access_token="tok")

    @patch("apps.channels.sender.requests.post")
    def test_send_success_posts_once(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        send_whatsapp(self.tenant, "1555", {"text": "hi", "buttons": []})
        self.assertEqual(mock_post.call_count, 1)

    @patch("apps.channels.sender.requests.post")
    def test_5xx_retries_once(self, mock_post):
        mock_post.return_value = MagicMock(status_code=503)
        send_whatsapp(self.tenant, "1555", {"text": "hi", "buttons": []})
        self.assertEqual(mock_post.call_count, 2)  # ERR-03: retry once on 5xx


class WhatsAppWindowTests(TestCase):
    """WA-03: refuse the WhatsApp send batch once 24h since the customer's message has passed."""

    def setUp(self):
        self.tenant = Tenant.objects.create(name="Acme", wa_phone_number_id="PN1", wa_access_token="tok")
        self.out = [{"text": "hi", "buttons": []}]

    @patch("apps.channels.sender.requests.post")
    def test_closed_window_skips_send(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        old_ts = int(time.time()) - 25 * 3600  # 25h ago → window closed
        send_outbounds(self.tenant, "1555", "whatsapp", self.out, customer_message_ts=old_ts)
        self.assertEqual(mock_post.call_count, 0)  # nothing sent

    @patch("apps.channels.sender.requests.post")
    def test_open_window_sends(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        recent_ts = int(time.time()) - 60  # 1 min ago → within window
        send_outbounds(self.tenant, "1555", "whatsapp", self.out, customer_message_ts=recent_ts)
        self.assertEqual(mock_post.call_count, 1)

    @patch("apps.channels.sender.requests.post")
    def test_missing_timestamp_sends(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        send_outbounds(self.tenant, "1555", "whatsapp", self.out)  # no ts → reactive default
        self.assertEqual(mock_post.call_count, 1)

    @patch("apps.channels.sender.requests.post")
    def test_window_does_not_apply_to_instagram(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        ig = Tenant.objects.create(name="IG", ig_account_id="IG1", ig_access_token="tok")
        old_ts = int(time.time()) - 25 * 3600
        send_outbounds(ig, "1555", "instagram", self.out, customer_message_ts=old_ts)
        self.assertEqual(mock_post.call_count, 1)  # IG unaffected by WA window
