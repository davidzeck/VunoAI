from pydantic import BaseModel, Field


class WorkflowOutput(BaseModel):
    steps: list[str] = Field(min_length=3, max_length=10)
