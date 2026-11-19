
from sqlalchemy import (
    String,
    TIMESTAMP,
    ForeignKey,
    UniqueConstraint,
    Index,
    Computed,
    text,
)
from sqlalchemy.dialects.mysql import BIGINT, CHAR
from sqlalchemy.orm import mapped_column

from app.database.connection import Base


class PatientIdentifier(Base):
    __tablename__ = "patient_identifiers"

    __table_args__ = (
        UniqueConstraint(
            "facility_id",
            "identifier_type",
            "identifier_hash",
            name="uq_patient_identifier"
        ),
        Index(
            "idx_identifier_patient",
            "patient_id"
        ),

        UniqueConstraint(
            "facility_scope",
            "identifier_type",
            "identifier_hash",
            name="uq_patient_identifier_scope"
        ),

    )
    

    identifier_id = mapped_column(
        BIGINT(unsigned=True),
        primary_key=True,
        autoincrement=True
    )

    patient_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey(
            "patients.patient_id",
            name="fk_identifier_patient"
        ),
        nullable=False
    )

    facility_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey(
            "facilities.facility_id",
            name="fk_identifier_facility"
        ),
        nullable=True
    )

    identifier_type = mapped_column(
        String(50),
        nullable=False
    )

    identifier_hash = mapped_column(
        CHAR(64),
        nullable=False
    )

    created_at = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=True
    )

    facility_scope = mapped_column(
        BIGINT(unsigned=True),
        Computed("COALESCE(facility_id, 0)", persisted=True)
    )



 