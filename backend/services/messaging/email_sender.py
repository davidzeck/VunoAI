from django.conf import settings
from django.core.mail import send_mail


def send_email(to_address: str, subject: str, body: str) -> None:
    send_mail(
        subject=subject,
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[to_address],
        fail_silently=False,
    )
