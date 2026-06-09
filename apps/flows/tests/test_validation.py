from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from apps.flows.models import FlowOption, FlowStep
from apps.flows.validation import validate_flow
from apps.tenants.models import Tenant


def codes(result_key):
    return {e["code"] for e in result_key}


class FlowValidationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("po", "po@example.com", "pw-123456")
        self.client.force_authenticate(self.user)
        self.tenant = Tenant.objects.create(name="Acme")

    def _start_with_terminal(self):
        start = FlowStep.objects.create(tenant=self.tenant, label="start", message_text="hi", is_start=True)
        FlowOption.objects.create(step=start, button_label="Done", next_step=None)
        return start

    def test_no_start_step_is_invalid(self):
        FlowStep.objects.create(tenant=self.tenant, label="s", message_text="x")
        result = validate_flow(self.tenant)
        self.assertFalse(result["valid"])
        self.assertIn("V-01", codes(result["errors"]))

    def test_unreachable_step_is_invalid(self):
        self._start_with_terminal()
        FlowStep.objects.create(tenant=self.tenant, label="orphan", message_text="x")  # no inbound link
        result = validate_flow(self.tenant)
        self.assertIn("V-04", codes(result["errors"]))

    def test_valid_flow_activates(self):
        self._start_with_terminal()
        resp = self.client.post(f"/api/tenants/{self.tenant.id}/activate/")
        self.assertEqual(resp.status_code, 200)
        self.tenant.refresh_from_db()
        self.assertTrue(self.tenant.is_active)

    def test_invalid_flow_cannot_activate(self):
        FlowStep.objects.create(tenant=self.tenant, label="s", message_text="x")  # no start
        resp = self.client.post(f"/api/tenants/{self.tenant.id}/activate/")
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.data["valid"])
        self.tenant.refresh_from_db()
        self.assertFalse(self.tenant.is_active)

    def test_deactivate_always_allowed(self):
        self.tenant.is_active = True
        self.tenant.save()
        resp = self.client.post(f"/api/tenants/{self.tenant.id}/deactivate/")
        self.assertEqual(resp.status_code, 200)
        self.tenant.refresh_from_db()
        self.assertFalse(self.tenant.is_active)
