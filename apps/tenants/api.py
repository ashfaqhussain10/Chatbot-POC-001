from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.audit.mixins import AuditLogMixin
from apps.flows.validation import validate_flow

from .models import Tenant
from .serializers import TenantSerializer


class TenantViewSet(AuditLogMixin, viewsets.ModelViewSet):
    """Tenant CRUD + config (FR-15/16). Auth + 401 from the global default (SEC-05).
    All writes are audited (FR-19)."""

    queryset = Tenant.objects.all()  # Tenant.Meta.ordering = ["name"] gives stable paging
    serializer_class = TenantSerializer

    @action(detail=True, methods=["get"])
    def validate(self, request, pk=None):
        """Flow health for the builder banner (AP-03 / V-01..06). Read-only."""
        return Response(validate_flow(self.get_object()))

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        """Activate the flow — refused if invalid (AP-03)."""
        tenant = self.get_object()
        result = validate_flow(tenant)
        if not result["valid"]:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        tenant.is_active = True
        tenant.save(update_fields=["is_active"])
        self._audit("activated", tenant, {"is_active": True})
        return Response({"is_active": True, **result})

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        """Deactivate — always allowed regardless of validation state."""
        tenant = self.get_object()
        tenant.is_active = False
        tenant.save(update_fields=["is_active"])
        self._audit("deactivated", tenant, {"is_active": False})
        return Response({"is_active": False})

    @action(detail=True, methods=["post"], url_path="set-tokens")
    def set_tokens(self, request, pk=None):
        """Securely set Meta tokens (write-only). Values are encrypted at rest (SEC-02)
        and never echoed or stored in the audit diff."""
        tenant = self.get_object()
        updated = []
        for field in ("wa_access_token", "ig_access_token"):
            if field in request.data:
                setattr(tenant, field, request.data[field] or "")
                updated.append(field)
        if updated:
            tenant.save(update_fields=updated)
            self._audit("tokens_updated", tenant, {"fields": updated})  # field names only
        return Response({"updated": updated})
