from sqlalchemy import (
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    text,
    Index
)
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import mapped_column

from app.database.connection import Base


class CaseAssignment(Base):
    __tablename__ = "case_assignments"
    __table_args__ = (
        Index("idx_assignment_case", "case_id"),
        Index("idx_assignment_owner", "facility_user_id"),
        Index("idx_assignment_current", "is_current"),
    )

    assignment_id = mapped_column(
        BIGINT(unsigned=True),
        primary_key=True,
        autoincrement=True
    )

    case_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("care_cases.case_id"),
        nullable=False
    )

    facility_user_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("facility_users.facility_user_id"),
        nullable=False
    )

    assigned_by = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("users.user_id"),
        nullable=False
    )

    assignment_reason = mapped_column(
        Text,
        nullable=True
    )

    assigned_at = mapped_column(
        DateTime,
        nullable=True,
        server_default=text("CURRENT_TIMESTAMP")
    )

    due_at = mapped_column(
        DateTime,
        nullable=True
    )

    ended_at = mapped_column(
        DateTime,
        nullable=True
    )

    is_current = mapped_column(
        Boolean,
        nullable=True,
        server_default=text("1")
    )