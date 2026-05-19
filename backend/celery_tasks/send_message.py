import structlog
from celery import shared_task
from django.utils.timezone import now

log = structlog.get_logger()


@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def send_channel_message(self, message_id: int):
    from apps.tasks.models import GeneratedMessage

    msg = GeneratedMessage.objects.select_related("task").get(pk=message_id)
    log.info("send_message_started", channel=msg.channel, task_code=msg.task.task_code)

    try:
        if msg.channel == "whatsapp":
            from services.messaging.whatsapp import send_whatsapp
            send_whatsapp(msg.recipient, msg.content)

        elif msg.channel == "email":
            from services.messaging.email_sender import send_email
            subject = f"Vunoh Request {msg.task.task_code} — Update"
            send_email(msg.recipient, subject, msg.content)

        else:
            raise ValueError(f"Unsupported channel for sending: {msg.channel}")

        msg.sent_at    = now()
        msg.send_error = ""
        msg.save(update_fields=["sent_at", "send_error"])
        log.info("send_message_success", channel=msg.channel, task_code=msg.task.task_code)

    except Exception as exc:
        msg.send_error = str(exc)
        msg.save(update_fields=["send_error"])
        log.warning("send_message_failed", channel=msg.channel, error=str(exc))
        raise self.retry(exc=exc)
