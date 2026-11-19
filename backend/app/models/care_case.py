from sqlalchemy import (
    DateTime,
    TIMESTAMP,
    ForeignKey,
    Enum,
    text,
    Index
)
from sqlalchemy.dialects.mysql import BIGINT, CHAR
from sqlalchemy.orm import mapped_column

from app.database.connection import Base


class CareCase(Base):
    __tablename__ = "care_cases"
    __table_args__ = (
        Index("idx_case_status", "case_status"),
        Index("idx_case_patient", "patient_id"),
        Index("idx_case_priority", "priority"),
        Index("idx_case_due", "due_at"),
    )

    case_id = mapped_column(
        BIGINT(unsigned=True),
        primary_key=True,
        autoincrement=True
    )

    public_case_id = mapped_column(
        CHAR(36),
        nullable=False,
        unique=True
    )

    result_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("screening_results.result_id"),
        nullable=False,
        unique=True
    )

    patient_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("patients.patient_id"),
        nullable=False
    )

    coordinating_facility_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("facilities.facility_id"),
        nullable=False
    )

    case_status = mapped_column(
        Enum(
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
        ),
        nullable=True,
        server_default=text("'OPEN'")
    )

    priority = mapped_column(
        Enum("ROUTINE", "LOW", "HIGH", "URGENT"),
        nullable=True,
        server_default=text("'ROUTINE'")
    )

    opened_at = mapped_column(
        DateTime,
        nullable=True,
        server_default=text("CURRENT_TIMESTAMP")
    )

    due_at = mapped_column(DateTime, nullable=True)

    resolved_at = mapped_column(DateTime, nullable=True)

    closed_at = mapped_column(DateTime, nullable=True)

    created_at = mapped_column(
        TIMESTAMP,
        nullable=True,
        server_default=text("CURRENT_TIMESTAMP")
    )

    updated_at = mapped_column(
        TIMESTAMP,
        nullable=True,
        server_default=text("CURRENT_TIMESTAMP"),
        server_onupdate=text("CURRENT_TIMESTAMP")
    )