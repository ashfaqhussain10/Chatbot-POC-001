from rest_framework import serializers

from .models import Message, Session


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = (
            "id",
            "session",
            "direction",
            "content",
            "channel",
            "provider_message_id",
            "sent_at",
        )


class SessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = (
            "id",
            "tenant",
            "channel",
            "customer_identifier",
            "current_step",
            "status",
            "started_at",
            "updated_at",
        )
