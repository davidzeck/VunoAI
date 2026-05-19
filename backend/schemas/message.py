from pydantic import BaseModel, Field


class MessageOutput(BaseModel):
    whatsapp: str = Field(max_length=500)
    email:    str
    sms:      str = Field(max_length=160)
