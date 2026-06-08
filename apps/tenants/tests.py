from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from .models import Tenant


class TenantAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("po", "po@example.com", "pw-123456")

    def test_requires_authentication(self):
        # SEC-05: unauthenticated requests are rejected.
        resp = self.client.get("/api/tenants/")
        self.assertEqual(resp.status_code, 401)

    def test_create_does_not_expose_tokens(self):
        self.client.force_authenticate(self.user)
        resp = self.client.post("/api/tenants/", {"name": "Acme"}, format="json")
        self.assertEqual(resp.status_code, 201)
        # SEC-02: tokens must never appear in API output.
        self.assertNotIn("wa_access_token", resp.data)
        self.assertNotIn("ig_access_token", resp.data)

    def test_deactivate_via_patch(self):
        self.client.force_authenticate(self.user)
        t = Tenant.objects.create(name="Acme")
        resp = self.client.patch(f"/api/tenants/{t.id}/", {"is_active": False}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data["is_active"])
