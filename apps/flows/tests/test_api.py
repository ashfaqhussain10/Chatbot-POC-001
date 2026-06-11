from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from apps.flows.models import FlowStep
from apps.tenants.models import Tenant


class FlowAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("po", "po@example.com", "pw-123456")
        self.client.force_authenticate(self.user)
        self.tenant = Tenant.objects.create(name="Acme")

    def test_create_step_and_option(self):
        step = self.client.post(
            "/api/flow-steps/",
            {"tenant": self.tenant.id, "label": "start", "message_text": "Hi", "is_start": True},
            format="json",
        )
        self.assertEqual(step.status_code, 201)
        opt = self.client.post(
            "/api/flow-options/",
            {"step": step.data["id"], "button_label": "Menu", "next_step": None},
            format="json",
        )
        self.assertEqual(opt.status_code, 201)

    def test_steps_filtered_by_tenant(self):
        FlowStep.objects.create(tenant=self.tenant, label="s1", message_text="x")
        other = Tenant.objects.create(name="Other")
        FlowStep.objects.create(tenant=other, label="s2", message_text="y")
        resp = self.client.get(f"/api/flow-steps/?tenant={self.tenant.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(resp.data["results"][0]["label"], "s1")
