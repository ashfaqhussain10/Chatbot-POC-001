from unittest.mock import patch

from django.test import TestCase

from apps.channels.tasks import process_inbound
from apps.conversations.models import Message, Session
from apps.flows.models import FlowOption, FlowStep
from apps.tenants.models import Tenant


class PipelineTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Acme", wa_phone_number_id="PN1", greeting_message="Hi!",
        )
        start = FlowStep.objects.create(tenant=self.tenant, label="start", message_text="?", is_start=True)
        FlowOption.objects.create(step=start, button_label="Done", next_step=None)

    def _event(self, mid="wamid.1", text="hi", button=None):
        return {"channel": "whatsapp", "phone_number_id": "PN1", "customer": "15550001",
                "provider_message_id": mid, "text": text, "button_label": button}

    @patch("apps.channels.tasks.send_outbounds")
    def test_inbound_drives_engine_and_sends(self, mock_send):
        process_inbound(self._event())
        # session created, inbound + outbound messages logged
        s = Session.objects.get(tenant=self.tenant, customer_identifier="15550001")
        self.assertEqual(s.current_step.label, "start")
        self.assertTrue(Message.objects.filter(session=s, direction="inbound").exists())
        mock_send.assert_called_once()

    @patch("apps.channels.tasks.send_outbounds")
    def test_duplicate_message_id_is_ignored(self, mock_send):
        process_inbound(self._event(mid="dup.1"))
        process_inbound(self._event(mid="dup.1"))  # retry — should be skipped (D-104)
        self.assertEqual(mock_send.call_count, 1)

    @patch("apps.channels.tasks.send_outbounds")
    def test_unknown_tenant_is_discarded(self, mock_send):
        process_inbound(self._event() | {"phone_number_id": "UNKNOWN"})
        mock_send.assert_not_called()
        self.assertEqual(Session.objects.count(), 0)
