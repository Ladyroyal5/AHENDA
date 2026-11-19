from sqlalchemy import String, Text, TIMESTAMP, text
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import mapped_column

from app.database.connection import Base


class Role(Base):
    __tablename__ = "roles"

    role_id = mapped_column(
        BIGINT(unsigned=True),
        primary_key=True,
        autoincrement=True
    )

    role_name = mapped_column(
        String(100),
        nullable=False,
        unique=True
    )

    description = mapped_column(
        Text,
        nullable=True
    )

    created_at = mapped_column(
        TIMESTAMP,
        nullable=True,
        server_default=text("CURRENT_TIMESTAMP")
    )