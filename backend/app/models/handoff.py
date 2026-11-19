from sqlalchemy import (
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


class Handoff(Base):
    __tablename__ = "handoffs"
    __table_args__ = (
        Index("idx_handoff_referral", "referral_id"),
        Index("idx_handoff_receiving_facility", "receiving_facility_id"),
        Index("idx_handoff_status", "handoff_status"),
    )

    handoff_id = mapped_column(
        BIGINT(unsigned=True),
        primary_key=True,
        autoincrement=True
    )

    public_id = mapped_column(
        CHAR(36),
        nullable=False,
        unique=True
    )

    referral_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("referrals.referral_id"),
        nullable=False
    )

    sending_facility_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("facilities.facility_id"),
        nullable=False
    )

    receiving_facility_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("facilities.facility_id"),
        nullable=False
    )

    sent_by = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("facility_users.facility_user_id"),
        nullable=False
    )

    received_by = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("facility_users.facility_user_id"),
        nullable=True
    )

    accepted_by = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("facility_users.facility_user_id"),
        nullable=True
    )

    handoff_status = mapped_column(
        Enum(
            "PREPARED",
            "SENT",
            "RECEIVED",
            "ACCEPTED",
            "REJECTED",
            "RETURNED",
            "EXPIRED"
        ),
        nullable=True,
        server_default=text("'PREPARED'")
    )

    sent_at = mapped_column(DateTime, nullable=True)

    received_at = mapped_column(DateTime, nullable=True)

    accepted_at = mapped_column(DateTime, nullable=True)

    rejected_at = mapped_column(DateTime, nullable=True)

    rejection_reason = mapped_column(Text, nullable=True)

    created_at = mapped_column(
        TIMESTAMP,
        nullable=True,
        server_default=text("CURRENT_TIMESTAMP")
    )