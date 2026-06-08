from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from apps.tenants.models import Tenant

from .models import Session


class SessionAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("po", "po@example.com", "pw-123456")
        self.tenant = Tenant.objects.create(name="Acme")

    def test_sessions_read_requires_auth(self):
        resp = self.client.get("/api/sessions/")
        self.assertEqual(resp.status_code, 401)

    def test_sessions_filtered_by_tenant(self):
        self.client.force_authenticate(self.user)
        Session.objects.create(tenant=self.tenant, channel="whatsapp", customer_identifier="c1")
        resp = self.client.get(f"/api/sessions/?tenant={self.tenant.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)

    def test_sessions_read_only(self):
        self.client.force_authenticate(self.user)
        resp = self.client.post("/api/sessions/", {"tenant": self.tenant.id}, format="json")
        self.assertEqual(resp.status_code, 405)  # read-only viewset
