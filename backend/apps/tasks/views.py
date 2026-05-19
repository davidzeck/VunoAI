from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import Task, StatusHistory, GeneratedMessage
from .serializers import (
    TaskListSerializer, TaskDetailSerializer,
    StatusUpdateSerializer, GeneratedMessageSerializer,
)
from services.task_service import TaskService

_task_service = None


def _get_task_service():
    global _task_service
    if _task_service is None:
        _task_service = TaskService()
    return _task_service


class TaskViewSet(viewsets.GenericViewSet):
    queryset     = Task.objects.all().order_by("-created_at")
    lookup_field = "task_code"

    def get_serializer_class(self):
        if self.action == "list":
            return TaskListSerializer
        return TaskDetailSerializer

    def list(self, request):
        qs = self.get_queryset()
        status_filter     = request.query_params.get("status")
        risk_level_filter = request.query_params.get("risk_level")
        intent_filter     = request.query_params.get("intent")
        search            = request.query_params.get("search")

        if status_filter:
            qs = qs.filter(status=status_filter)
        if risk_level_filter:
            qs = qs.filter(risk_level=risk_level_filter)
        if intent_filter:
            qs = qs.filter(intent=intent_filter)
        if search:
            qs = qs.filter(task_code__icontains=search) | qs.filter(customer_request__icontains=search)

        serializer = TaskListSerializer(qs, many=True)
        return Response(serializer.data)

    def create(self, request):
        customer_request = request.data.get("customer_request", "").strip()
        if not customer_request:
            return Response(
                {"error": "customer_request is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        task = _get_task_service().initiate(customer_request)
        return Response(
            {
                "task_code": task.task_code,
                "status":    task.status,
                "message":   "Request received. Processing in background.",
            },
            status=status.HTTP_202_ACCEPTED,
        )

    def retrieve(self, request, task_code=None):
        task = get_object_or_404(Task, task_code=task_code)
        return Response(TaskDetailSerializer(task).data)

    @action(detail=True, methods=["patch"], url_path="status")
    def update_status(self, request, task_code=None):
        task = get_object_or_404(Task, task_code=task_code)
        serializer = StatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        old_status = task.status
        new_status = serializer.validated_data["status"]
        note       = serializer.validated_data.get("note", "")

        if old_status == new_status:
            return Response({"detail": "Status unchanged."})

        StatusHistory.objects.create(
            task=task,
            from_status=old_status,
            to_status=new_status,
            note=note,
        )
        task.status = new_status
        task.save(update_fields=["status", "updated_at"])

        return Response({"task_code": task.task_code, "status": task.status})

    @action(detail=True, methods=["get"], url_path="messages")
    def messages(self, request, task_code=None):
        task = get_object_or_404(Task, task_code=task_code)
        msgs = GeneratedMessage.objects.filter(task=task)
        return Response(GeneratedMessageSerializer(msgs, many=True).data)
