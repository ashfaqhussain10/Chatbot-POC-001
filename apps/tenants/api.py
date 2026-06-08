from rest_framework import viewsets

from .models import Tenant
from .serializers import TenantSerializer


class TenantViewSet(viewsets.ModelViewSet):
    """Tenant CRUD + config (FR-15/16). Deactivate via PATCH is_active=false.
    Auth + 401 come from the global IsAuthenticated default (SEC-05)."""

    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer
