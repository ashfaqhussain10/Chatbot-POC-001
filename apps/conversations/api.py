from rest_framework import viewsets

from .models import Message, Session
from .serializers import MessageSerializer, SessionSerializer


class SessionViewSet(viewsets.ReadOnlyModelViewSet):
    """Conversation sessions, read-only (FR-18). Filter by tenant: ?tenant=<id>."""

    serializer_class = SessionSerializer

    def get_queryset(self):
        qs = Session.objects.all()
        tenant = self.request.query_params.get("tenant")
        if tenant:
            qs = qs.filter(tenant_id=tenant)
        return qs


class MessageViewSet(viewsets.ReadOnlyModelViewSet):
    """Messages, read-only (FR-18). Filter by session: ?session=<id>."""

    serializer_class = MessageSerializer

    def get_queryset(self):
        qs = Message.objects.all()
        session = self.request.query_params.get("session")
        if session:
            qs = qs.filter(session_id=session)
        return qs
