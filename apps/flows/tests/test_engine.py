from django.test import TestCase

from apps.conversations.models import Session
from apps.flows.engine import handle_inbound
from apps.flows.models import FlowOption, FlowStep
from apps.tenants.models import Tenant

CH = "whatsapp"
CUST = "+1555000111"


def kinds(outbounds):
    return [o["kind"] for o in outbounds]


class FlowEngineTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Verde", greeting_message="Hi there!", closing_message="Bye!",
        )
        self.start = FlowStep.objects.create(
            tenant=self.tenant, label="start", message_text="What can I help with?", is_start=True,
        )
        self.menu = FlowStep.objects.create(
            tenant=self.tenant, label="menu", message_text="Here is the menu",
        )
        # start --[Menu]--> menu ;  start --[Done]--> END (terminal)
        FlowOption.objects.create(step=self.start, button_label="Menu", next_step=self.menu)
        FlowOption.objects.create(step=self.start, button_label="Done", next_step=None)

    def _first_contact(self):
        return handle_inbound(self.tenant, CH, CUST, text="hi")

    def test_first_contact_greets_then_start(self):
        out = self._first_contact()
        self.assertEqual(kinds(out), ["greeting", "step"])
        s = Session.objects.get(tenant=self.tenant, customer_identifier=CUST)
        self.assertEqual(s.current_step_id, self.start.id)
        self.assertEqual(s.status, Session.Status.ACTIVE)

    def test_button_advances(self):
        self._first_contact()
        out = handle_inbound(self.tenant, CH, CUST, button_label="Menu")
        self.assertEqual(kinds(out), ["step"])
        self.assertEqual(out[0]["text"], "Here is the menu")
        s = Session.objects.get(customer_identifier=CUST)
        self.assertEqual(s.current_step_id, self.menu.id)

    def test_free_text_reprompts_without_advancing(self):
        self._first_contact()
        out = handle_inbound(self.tenant, CH, CUST, text="random words")
        self.assertEqual(kinds(out), ["step"])
        s = Session.objects.get(customer_identifier=CUST)
        self.assertEqual(s.current_step_id, self.start.id)  # unchanged

    def test_terminal_handoff_disabled_sends_closing_and_completes(self):
        self.tenant.handoff_enabled = False
        self.tenant.save()
        self._first_contact()
        out = handle_inbound(self.tenant, CH, CUST, button_label="Done")
        self.assertEqual(kinds(out), ["closing"])
        self.assertEqual(out[0]["text"], "Bye!")
        s = Session.objects.get(customer_identifier=CUST)
        self.assertEqual(s.status, Session.Status.COMPLETED)

    def test_terminal_handoff_enabled_offers_then_hands_off(self):
        self.tenant.handoff_enabled = True
        self.tenant.save()
        self._first_contact()
        offer = handle_inbound(self.tenant, CH, CUST, button_label="Done")
        self.assertEqual(kinds(offer), ["handoff_offer"])
        s = Session.objects.get(customer_identifier=CUST)
        self.assertTrue(s.awaiting_handoff)
        conf = handle_inbound(self.tenant, CH, CUST, button_label="Talk to a human")
        self.assertEqual(kinds(conf), ["confirmation"])
        s.refresh_from_db()
        self.assertEqual(s.status, Session.Status.HANDED_OFF)

    def test_returning_after_completion_starts_new_session(self):
        self.tenant.handoff_enabled = False
        self.tenant.save()
        self._first_contact()
        handle_inbound(self.tenant, CH, CUST, button_label="Done")  # completes
        out = handle_inbound(self.tenant, CH, CUST, text="hello again")
        self.assertEqual(kinds(out), ["greeting", "step"])  # fresh session, greeted again
        self.assertEqual(
            Session.objects.filter(tenant=self.tenant, customer_identifier=CUST).count(), 2
        )

    def test_deleted_step_recovery_resets_to_start(self):
        self._first_contact()
        handle_inbound(self.tenant, CH, CUST, button_label="Menu")  # now at menu
        self.menu.delete()  # SET_NULL nulls current_step
        out = handle_inbound(self.tenant, CH, CUST, text="hi?")
        self.assertEqual(kinds(out), ["greeting", "step"])
        s = Session.objects.get(customer_identifier=CUST)
        self.assertEqual(s.current_step_id, self.start.id)
