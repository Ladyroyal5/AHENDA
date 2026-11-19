from sqlalchemy import (
    String,
    Text,
    DateTime,
    ForeignKey,
    Enum,
    Index,
    text
)
from sqlalchemy.dialects.mysql import BIGINT, CHAR
from sqlalchemy.orm import mapped_column

from app.database.connection import Base


class Escalation(Base):
    __tablename__ = "escalations"
    __table_args__ = (
        Index("idx_escalation_case", "case_id"),
        Index("idx_escalation_assigned_to", "assigned_to"),
        Index("idx_escalation_severity", "severity"),
        Index("idx_escalation_status", "escalation_status"),
    )

    escalation_id = mapped_column(
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

    task_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("tasks.task_id"),
        nullable=True
    )

    assigned_to = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("facility_users.facility_user_id"),
        nullable=True
    )

    triggered_by = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("users.user_id"),
        nullable=True
    )

    escalation_type = mapped_column(
        String(100),
        nullable=False
    )

    severity = mapped_column(
        Enum("LOW", "MEDIUM", "HIGH", "CRITICAL"),
        nullable=False
    )

    escalation_reason = mapped_column(
        Text,
        nullable=False
    )

    escalation_status = mapped_column(
        Enum(
            "OPEN",
            "ACKNOWLEDGED",
            "IN_PROGRESS",
            "RESOLVED",
            "CLOSED"
        ),
        nullable=True,
        server_default=text("'OPEN'")
    )

    created_at = mapped_column(
        DateTime,
        nullable=True,
        server_default=text("CURRENT_TIMESTAMP")
    )

    acknowledged_at = mapped_column(
        DateTime,
        nullable=True
    )

    resolved_at = mapped_column(
        DateTime,
        nullable=True
    )

    resolution_notes = mapped_column(
        Text,
        nullable=True
    )