from sqlalchemy import (
    DateTime,
    TIMESTAMP,
    ForeignKey,
    Enum,
    Index,
    text
)
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import mapped_column

from app.database.connection import Base


class PatientFacilityRelationship(Base):
    __tablename__ = "patient_facility_relationships"

    __table_args__ = (
        Index(
            "idx_pfr_patient_facility_status",
            "patient_id",
            "facility_id",
            "relationship_status"
        ),
        Index(
            "idx_pfr_facility_patient_status",
            "facility_id",
            "patient_id",
            "relationship_status"
        ),
    )

    relationship_id = mapped_column(
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
        nullable=False
    )

    relationship_type = mapped_column(
        Enum(
            "REGISTRATION",
            "SCREENING",
            "CARE",
            "FOLLOW_UP",
            "OTHER"
        ),
        nullable=False
    )

    relationship_status = mapped_column(
        Enum("ACTIVE", "ENDED", "SUSPENDED"),
        nullable=False,
        server_default=text("'ACTIVE'")
    )

    established_by = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("users.user_id"),
        nullable=False
    )

    established_at = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP")
    )

    ended_at = mapped_column(
        DateTime,
        nullable=True
    )

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