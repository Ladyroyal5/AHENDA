
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field



class ConsultationCreate(BaseModel):
    consultation_type: Literal[
        "PATIENT_CLINICIAN",
        "CLINICIAN_CLINICIAN",
        "SPECIALIST_REVIEW"
    ]

    consultation_channel: Literal[
        "IN_PERSON",
        "PHONE",
        "VIDEO",
        "SECURE_MESSAGE"
    ]

    scheduled_at: datetime | None = None


class ConsultationOutcome(BaseModel):
    outcome_summary: str = Field(
        min_length=10,
        max_length=5000
    )

    follow_up_required: bool

class ConsultationSchedule(BaseModel):
    scheduled_at: datetime  


class ConsultationCompletion(BaseModel):
    outcome_summary: str = Field(
        min_length=10,
        max_length=5000
    )

    follow_up_required: bool
