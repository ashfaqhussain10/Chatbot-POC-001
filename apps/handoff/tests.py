from django.core import mail
from django.test import TestCase

from apps.conversations.models import Session
from apps.flows.engine import handle_inbound
from apps.flows.models import FlowOption, FlowStep
from apps.handoff.services import trigger_handoff
from apps.tenants.models import Tenant

CH = "whatsapp"
CUST = "+1555000999"


class HandoffServiceTests(TestCase):
    def test_no_email_when_address_blank(self):
        t = Tenant.objects.create(name="NoEmail", handoff_enabled=True, handoff_email="")
        s = Session.objects.create(tenant=t, channel=CH, customer_identifier=CUST)
        self.assertFalse(trigger_handoff(s))
        self.assertEqual(len(mail.outbox), 0)

    def test_email_sent_with_context(self):
        t = Tenant.objects.create(name="Acme", handoff_enabled=True, handoff_email="agent@acme.com")
        s = Session.objects.create(tenant=t, channel=CH, customer_identifier=CUST)
        self.assertTrue(trigger_handoff(s))
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ["agent@acme.com"])
        self.assertIn(CUST, email.body)
        self.assertIn(CH, email.body)


class HandoffEngineIntegrationTests(TestCase):
    def setUp(self):
        self.t = Tenant.objects.create(
            name="Verde", greeting_message="Hi!", handoff_enabled=True,
            handoff_email="frontdesk@verde.com",
        )
        start = FlowStep.objects.create(tenant=self.t, label="start", message_text="?", is_start=True)
        FlowOption.objects.create(step=start, button_label="Done", next_step=None)

    def test_handoff_tap_sends_email_and_marks_handed_off(self):
        handle_inbound(self.t, CH, CUST, text="hi")              # greeting + start
        handle_inbound(self.t, CH, CUST, button_label="Done")    # terminal → offer
        handle_inbound(self.t, CH, CUST, button_label="Talk to a human")  # accept → handoff
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["frontdesk@verde.com"])
        s = Session.objects.get(tenant=self.t, customer_identifier=CUST)
        self.assertEqual(s.status, Session.Status.HANDED_OFF)
