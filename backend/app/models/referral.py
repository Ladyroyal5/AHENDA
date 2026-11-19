from sqlalchemy import (
    String,
    Text,
    DateTime,
    TIMESTAMP,
    ForeignKey,
    Enum,
    Index,
    text
)
from sqlalchemy.dialects.mysql import BIGINT, CHAR
from sqlalchemy.orm import mapped_column

from app.database.connection import Base


class Referral(Base):
    __tablename__ = "referrals"
    __table_args__ = (
        Index("idx_referral_case", "case_id"),
        Index("idx_referral_receiving_facility", "receiving_facility_id"),
        Index("idx_referral_status", "referral_status"),
    )

    referral_id = mapped_column(
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

    consultation_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("consultations.consultation_id"),
        nullable=True
    )

    referring_facility_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("facilities.facility_id"),
        nullable=False
    )

    receiving_facility_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("facilities.facility_id"),
        nullable=False
    )

    referred_by = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("users.user_id"),
        nullable=False
    )

    specialty = mapped_column(
        String(150),
        nullable=True
    )

    referral_type = mapped_column(
        String(100),
        nullable=False
    )

    referral_reason = mapped_column(
        Text,
        nullable=False
    )

    urgency = mapped_column(
        Enum("ROUTINE", "SOON", "URGENT", "EMERGENCY"),
        nullable=False
    )

    referral_status = mapped_column(
        Enum(
            "DRAFT",
            "ISSUED",
            "SENT",
            "ACKNOWLEDGED",
            "ACCEPTED",
            "REJECTED",
            "CANCELLED",
            "COMPLETED"
        ),
        nullable=True,
        server_default=text("'DRAFT'")
    )

    issued_at = mapped_column(DateTime, nullable=True)

    due_at = mapped_column(DateTime, nullable=True)

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
