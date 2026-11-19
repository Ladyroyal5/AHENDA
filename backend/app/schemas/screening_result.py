from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Literal


class ScreeningResultCreate(BaseModel):

    patient_public_id: str = Field(min_length=36, max_length=36)

    programme_id: int = Field(gt=0)

    external_result_reference: str | None = Field(
        default=None,
        max_length=100
    )

    test_name: str = Field(
        min_length=2,
        max_length=200
    )

    result_value: str | None = None

    result_unit: str | None = Field(
        default=None,
        max_length=50
    )

    reference_range: str | None = Field(
        default=None,
        max_length=255
    )

    result_classification: str | None = Field(
        default=None,
        max_length=50
    )

    issued_at: datetime | None = None


class ScreeningResultResponse(BaseModel):

    public_id: str
    test_name: str
    result_value: str | None
    result_unit: str | None
    reference_range: str | None
    result_classification: str | None
    review_status: str | None
    actionability_status: str | None
    clinical_urgency: str | None
    issued_at: datetime | None
    received_at: datetime | None

    model_config = ConfigDict(from_attributes=True)

class ScreeningResultReview(BaseModel):

    actionability_status: Literal[
        "ACTIONABLE",
        "NOT_ACTIONABLE",
        "NEEDS_REVIEW"
    ]

    clinical_urgency: Literal[
        "ROUTINE",
        "SOON",
        "URGENT",
        "EMERGENCY"
    ] | None = None 