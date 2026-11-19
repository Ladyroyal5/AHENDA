from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime


class InterventionReview(BaseModel):
    review_status: Literal["APPROVED", "REJECTED"]
    review_notes: str | None = Field(
        default=None,
        max_length=2000
    )

class InterventionExecutionTask(BaseModel):
    assigned_to: int = Field(gt=0)

    title: str = Field(
        min_length=3,
        max_length=200
    )

    description: str = Field(
        min_length=10,
        max_length=2000
    )

    priority: str = Field(
        pattern="^(LOW|NORMAL|HIGH|URGENT)$"
    )

    due_at: datetime | None = None    