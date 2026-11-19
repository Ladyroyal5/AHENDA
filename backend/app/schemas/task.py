from pydantic import BaseModel, Field
from datetime import datetime


class TaskCompletion(BaseModel):
    completion_notes: str = Field(
        min_length=5,
        max_length=1000
    )


class TaskCreate(BaseModel):
    case_id: int = Field(gt=0)
    assigned_to: int = Field(gt=0)
    task_type: str = Field(min_length=3, max_length=100)
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=2000)
    priority: str = Field(
        pattern="^(LOW|NORMAL|HIGH|URGENT)$"
    )
    due_at: datetime | None = None


class ClinicalOutcomeFollowUpTask(BaseModel):
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

class TaskCancellation(BaseModel):
    cancellation_reason: str = Field(
        min_length=10,
        max_length=1000
    )