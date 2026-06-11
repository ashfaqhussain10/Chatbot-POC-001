from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from .models import AuditLog


class AuditTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("po", "po@example.com", "pw-123456")
        self.client.force_authenticate(self.user)

    def test_tenant_create_is_audited_with_actor(self):
        resp = self.client.post("/api/tenants/", {"name": "Acme"}, format="json")
        self.assertEqual(resp.status_code, 201)
        log = AuditLog.objects.get(entity_type="Tenant", action="created")
        self.assertEqual(log.admin_user, self.user)
        self.assertEqual(log.entity_id, str(resp.data["id"]))

    def test_audit_log_readable_via_api(self):
        self.client.post("/api/tenants/", {"name": "Acme"}, format="json")
        resp = self.client.get("/api/audit-logs/?entity_type=Tenant")
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(resp.data["count"], 1)

    def test_set_tokens_audit_has_no_token_values(self):
        t = self.client.post("/api/tenants/", {"name": "Acme"}, format="json").data
        self.client.post(f"/api/tenants/{t['id']}/set-tokens/",
                         {"wa_access_token": "SECRET"}, format="json")
        log = AuditLog.objects.get(action="tokens_updated")
        self.assertNotIn("SECRET", str(log.diff))  # SEC-02: never store token values
        self.assertIn("wa_access_token", log.diff["fields"])
