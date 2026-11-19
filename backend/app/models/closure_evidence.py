from sqlalchemy import (
    String,
    Text,
    DateTime,
    ForeignKey,
    TIMESTAMP,
    Index,
    text
)
from sqlalchemy.dialects.mysql import BIGINT, CHAR
from sqlalchemy.orm import mapped_column

from app.database.connection import Base


class ClosureEvidence(Base):
    __tablename__ = "closure_evidence"
    __table_args__ = (
        Index("idx_closure_evidence_closure", "closure_id"),
    )

    evidence_id = mapped_column(
        BIGINT(unsigned=True),
        primary_key=True,
        autoincrement=True
    )

    closure_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("case_closures.closure_id"),
        nullable=False
    )

    evidence_type = mapped_column(
        String(100),
        nullable=False
    )

    evidence_reference = mapped_column(
        String(255),
        nullable=True
    )

    evidence_description = mapped_column(
        Text,
        nullable=True
    )

    file_hash = mapped_column(
        CHAR(64),
        nullable=True
    )

    uploaded_by = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("users.user_id"),
        nullable=False
    )

    uploaded_at = mapped_column(
        DateTime,
        nullable=True,
        server_default=text("CURRENT_TIMESTAMP")
    )