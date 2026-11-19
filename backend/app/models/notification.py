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


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("idx_notification_case", "case_id"),
        Index("idx_notification_patient", "patient_id"),
        Index("idx_notification_delivery", "delivery_status"),
    )

    notification_id = mapped_column(
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

    case_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("care_cases.case_id"),
        nullable=False
    )

    channel = mapped_column(
        Enum("SMS", "WHATSAPP", "EMAIL", "IN_APP", "PHONE"),
        nullable=False
    )

    notification_type = mapped_column(
        String(100),
        nullable=False
    )

    message_reference = mapped_column(
        String(150),
        nullable=True
    )

    delivery_status = mapped_column(
        Enum("PENDING", "SENT", "DELIVERED", "FAILED", "CANCELLED"),
        nullable=True,
        server_default=text("'PENDING'")
    )

    external_message_id = mapped_column(
        String(255),
        nullable=True,
        unique=True
    )

    sent_at = mapped_column(DateTime, nullable=True)

    delivered_at = mapped_column(DateTime, nullable=True)

    failure_reason = mapped_column(Text, nullable=True)

    created_at = mapped_column(
        TIMESTAMP,
        nullable=True,
        server_default=text("CURRENT_TIMESTAMP")
    )