from django.db import models


class Session(models.Model):
    """
    One conversation with one customer. A new conversation always creates a new
    session — never reused across conversations (FR-09 / D-05).

    Flow execution reads + advances this row inside a transaction using
    select_for_update() so concurrent inbound messages serialize (D-105).
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        HANDED_OFF = "handed_off", "Handed off"

    class Channel(models.TextChoices):
        WHATSAPP = "whatsapp", "WhatsApp"
        INSTAGRAM = "instagram", "Instagram"

    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="sessions"
    )
    channel = models.CharField(max_length=16, choices=Channel.choices)
    customer_identifier = models.CharField(max_length=128)
    current_step = models.ForeignKey(
        "flows.FlowStep",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sessions",
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.ACTIVE
    )
    started_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            # The hot lookup on every inbound message: resolve session by who+where.
            models.Index(fields=["tenant", "channel", "customer_identifier"]),
        ]

    def __str__(self):
        return f"{self.customer_identifier} @ tenant {self.tenant_id} ({self.status})"


class Message(models.Model):
    """An inbound or outbound message, logged for the conversation history (FR-18)."""

    class Direction(models.TextChoices):
        INBOUND = "inbound", "Inbound"
        OUTBOUND = "outbound", "Outbound"

    session = models.ForeignKey(
        Session, on_delete=models.CASCADE, related_name="messages"
    )
    direction = models.CharField(max_length=8, choices=Direction.choices)
    content = models.TextField(blank=True)
    channel = models.CharField(max_length=16)
    # D-104: Meta retries webhooks. Store the provider's message id and make it unique
    # per session so a duplicate delivery is detected and skipped (idempotency).
    provider_message_id = models.CharField(max_length=128, null=True, blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session", "provider_message_id"],
                condition=models.Q(provider_message_id__isnull=False),
                name="unique_provider_message_per_session",
            )
        ]
        indexes = [models.Index(fields=["session", "sent_at"])]

    def __str__(self):
        return f"{self.direction} message {self.id}"
