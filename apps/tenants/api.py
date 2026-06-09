from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.flows.validation import validate_flow

from .models import Tenant
from .serializers import TenantSerializer


class TenantViewSet(viewsets.ModelViewSet):
    """Tenant CRUD + config (FR-15/16). Auth + 401 from the global default (SEC-05)."""

    queryset = Tenant.objects.all()
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
        return Response({"is_active": True, **result})

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        """Deactivate — always allowed regardless of validation state."""
        tenant = self.get_object()
        tenant.is_active = False
        tenant.save(update_fields=["is_active"])
        return Response({"is_active": False})
