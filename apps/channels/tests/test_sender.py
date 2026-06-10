from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.channels.sender import build_whatsapp_payload, send_whatsapp
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
