
from sqlalchemy import (
    String,
    CHAR,
    Text,
    Enum,
    TIMESTAMP,
    DateTime,
    ForeignKey,
    Index,
    text
)
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import mapped_column

from app.database.connection import Base


class IdentityReviewCase(Base):
    __tablename__ = "identity_review_cases"

    __table_args__ = (
        Index("idx_review_status", "review_status"),
        Index("idx_review_patient", "patient_id"),
        Index("idx_review_matched_patient", "matched_patient_id"),
    )

    review_id = mapped_column(
        BIGINT(unsigned=True),
        primary_key=True,
        autoincrement=True
    )

    patient_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("patients.patient_id"),
        nullable=False
    )

    matched_patient_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("patients.patient_id"),
        nullable=False
    )

    identifier_type = mapped_column(
        String(50),
        nullable=False
    )

    identifier_hash = mapped_column(
        CHAR(64),
        nullable=False
    )

    review_status = mapped_column(
        Enum("PENDING", "CONFIRMED_MATCH", "REJECTED"),
        nullable=False,
        server_default=text("'PENDING'")
    )

    reviewed_by = mapped_column(
    BIGINT(unsigned=True),
    ForeignKey("users.user_id"),
    nullable=True
)  

    reviewed_at = mapped_column(DateTime, nullable=True)

    review_notes = mapped_column(Text, nullable=True)

    created_at = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP")
    )
