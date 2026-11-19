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


class CaseStatusHistory(Base):
    __tablename__ = "case_status_history"
    __table_args__ = (
        Index("idx_case_history_case", "case_id"),
        Index("idx_case_history_changed_at", "changed_at"),
    )

    history_id = mapped_column(
        BIGINT(unsigned=True),
        primary_key=True,
        autoincrement=True
    )

    case_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("care_cases.case_id"),
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