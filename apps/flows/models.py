from django.db import models


class FlowStep(models.Model):
    """One node in a tenant's conversation flow (a message + its buttons)."""

    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="steps"
    )
    label = models.CharField(max_length=255)
    message_text = models.TextField()
    is_start = models.BooleanField(default=False)
    is_terminal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # At most one start step per tenant, enforced at the DB level (partial
            # unique index). "Exactly one" also needs >=1, validated at flow activation
            # time (D1-23) since that half can't be a simple constraint.
            models.UniqueConstraint(
                fields=["tenant"],
                condition=models.Q(is_start=True),
                name="unique_start_step_per_tenant",
            )
        ]
        indexes = [models.Index(fields=["tenant"])]

    def __str__(self):
        return f"{self.label} (tenant {self.tenant_id})"


class FlowOption(models.Model):
    """A button on a step. Null next_step = terminal branch."""

    step = models.ForeignKey(
        FlowStep, on_delete=models.CASCADE, related_name="options"
    )
    button_label = models.CharField(max_length=20)  # WA-02: labels max 20 chars
    next_step = models.ForeignKey(
        FlowStep,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incoming_options",
    )

    def __str__(self):
        return self.button_label
