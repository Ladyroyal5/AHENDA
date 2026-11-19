from pydantic import BaseModel, Field


class EscalationResolve(BaseModel):
    resolution_notes: str = Field(
        min_length=10,
        max_length=2000
    )