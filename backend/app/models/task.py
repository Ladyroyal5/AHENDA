from sqlalchemy import (
    String,
    Text,
    DateTime,
    TIMESTAMP,
    ForeignKey,
    Enum,
    text,
    Index
)
from sqlalchemy.dialects.mysql import BIGINT, CHAR
from sqlalchemy.orm import mapped_column

from app.database.connection import Base


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        Index("idx_task_status", "task_status"),
        Index("idx_task_case", "case_id"),
        Index("idx_task_assigned_to", "assigned_to"),
        Index("idx_task_due", "due_at"),
    )

    task_id = mapped_column(
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

    clinical_outcome_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("clinical_outcomes.outcome_id"),
        nullable=True,
        unique=True
    )

    recommendation_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey(
            "intervention_recommendations.recommendation_id"
        ),
        nullable=True,
        unique=True
    )

    assigned_to = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("facility_users.facility_user_id"),
        nullable=True
    )

    assigned_by = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("users.user_id"),
        nullable=False
    )

    task_type = mapped_column(String(100), nullable=False)

    title = mapped_column(String(200), nullable=False)

    description = mapped_column(Text, nullable=True)

    task_status = mapped_column(
        Enum(
            "PENDING",
            "IN_PROGRESS",
            "COMPLETED",
            "CANCELLED",
            "OVERDUE"
        ),
        nullable=True,
        server_default=text("'PENDING'")
    )

    priority = mapped_column(
        Enum("LOW", "NORMAL", "HIGH", "URGENT"),
        nullable=True,
        server_default=text("'NORMAL'")
    )

    due_at = mapped_column(DateTime, nullable=True)

    completed_at = mapped_column(DateTime, nullable=True)

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