from sqlalchemy import (
    String,
    JSON,
    DateTime,
    ForeignKey,
    Index,
    text
)
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import mapped_column

from app.database.connection import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("idx_audit_actor", "actor_user_id"),
        Index("idx_audit_entity", "entity_type", "entity_id"),
        Index("idx_audit_created_at", "created_at"),
    )

    audit_id = mapped_column(
        BIGINT(unsigned=True),
        primary_key=True,
        autoincrement=True
    )

    actor_user_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("users.user_id"),
        nullable=True
    )

    facility_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("facilities.facility_id"),
        nullable=True
    )

    action = mapped_column(
        String(100),
        nullable=False
    )

    entity_type = mapped_column(
        String(100),
        nullable=False
    )

    entity_id = mapped_column(
        String(100),
        nullable=False
    )

    old_values = mapped_column(
        JSON,
        nullable=True
    )

    new_values = mapped_column(
        JSON,
        nullable=True
    )

    ip_address = mapped_column(
        String(45),
        nullable=True
    )

    created_at = mapped_column(
        DateTime,
        nullable=True,
        server_default=text("CURRENT_TIMESTAMP")
    )