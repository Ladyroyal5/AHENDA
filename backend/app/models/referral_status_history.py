from sqlalchemy import (
    String,
    Text,
    DateTime,
    ForeignKey,
    Index,
    text
)
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import mapped_column

from app.database.connection import Base


class ReferralStatusHistory(Base):
    __tablename__ = "referral_status_history"
    __table_args__ = (
        Index("idx_referral_history_referral", "referral_id"),
    )

    history_id = mapped_column(
        BIGINT(unsigned=True),
        primary_key=True,
        autoincrement=True
    )

    referral_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("referrals.referral_id"),
        nullable=False
    )

    previous_status = mapped_column(
        String(50),
        nullable=True
    )

    new_status = mapped_column(
        String(50),
        nullable=False
    )

    changed_by = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("users.user_id"),
        nullable=False
    )

    change_reason = mapped_column(
        Text,
        nullable=True
    )

    changed_at = mapped_column(
        DateTime,
        nullable=True,
        server_default=text("CURRENT_TIMESTAMP")
    )