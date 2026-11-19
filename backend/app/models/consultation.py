from sqlalchemy import (
    String,
    Text,
    DateTime,
    TIMESTAMP,
    Boolean,
    ForeignKey,
    Enum,
    Index,
    text
)
from sqlalchemy.dialects.mysql import BIGINT, CHAR
from sqlalchemy.orm import mapped_column

from app.database.connection import Base


class Consultation(Base):
    __tablename__ = "consultations"
    __table_args__ = (
        Index("idx_consultation_case", "case_id"),
        Index("idx_consultation_status", "consultation_status"),
    )

    consultation_id = mapped_column(
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

    clinician_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("facility_users.facility_user_id"),
        nullable=False
    )

    consultation_type = mapped_column(
        Enum(
            "PATIENT_CLINICIAN",
            "CLINICIAN_CLINICIAN",
            "SPECIALIST_REVIEW"
        ),
        nullable=False
    )

    consultation_channel = mapped_column(
        Enum("IN_PERSON", "PHONE", "VIDEO", "SECURE_MESSAGE"),
        nullable=False
    )

    consultation_status = mapped_column(
        Enum(
            "REQUESTED",
            "SCHEDULED",
            "IN_PROGRESS",
            "COMPLETED",
            "CANCELLED"
        ),
        nullable=True,
        server_default=text("'REQUESTED'")
    )

    scheduled_at = mapped_column(DateTime, nullable=True)

    started_at = mapped_column(DateTime, nullable=True)

    completed_at = mapped_column(DateTime, nullable=True)

    outcome_summary = mapped_column(Text, nullable=True)

    follow_up_required = mapped_column(
        Boolean,
        nullable=True,
        server_default=text("0")
    )

    created_at = mapped_column(
        TIMESTAMP,
        nullable=True,
        server_default=text("CURRENT_TIMESTAMP")
    )