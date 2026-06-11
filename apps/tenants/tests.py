from django.contrib.auth.models import User
from django.core.cache import cache
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


class LoginThrottleTests(APITestCase):
    """The JWT token endpoint is brute-force throttled (login scope = 5/min)."""

    def setUp(self):
        cache.clear()  # isolate the login throttle bucket from other tests

    def test_login_endpoint_throttles_after_limit(self):
        # Throttle runs before auth, so even wrong-credential attempts count.
        # 5 are allowed within the window; the 6th is rejected with 429.
        for _ in range(5):
            self.client.post("/api/auth/token/", {"username": "x", "password": "y"}, format="json")
        resp = self.client.post("/api/auth/token/", {"username": "x", "password": "y"}, format="json")
        self.assertEqual(resp.status_code, 429)
