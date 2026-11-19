from pydantic import BaseModel, Field
from typing import Literal


class HandoffSend(BaseModel):
    event_notes: str | None = Field(
        default=None,
        max_length=2000
    )

    external_reference: str | None = Field(
        default=None,
        max_length=255
    )


class HandoffReceive(BaseModel):
    event_notes: str | None = Field(
        default=None,
        max_length=2000
    )

    external_reference: str | None = Field(
        default=None,
        max_length=255
    )

class HandoffDecision(BaseModel):
    decision: Literal["ACCEPTED", "REJECTED"]

    decision_reason: str = Field(
        min_length=5,
        max_length=2000
    )    