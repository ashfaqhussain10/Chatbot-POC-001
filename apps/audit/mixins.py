"""
AuditLogMixin — records create/update/delete on a DRF viewset into audit_logs with the
acting user (SEC-05 / FR-19). Apply to writable admin viewsets.
"""
import json

from django.core.serializers.json import DjangoJSONEncoder

from .models import AuditLog


def _json_safe(data):
    return json.loads(json.dumps(data, cls=DjangoJSONEncoder))


class AuditLogMixin:
    def _actor(self):
        user = getattr(self.request, "user", None)
        return user if (user and user.is_authenticated) else None

    def _audit(self, action, instance, diff=None):
        AuditLog.objects.create(
            admin_user=self._actor(),
            action=action,
            entity_type=type(instance).__name__,
            entity_id=str(instance.pk),
            diff=_json_safe(diff or {}),
        )

    def perform_create(self, serializer):
        instance = serializer.save()
        self._audit("created", instance, serializer.data)

    def perform_update(self, serializer):
        instance = serializer.save()
        self._audit("updated", instance, serializer.data)

    def perform_destroy(self, instance):
        entity_type, pk = type(instance).__name__, str(instance.pk)
        instance.delete()
        AuditLog.objects.create(
            admin_user=self._actor(), action="deleted", entity_type=entity_type, entity_id=pk, diff={}
        )
