
from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    TIMESTAMP,
    text
)
from sqlalchemy.dialects.mysql import BIGINT, CHAR
from sqlalchemy.orm import mapped_column

from app.database.connection import Base


class PatientActivationToken(Base):
    __tablename__ = "patient_activation_tokens"

    activation_token_id = mapped_column(
        BIGINT(unsigned=True),
        primary_key=True,
        autoincrement=True
    )

    user_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("users.user_id"),
        nullable=False,
        index=True
    )

    token_hash = mapped_column(
        CHAR(64),
        nullable=False,
        unique=True
    )

    expires_at = mapped_column(
        DateTime,
        nullable=False
    )

    used_at = mapped_column(
        DateTime,
        nullable=True
    )

    revoked_at = mapped_column(
        DateTime,
        nullable=True
    )

    created_at = mapped_column(
        TIMESTAMP,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP")
    )
