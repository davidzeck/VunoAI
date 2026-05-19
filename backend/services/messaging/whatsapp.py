from decouple import config
from twilio.rest import Client


def send_whatsapp(to_number: str, body: str) -> str:
    client = Client(config("TWILIO_ACCOUNT_SID"), config("TWILIO_AUTH_TOKEN"))
    msg = client.messages.create(
        from_=f"whatsapp:{config('TWILIO_WHATSAPP_FROM')}",
        to=f"whatsapp:{to_number}",
        body=body,
    )
    return msg.sid
