from sqlalchemy import (
    String,
    Text,
    Enum,
    DateTime,
    ForeignKey,
    Index,
    text
)
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import mapped_column

from app.database.connection import Base


class ConsentRecord(Base):
    __tablename__ = "consent_records"
    __table_args__ = (
        Index("idx_consent_patient", "patient_id"),
        Index("idx_consent_status", "consent_status"),
    )

    consent_id = mapped_column(
        BIGINT(unsigned=True),
        primary_key=True,
        autoincrement=True
    )

    patient_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("patients.patient_id"),
        nullable=False
    )

    facility_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("facilities.facility_id"),
        nullable=True
    )

    consent_type = mapped_column(
        String(100),
        nullable=False
    )

    consent_status = mapped_column(
        Enum("GRANTED", "DENIED", "WITHDRAWN", "EXPIRED"),
        nullable=False
    )

    consent_method = mapped_column(
        Enum("WRITTEN", "DIGITAL", "VERBAL", "OTHER"),
        nullable=False
    )

    consent_version = mapped_column(
        String(30),
        nullable=True
    )

    recorded_by = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("users.user_id"),
        nullable=True
    )

    recorded_at = mapped_column(
        DateTime,
        nullable=True,
        server_default=text("CURRENT_TIMESTAMP")
    )

    withdrawn_at = mapped_column(
        DateTime,
        nullable=True
    )

    notes = mapped_column(
        Text,
        nullable=True
    )