
from typing import Literal

from pydantic import BaseModel, Field


class CareCaseAssignmentCreate(BaseModel):
    recipient_facility_user_id: int = Field(gt=0)

    assignment_reason: str = Field(
        min_length=10,
        max_length=1000
    )


class CareCaseStatusUpdate(BaseModel):
    new_status: Literal[
        "OPEN",
        "IN_PROGRESS",
        "AWAITING_PATIENT",
        "AWAITING_FACILITY",
        "AWAITING_TEST",
        "AWAITING_APPOINTMENT",
        "UNDER_TREATMENT",
        "UNDER_SURVEILLANCE",
        "RESOLVED",
        "CLOSED",
        "TRANSFERRED",
        "CANCELLED"
    ]

    change_reason: str = Field(
        min_length=10,
        max_length=1000
    )


class CareCaseClosureCreate(BaseModel):
    closure_type: Literal[
        "CARE_COMPLETED",
        "TRANSFERRED",
        "PATIENT_DECLINED",
        "UNABLE_TO_CONTACT",
        "DUPLICATE_CASE",
        "NOT_CLINICALLY_INDICATED",
        "OTHER_AUTHORISED"
    ]

    closure_reason: str = Field(
        min_length=10,
        max_length=2000
    )

    evidence_summary: str = Field(
        min_length=10,
        max_length=2000
    )
