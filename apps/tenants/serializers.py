from rest_framework import serializers

from .models import Tenant


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        # Tokens are deliberately excluded — never exposed via the API (SEC-02).
        fields = (
            "id",
            "name",
            "wa_phone_number",
            "ig_account_id",
            "greeting_message",
            "closing_message",
            "handoff_enabled",
            "handoff_email",
            "is_active",
            "created_at",
        )
        read_only_fields = ("id", "created_at")
