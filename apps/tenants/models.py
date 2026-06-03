from django.db import models


class Tenant(models.Model):
    """
    A business client. Parent of all flow / conversation / audit data — every other
    table is FK-scoped to a tenant for isolation (FR-20).

    NOTE: wa_access_token / ig_access_token are intentionally NOT here. They are added
    in D1-06 as ENCRYPTED fields (SEC-02 / decision D-100) so no plaintext token can
    ever be stored.
    """

    name = models.CharField(max_length=255)

    # Routing keys — how inbound webhooks map to a tenant (FR-01 / FR-04).
    wa_phone_number = models.CharField(max_length=32, unique=True, null=True, blank=True)
    ig_account_id = models.CharField(max_length=64, unique=True, null=True, blank=True)

    # Per-client config (FR-16).
    greeting_message = models.TextField(blank=True)
    closing_message = models.TextField(blank=True)
    handoff_enabled = models.BooleanField(default=False)
    handoff_email = models.EmailField(blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
