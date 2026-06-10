import hashlib
import hmac
import json
from unittest.mock import patch

from django.test import TestCase, override_settings

SECRET = "test-app-secret"


@override_settings(META_APP_SECRET=SECRET, META_WEBHOOK_VERIFY_TOKEN="vtoken",
                   ALLOWED_HOSTS=["testserver"])
class WebhookTests(TestCase):
    def _sign(self, raw):
        return "sha256=" + hmac.new(SECRET.encode(), raw, hashlib.sha256).hexdigest()

    def test_get_verify_returns_challenge(self):
        resp = self.client.get(
            "/webhook/",
            {"hub.mode": "subscribe", "hub.verify_token": "vtoken", "hub.challenge": "98765"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content.decode(), "98765")

    def test_get_verify_wrong_token_is_403(self):
        resp = self.client.get(
            "/webhook/",
            {"hub.mode": "subscribe", "hub.verify_token": "nope", "hub.challenge": "x"},
        )
        self.assertEqual(resp.status_code, 403)

    @patch("apps.channels.webhook.async_task")
    def test_valid_signature_enqueues_and_returns_200(self, mock_async):
        body = {"entry": [{"changes": [{"value": {
            "metadata": {"phone_number_id": "p1"},
            "messages": [{"from": "15550001", "id": "wamid.1", "type": "text", "text": {"body": "hi"}}],
        }}]}]}
        raw = json.dumps(body).encode()
        resp = self.client.post(
            "/webhook/", data=raw, content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=self._sign(raw),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(mock_async.call_count, 1)

    @patch("apps.channels.webhook.async_task")
    def test_invalid_signature_discarded_with_200(self, mock_async):
        raw = b'{"entry": []}'
        resp = self.client.post(
            "/webhook/", data=raw, content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256="sha256=deadbeef",
        )
        self.assertEqual(resp.status_code, 200)  # ERR-01
        mock_async.assert_not_called()
