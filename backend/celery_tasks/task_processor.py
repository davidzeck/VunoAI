import structlog
from celery import shared_task

log = structlog.get_logger()


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def process_task(self, task_id: int):
    from apps.tasks.models import Task
    from services.task_service import TaskService

    task = Task.objects.get(id=task_id)
    service = TaskService()

    try:
        service.run_pipeline(task)

    except Exception as exc:
        from services.ai.base import AllProvidersExhaustedError

        if isinstance(exc, AllProvidersExhaustedError):
            # Both providers rate-limited — don't retry immediately.
            # The midnight cron (retry_api_failures) detects "rate_limit" in error_detail
            # and requeues automatically.
            log.warning("all_providers_exhausted", task_id=task_id, task_code=task.task_code)
            task.status       = Task.Status.FAILED
            task.error_detail = str(exc)   # starts with "rate_limit_exceeded:"
            task.save(update_fields=["status", "error_detail", "updated_at"])
        else:
            # Transient error — let Celery retry up to max_retries
            log.error("pipeline_failed", task_id=task_id, error=str(exc), attempt=self.request.retries)
            task.status       = Task.Status.FAILED
            task.error_detail = str(exc)
            task.save(update_fields=["status", "error_detail", "updated_at"])
            raise self.retry(exc=exc)
