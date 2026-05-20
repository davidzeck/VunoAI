import structlog
from django.db import transaction

from apps.tasks.models import Task, ExtractedEntity, TaskStep, GeneratedMessage, StatusHistory
from utils.task_codes import generate_task_code
from services.ai.scope_checker import ScopeChecker
from services.ai.intent_extractor import IntentExtractor
from services.ai.workflow_generator import WorkflowGenerator
from services.ai.message_generator import MessageGenerator
from services.risk_engine import calculate_risk
from services.assignment_engine import assign_team

log = structlog.get_logger()


class TaskService:
    def __init__(self):
        self.scope_checker      = ScopeChecker()
        self.intent_extractor   = IntentExtractor()
        self.workflow_generator = WorkflowGenerator()
        self.message_generator  = MessageGenerator()

    def initiate(self, customer_request: str) -> Task:
        task = Task.objects.create(
            task_code=generate_task_code(),
            customer_request=customer_request,
            status=Task.Status.PENDING,
        )
        log.info("task_initiated", task_code=task.task_code)

        from celery_tasks.task_processor import process_task
        process_task.delay(task.id)

        return task

    def run_pipeline(self, task: Task) -> None:
        log.info("pipeline_started", task_code=task.task_code)
        task.status = Task.Status.IN_PROGRESS
        task.save(update_fields=["status", "updated_at"])

        # Stage 0 — scope check
        scope = self.scope_checker.check(task.customer_request)
        if not scope.in_scope:
            task.status = Task.Status.REJECTED
            task.error_detail = scope.reason
            task.save(update_fields=["status", "error_detail", "updated_at"])
            StatusHistory.objects.create(
                task=task,
                from_status=Task.Status.IN_PROGRESS,
                to_status=Task.Status.REJECTED,
                note=scope.reason,
            )
            log.info("task_rejected", task_code=task.task_code, reason=scope.reason)
            return

        if scope.clarification_note:
            task.clarification_note = scope.clarification_note
            task.save(update_fields=["clarification_note"])
            log.info("task_clarified", task_code=task.task_code, note=scope.clarification_note)

        # Stage 1 — intent extraction
        intent_data = self.intent_extractor.extract(task.customer_request)
        log.info("intent_extracted", task_code=task.task_code, intent=intent_data.intent,
                 confidence=intent_data.confidence)

        # Stage 2 — risk scoring (deterministic)
        intent_dict = intent_data.model_dump()
        risk_data   = calculate_risk(intent_dict)
        log.info("risk_calculated", task_code=task.task_code,
                 score=risk_data["risk_score"], level=risk_data["risk_level"])

        # Stage 3 — workflow generation
        workflow = self.workflow_generator.generate(intent_data.intent, intent_data.entities)
        log.info("workflow_generated", task_code=task.task_code, steps=len(workflow.steps))

        # Stage 4 — message generation
        messages = self.message_generator.generate(
            intent_data.intent, intent_data.entities, risk_data["risk_level"]
        )
        log.info("messages_generated", task_code=task.task_code)

        # Stage 5 — team assignment (deterministic)
        team = assign_team(intent_data.intent)

        # Stage 6 — persist everything atomically
        with transaction.atomic():
            task.intent              = intent_data.intent
            task.ai_confidence       = intent_data.confidence
            task.entities            = intent_data.entities
            task.urgency_level       = intent_data.urgency_level
            task.risk_score          = risk_data["risk_score"]
            task.risk_level          = risk_data["risk_level"]
            task.risk_flags          = risk_data["risk_flags"]
            task.risk_explanation    = risk_data["risk_explanation"]
            task.escalation_required = risk_data["escalation_required"]
            task.employee_assignment = team
            task.status              = Task.Status.COMPLETED
            task.save()

            # Extracted entities
            ExtractedEntity.objects.bulk_create([
                ExtractedEntity(task=task, entity_key=k, entity_value=str(v))
                for k, v in intent_data.entities.items()
            ])

            # Workflow steps
            TaskStep.objects.bulk_create([
                TaskStep(task=task, order=i + 1, description=step)
                for i, step in enumerate(workflow.steps)
            ])

            # Generated messages
            GeneratedMessage.objects.bulk_create([
                GeneratedMessage(task=task, channel="whatsapp", content=messages.whatsapp),
                GeneratedMessage(task=task, channel="email",    content=messages.email),
                GeneratedMessage(task=task, channel="sms",      content=messages.sms),
            ])

            # Status history
            StatusHistory.objects.create(
                task=task,
                from_status=Task.Status.IN_PROGRESS,
                to_status=Task.Status.COMPLETED,
            )

        log.info("pipeline_completed", task_code=task.task_code)
