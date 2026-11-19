
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ReferralCreate(BaseModel):
    receiving_facility_id: int = Field(gt=0)

    specialty: str | None = Field(
        default=None,
        max_length=150
    )

    referral_type: str = Field(
        min_length=3,
        max_length=100
    )

    referral_reason: str = Field(
        min_length=10,
        max_length=2000
    )

    urgency: Literal[
        "ROUTINE",
        "SOON",
        "URGENT",
        "EMERGENCY"
    ]

    due_at: datetime | None = None

class ReferralStatusUpdate(BaseModel):
    referral_status: Literal[
        "ISSUED",
        "SENT",
        "ACKNOWLEDGED",
        "ACCEPTED",
        "REJECTED",
        "CANCELLED",
        "COMPLETED"
    ]
    change_reason: str = Field(min_length=5, max_length=1000)