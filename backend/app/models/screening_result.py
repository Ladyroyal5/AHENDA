from sqlalchemy import (
    String,
    Text,
    DateTime,
    TIMESTAMP,
    ForeignKey,
    Enum,
    text,
    UniqueConstraint,
    Index
)
from sqlalchemy.dialects.mysql import BIGINT, CHAR
from sqlalchemy.orm import mapped_column

from app.database.connection import Base


class ScreeningResult(Base):
    __tablename__ = "screening_results"
    __table_args__ = (
        UniqueConstraint(
            "facility_id",
            "external_result_reference",
            name="uq_facility_external_result"
        ),

        Index("idx_result_facility", "facility_id"),
        Index("idx_result_patient", "patient_id"),
        Index("idx_result_review", "review_status"),
        Index("idx_result_actionability", "actionability_status"),
    )

    result_id = mapped_column(
        BIGINT(unsigned=True),
        primary_key=True,
        autoincrement=True
    )

    public_id = mapped_column(
        CHAR(36),
        nullable=False,
        unique=True
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

    programme_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("screening_programmes.programme_id"),
        nullable=False
    )

    submitted_by = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("users.user_id"),
        nullable=False
    )

    reviewed_by = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("users.user_id"),
        nullable=True
    )

    external_result_reference = mapped_column(
        String(100),
        nullable=True
    )

    test_name = mapped_column(
        String(200),
        nullable=False
    )

    result_value = mapped_column(Text, nullable=True)

    result_unit = mapped_column(String(50), nullable=True)

    reference_range = mapped_column(String(255), nullable=True)

    result_classification = mapped_column(
        String(50),
        nullable=True
    )

    review_status = mapped_column(
        Enum(
            "PENDING",
            "UNDER_REVIEW",
            "REVIEWED",
            "CORRECTED",
            "CANCELLED"
        ),
        nullable=True,
        server_default=text("'PENDING'")
    )

    actionability_status = mapped_column(
        Enum(
            "PENDING",
            "ACTIONABLE",
            "NOT_ACTIONABLE",
            "NEEDS_REVIEW"
        ),
        nullable=True,
        server_default=text("'PENDING'")
    )

    clinical_urgency = mapped_column(
        Enum("ROUTINE", "SOON", "URGENT", "EMERGENCY"),
        nullable=True
    )

    issued_at = mapped_column(DateTime, nullable=True)

    received_at = mapped_column(
        DateTime,
        nullable=True,
        server_default=text("CURRENT_TIMESTAMP")
    )

    reviewed_at = mapped_column(DateTime, nullable=True)

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