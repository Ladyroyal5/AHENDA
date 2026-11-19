from sqlalchemy import (
    Text,
    DateTime,
    ForeignKey,
    Enum,
    Index,
    text
)
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import mapped_column

from app.database.connection import Base


class Acknowledgement(Base):
    __tablename__ = "acknowledgements"
    __table_args__ = (
        Index("idx_acknowledgement_notification", "notification_id"),
        Index("idx_acknowledgement_patient", "patient_id"),
    )

    acknowledgement_id = mapped_column(
        BIGINT(unsigned=True),
        primary_key=True,
        autoincrement=True
    )

    notification_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("notifications.notification_id"),
        nullable=False
    )

    patient_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("patients.patient_id"),
        nullable=False
    )

    acknowledgement_method = mapped_column(
        Enum("SMS", "WHATSAPP", "IN_APP", "PHONE", "IN_PERSON"),
        nullable=False
    )

    acknowledgement_status = mapped_column(
        Enum(
            "RECEIVED",
            "UNDERSTOOD",
            "NEEDS_CLARIFICATION",
            "UNABLE_TO_RESPOND"
        ),
        nullable=False
    )

    acknowledged_at = mapped_column(
        DateTime,
        nullable=True,
        server_default=text("CURRENT_TIMESTAMP")
    )

    notes = mapped_column(
        Text,
        nullable=True
    )