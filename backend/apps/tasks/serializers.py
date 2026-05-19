from rest_framework import serializers
from .models import Task, TaskStep, GeneratedMessage, ExtractedEntity, StatusHistory


class TaskStepSerializer(serializers.ModelSerializer):
    class Meta:
        model  = TaskStep
        fields = ["order", "description", "completed"]


class GeneratedMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model  = GeneratedMessage
        fields = ["id", "channel", "content", "recipient", "sent_at", "send_error"]


class ExtractedEntitySerializer(serializers.ModelSerializer):
    class Meta:
        model  = ExtractedEntity
        fields = ["entity_key", "entity_value"]


class StatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model  = StatusHistory
        fields = ["from_status", "to_status", "changed_at", "note"]


class TaskListSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Task
        fields = [
            "task_code", "intent", "status", "risk_level", "risk_score",
            "employee_assignment", "urgency_level", "ai_confidence",
            "escalation_required", "created_at",
        ]


class TaskDetailSerializer(serializers.ModelSerializer):
    steps             = TaskStepSerializer(many=True, read_only=True)
    messages          = GeneratedMessageSerializer(many=True, read_only=True)
    extracted_entities = ExtractedEntitySerializer(many=True, read_only=True)
    history           = StatusHistorySerializer(many=True, read_only=True)

    class Meta:
        model  = Task
        fields = [
            "task_code", "customer_request", "intent", "status",
            "risk_score", "risk_level", "risk_flags", "risk_explanation",
            "escalation_required", "entities", "urgency_level",
            "ai_confidence", "employee_assignment", "error_detail",
            "created_at", "updated_at",
            "steps", "messages", "extracted_entities", "history",
        ]


class StatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Task.Status.choices)
    note   = serializers.CharField(required=False, allow_blank=True, default="")
