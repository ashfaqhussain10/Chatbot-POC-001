"""
Webhook receiver (C-01) — the single public endpoint for all tenants' inbound Meta events.
Validates the signature (SEC-01), parses, and hands off to the async worker. Always
returns HTTP 200 to Meta (ERR-01); heavy work is async.
"""
import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.http import HttpResponse
from django_q.tasks import async_task
from rest_framework.views import APIView

from .parsing import parse_events

logger = logging.getLogger(__name__)


def valid_signature(raw_body, header):
    """Constant-time HMAC-SHA256 check of the raw body (SEC-01)."""
    secret = settings.META_APP_SECRET
    if not secret or not header or not header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header)


class WebhookView(APIView):
    # Public endpoint — protected by signature, not by auth (SEC-01).
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        # WA-04 verification handshake.
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge", "")
        if mode == "subscribe" and token and token == settings.META_WEBHOOK_VERIFY_TOKEN:
            return HttpResponse(challenge)
        return HttpResponse("forbidden", status=403)

    def post(self, request):
        raw = request.body
        if not valid_signature(raw, request.headers.get("X-Hub-Signature-256", "")):
            logger.warning("Webhook signature invalid; discarding")
            return HttpResponse(status=200)  # ERR-01: always 200, even on rejection

        try:
            payload = json.loads(raw.decode() or "{}")
        except ValueError:
            return HttpResponse(status=200)

        for event in parse_events(payload):
            async_task("apps.channels.tasks.process_inbound", event)
        return HttpResponse(status=200)
