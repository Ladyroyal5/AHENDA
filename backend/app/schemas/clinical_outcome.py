
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ClinicalOutcomeCreate(BaseModel):
    case_id: int = Field(gt=0)

    outcome_type: Literal[
        "CONFIRMATORY_TEST",
        "TREATMENT_INITIATED",
        "TREATMENT_COMPLETED",
        "SURVEILLANCE",
        "SPECIALIST_REVIEW",
        "OTHER"
    ]

    outcome_status: str = Field(
        min_length=2,
        max_length=50
    )

    outcome_summary: str = Field(
        min_length=10,
        max_length=5000
    )

    occurred_at: datetime

    follow_up_required: bool = False

    next_follow_up_at: datetime | None = None

class ClinicalOutcomeReview(BaseModel):
    review_status: Literal[
        "REVIEWED",
        "REQUIRES_ACTION"
    ]

    review_notes: str = Field(
        min_length=10,
        max_length=5000
    )