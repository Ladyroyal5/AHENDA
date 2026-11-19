from sqlalchemy import String, Text, Boolean, TIMESTAMP, text
from sqlalchemy.dialects.mysql import BIGINT, CHAR
from sqlalchemy.orm import mapped_column

from app.database.connection import Base


class ScreeningProgramme(Base):
    __tablename__ = "screening_programmes"

    programme_id = mapped_column(
        BIGINT(unsigned=True),
        primary_key=True,
        autoincrement=True
    )

    public_id = mapped_column(
        CHAR(36),
        nullable=False,
        unique=True
    )

    programme_name = mapped_column(
        String(200),
        nullable=False
    )

    programme_code = mapped_column(
        String(50),
        nullable=False,
        unique=True
    )

    description = mapped_column(
        Text,
        nullable=True
    )

    screening_type = mapped_column(
        String(100),
        nullable=False
    )

    target_population = mapped_column(
        Text,
        nullable=True
    )

    is_active = mapped_column(
        Boolean,
        nullable=True,
        server_default=text("1")
    )

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