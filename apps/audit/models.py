from django.db import models


class AuditLog(models.Model):
    """
    Append-only record of product-owner actions on config/flows (FR-19 / SEC-05).
    The auto-record wiring (who did what, on save/delete) lands with auth (D1-11),
    which provides the actor; this model is the store it writes to.
    """

    admin_user = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=32)  # e.g. created, updated, deleted
    entity_type = models.CharField(max_length=64)  # e.g. Tenant, FlowStep
    entity_id = models.CharField(max_length=64)
    diff = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["entity_type", "entity_id"])]

    def __str__(self):
        return f"{self.action} {self.entity_type}#{self.entity_id}"
