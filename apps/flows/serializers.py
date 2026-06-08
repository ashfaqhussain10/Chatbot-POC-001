from rest_framework import serializers

from .models import FlowOption, FlowStep


class FlowOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlowOption
        fields = ("id", "step", "button_label", "next_step")


class FlowStepSerializer(serializers.ModelSerializer):
    options = FlowOptionSerializer(many=True, read_only=True)

    class Meta:
        model = FlowStep
        fields = (
            "id",
            "tenant",
            "label",
            "message_text",
            "is_start",
            "is_terminal",
            "created_at",
            "options",
        )
        read_only_fields = ("id", "created_at")
