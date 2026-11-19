from sqlalchemy import (
    String,
    Text,
    Enum,
    DateTime,
    TIMESTAMP,
    Index,
    ForeignKey,
    text
)
from sqlalchemy.dialects.mysql import BIGINT, CHAR
from sqlalchemy.orm import mapped_column

from app.database.connection import Base


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (
        Index("idx_appointment_case", "case_id"),
        Index("idx_appointment_patient", "patient_id"),
        Index("idx_appointment_facility", "facility_id"),
        Index("idx_appointment_status", "appointment_status"),
        Index("idx_appointment_scheduled_at", "scheduled_at"),
    )

    appointment_id = mapped_column(
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

    referral_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("referrals.referral_id"),
        nullable=True
    )

    patient_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("patients.patient_id"),
        nullable=False
    )

    facility_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("facilities.facility_id"),
        nullable=False
    )

    scheduled_by = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("users.user_id"),
        nullable=False
    )

    appointment_type = mapped_column(
        String(100),
        nullable=True
    )

    appointment_status = mapped_column(
        Enum(
            "REQUESTED",
            "SCHEDULED",
            "CONFIRMED",
            "ATTENDED",
            "NO_SHOW",
            "CANCELLED",
            "RESCHEDULED"
        ),
        nullable=True,
        server_default=text("'REQUESTED'")
    )

    scheduled_at = mapped_column(
        DateTime,
        nullable=False
    )

    checked_in_at = mapped_column(
        DateTime,
        nullable=True
    )

    completed_at = mapped_column(
        DateTime,
        nullable=True
    )

    cancellation_reason = mapped_column(
        Text,
        nullable=True
    )

    created_at = mapped_column(
        TIMESTAMP,
        nullable=True,
        server_default=text("CURRENT_TIMESTAMP")
    )