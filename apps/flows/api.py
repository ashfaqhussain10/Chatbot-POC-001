from rest_framework import viewsets

from apps.audit.mixins import AuditLogMixin

from .models import FlowOption, FlowStep
from .serializers import FlowOptionSerializer, FlowStepSerializer


class FlowStepViewSet(AuditLogMixin, viewsets.ModelViewSet):
    """Flow step CRUD (FR-17), audited. Filter by tenant: ?tenant=<id>."""

    serializer_class = FlowStepSerializer

    def get_queryset(self):
        qs = FlowStep.objects.all().prefetch_related("options")
        tenant = self.request.query_params.get("tenant")
        if tenant:
            qs = qs.filter(tenant_id=tenant)
        return qs


class FlowOptionViewSet(AuditLogMixin, viewsets.ModelViewSet):
    """Flow option (button) CRUD, audited. Filter by step: ?step=<id>."""

    serializer_class = FlowOptionSerializer

    def get_queryset(self):
        qs = FlowOption.objects.all()
        step = self.request.query_params.get("step")
        if step:
            qs = qs.filter(step_id=step)
        return qs
