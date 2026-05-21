from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404

from .models import DigestReport, Task, StatusHistory, GeneratedMessage, TaskOutcome
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
            qs = qs.filter(Q(task_code__icontains=search) | Q(customer_request__icontains=search))

        serializer = TaskListSerializer(qs, many=True)
        return Response(serializer.data)

    def create(self, request):
        customer_request = request.data.get("customer_request", "").strip()
        if not customer_request:
            return Response(
                {"error": "customer_request is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(customer_request) > 2000:
            return Response(
                {"error": "customer_request must be 2000 characters or fewer."},
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

        # Record outcome when a human closes the task
        if new_status in [Task.Status.COMPLETED, Task.Status.FAILED]:
            human_assignment = request.data.get("final_assignment", task.employee_assignment)
            TaskOutcome.objects.update_or_create(
                task=task,
                defaults={
                    "final_assignment": human_assignment,
                    "human_overrode_assignment": human_assignment != task.employee_assignment,
                    "ai_was_correct": human_assignment == task.employee_assignment,
                    "override_note": note,
                },
            )

        return Response({"task_code": task.task_code, "status": task.status})

    @action(detail=True, methods=["get"], url_path="messages")
    def messages(self, request, task_code=None):
        task = get_object_or_404(Task, task_code=task_code)
        msgs = GeneratedMessage.objects.filter(task=task)
        return Response(GeneratedMessageSerializer(msgs, many=True).data)

    @action(detail=True, methods=["post"], url_path="messages/send")
    def send_message(self, request, task_code=None):
        task      = get_object_or_404(Task, task_code=task_code)
        channel   = request.data.get("channel")
        recipient = request.data.get("recipient", "").strip()

        if channel not in ["whatsapp", "email"]:
            return Response({"error": "channel must be whatsapp or email"}, status=status.HTTP_400_BAD_REQUEST)
        if not recipient:
            return Response({"error": "recipient is required"}, status=status.HTTP_400_BAD_REQUEST)

        msg = GeneratedMessage.objects.filter(task=task, channel=channel).first()
        if not msg:
            return Response({"error": "No message found for this channel."}, status=status.HTTP_404_NOT_FOUND)

        msg.recipient = recipient
        msg.save(update_fields=["recipient"])

        from celery_tasks.send_message import send_channel_message
        send_channel_message.delay(msg.id)

        return Response({"detail": f"Message queued for {channel}.", "channel": channel})

    @action(detail=False, methods=["get"], url_path="reports/calibration")
    def calibration(self, request):
        outcomes   = TaskOutcome.objects.select_related("task").all()
        total      = outcomes.count()
        correct    = outcomes.filter(ai_was_correct=True).count()
        overridden = outcomes.filter(human_overrode_assignment=True).count()
        by_intent  = list(
            outcomes.values("task__intent").annotate(
                count=Count("id"),
                correct=Count("id", filter=Q(ai_was_correct=True)),
            )
        )
        return Response({
            "total_outcomes":    total,
            "ai_accuracy_pct":   round(correct / total * 100, 1) if total else None,
            "override_rate_pct": round(overridden / total * 100, 1) if total else None,
            "by_intent":         by_intent,
        })

    @action(detail=False, methods=["get"], url_path="reports/digest")
    def digest(self, request):
        latest = DigestReport.objects.order_by("-generated_at").first()
        if not latest:
            return Response({"detail": "No digest generated yet."}, status=status.HTTP_404_NOT_FOUND)
        return Response({
            "generated_at":   latest.generated_at,
            "high_risk_count": latest.high_risk_count,
            "failed_count":    latest.failed_count,
            "task_codes":      latest.task_codes,
        })

    @action(detail=False, methods=["post"], url_path="reports/digest/generate")
    def generate_digest(self, request):
        from celery_tasks.scheduled import daily_digest
        result = daily_digest.delay()
        return Response({"detail": "Digest generation queued.", "task_id": result.id})
