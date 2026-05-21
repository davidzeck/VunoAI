from datetime import timedelta

import structlog
from celery import shared_task
from django.utils.timezone import now

from apps.tasks.models import DigestReport, StatusHistory, Task

log = structlog.get_logger()


@shared_task
def auto_escalate_stale():
    """Auto-escalate in_progress tasks with no activity for 30+ minutes."""
    cutoff = now() - timedelta(minutes=30)
    stale = Task.objects.filter(
        status=Task.Status.IN_PROGRESS,
        updated_at__lt=cutoff,
        escalation_required=False,
    )
    count = 0
    for task in stale:
        task.escalation_required = True
        task.save(update_fields=["escalation_required", "updated_at"])
        StatusHistory.objects.create(
            task=task,
            from_status=task.status,
            to_status=task.status,
            note="Auto-escalated: no activity for 30 minutes.",
        )
        count += 1
    log.info("auto_escalate_complete", escalated=count)
    return {"escalated": count}


@shared_task
def rescore_pending():
    """
    Re-run risk engine on pending/in_progress tasks that warrant re-evaluation:
    - send_money tasks with amount > 100k (amount-driven risk may have changed)
    - verify_document tasks (document_subtype now extracted — rules are richer)
    confidence is intentionally omitted → calculate_risk defaults it to 1.0.
    """
    from services.risk_engine import calculate_risk

    tasks = Task.objects.filter(
        intent__in=["send_money", "verify_document"],
        status__in=[Task.Status.PENDING, Task.Status.IN_PROGRESS],
    )
    rescored = 0
    for task in tasks:
        # For send_money: skip low-amount tasks that can't trigger elevated rules
        if task.intent == "send_money":
            try:
                amount = float(task.entities.get("amount", 0) or 0)
            except (TypeError, ValueError):
                continue
            if amount <= 100_000:
                continue

        # confidence omitted — calculate_risk defaults to 1.0 for rescore path
        result = calculate_risk({
            **task.entities,
            "intent":        task.intent,
            "urgency_level": task.urgency_level,
        })
        task.risk_score          = result["risk_score"]
        task.risk_level          = result["risk_level"]
        task.risk_flags          = result["risk_flags"]
        task.risk_explanation    = result["risk_explanation"]
        task.escalation_required = result["escalation_required"]
        task.save(update_fields=[
            "risk_score", "risk_level", "risk_flags",
            "risk_explanation", "escalation_required", "updated_at",
        ])
        log.info("task_rescored", task_code=task.task_code,
                 score=result["risk_score"], level=result["risk_level"])
        rescored += 1

    log.info("rescore_complete", rescored=rescored)
    return {"rescored": rescored}


@shared_task
def daily_digest():
    """Generate a daily digest of high-risk and failed tasks from the past 24h."""
    yesterday = now() - timedelta(hours=24)
    high_risk = Task.objects.filter(risk_level="high", created_at__gte=yesterday)
    failed    = Task.objects.filter(status=Task.Status.FAILED, created_at__gte=yesterday)

    report = DigestReport.objects.create(
        high_risk_count=high_risk.count(),
        failed_count=failed.count(),
        task_codes=list(high_risk.values_list("task_code", flat=True)),
    )
    log.info(
        "daily_digest_generated",
        high_risk=report.high_risk_count,
        failed=report.failed_count,
    )
    return {
        "high_risk_count": report.high_risk_count,
        "failed_count": report.failed_count,
    }


@shared_task
def retry_api_failures():
    """Re-queue failed tasks whose error was an API timeout or rate limit."""
    from celery_tasks.task_processor import process_task

    api_error_markers = ["timeout", "rate limit", "ratelimit", "connection", "503", "429"]
    failed = Task.objects.filter(status=Task.Status.FAILED)
    requeued = 0
    for task in failed:
        if any(marker in task.error_detail.lower() for marker in api_error_markers):
            task.status      = Task.Status.PENDING
            task.error_detail = ""
            task.save(update_fields=["status", "error_detail", "updated_at"])
            process_task.delay(task.id)
            requeued += 1
    log.info("retry_sweep_complete", requeued=requeued)
    return {"requeued": requeued}
