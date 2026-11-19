from sqlalchemy import (
    String,
    Text,
    Enum,
    Boolean,
    DateTime,
    TIMESTAMP,
    ForeignKey,
    Index,
    text
)
from sqlalchemy.dialects.mysql import BIGINT, CHAR
from sqlalchemy.orm import mapped_column

from app.database.connection import Base


class ClinicalOutcome(Base):
    __tablename__ = "clinical_outcomes"
    __table_args__ = (
        Index("idx_outcome_case", "case_id"),
    )

    outcome_id = mapped_column(
        BIGINT(unsigned=True),
        primary_key=True,
        autoincrement=True
    )

    public_id = mapped_column(
        CHAR(36),
        nullable=False,
        unique=True
    )

    case_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("care_cases.case_id"),
        nullable=False
    )

    facility_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("facilities.facility_id"),
        nullable=False
    )

    recorded_by = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("facility_users.facility_user_id"),
        nullable=False
    )

    outcome_type = mapped_column(
        Enum(
            "CONFIRMATORY_TEST",
            "TREATMENT_INITIATED",
            "TREATMENT_COMPLETED",
            "SURVEILLANCE",
            "SPECIALIST_REVIEW",
            "OTHER"
        ),
        nullable=False
    )

    outcome_status = mapped_column(
        String(50),
        nullable=False
    )

    outcome_summary = mapped_column(
        Text,
        nullable=True
    )

    occurred_at = mapped_column(
        DateTime,
        nullable=False
    )

    follow_up_required = mapped_column(
        Boolean,
        nullable=True,
        server_default=text("0")
    )

    next_follow_up_at = mapped_column(
        DateTime,
        nullable=True
    )

    review_status = mapped_column(
        Enum(
            "PENDING",
            "REVIEWED",
            "REQUIRES_ACTION"
        ),
        nullable=False,
        server_default=text("'PENDING'")
    )

    reviewed_by = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("facility_users.facility_user_id"),
        nullable=True
    )

    reviewed_at = mapped_column(
        DateTime,
        nullable=True
    )

    review_notes = mapped_column(
        Text,
        nullable=True
    )

    created_at = mapped_column(
        TIMESTAMP,
        nullable=True,
        server_default=text("CURRENT_TIMESTAMP")
    )