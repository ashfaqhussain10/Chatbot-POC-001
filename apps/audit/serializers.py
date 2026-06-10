from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    admin_user = serializers.StringRelatedField()

    class Meta:
        model = AuditLog
        fields = ("id", "admin_user", "action", "entity_type", "entity_id", "diff", "created_at")
