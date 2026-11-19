from sqlalchemy import (
    Text,
    String,
    Enum,
    DateTime,
    ForeignKey,
    Index,
    text
)
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import mapped_column

from app.database.connection import Base


class HandoffEvent(Base):
    __tablename__ = "handoff_events"
    __table_args__ = (
        Index("idx_handoff_event_handoff", "handoff_id"),
        Index("idx_handoff_event_time", "event_at"),
    )

    event_id = mapped_column(
        BIGINT(unsigned=True),
        primary_key=True,
        autoincrement=True
    )

    handoff_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("handoffs.handoff_id"),
        nullable=False
    )

    actor_facility_user_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("facility_users.facility_user_id"),
        nullable=True
    )

    event_type = mapped_column(
        Enum(
            "PREPARED",
            "SENT",
            "RECEIVED",
            "ACCEPTED",
            "REJECTED",
            "RETURNED",
            "EXPIRED",
            "RESOLVED"
        ),
        nullable=False
    )

    event_notes = mapped_column(
        Text,
        nullable=True
    )

    external_reference = mapped_column(
        String(255),
        nullable=True
    )

    event_at = mapped_column(
        DateTime,
        nullable=True,
        server_default=text("CURRENT_TIMESTAMP")
    )