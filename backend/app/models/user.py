
import enum

from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    TIMESTAMP,
    Enum,
    text
)
from sqlalchemy.dialects.mysql import BIGINT, CHAR
from sqlalchemy.orm import mapped_column

from app.database.connection import Base


class AccountType(str, enum.Enum):
    STAFF = "STAFF"
    PATIENT = "PATIENT"


class User(Base):
    __tablename__ = "users"

    user_id = mapped_column(
        BIGINT(unsigned=True),
        primary_key=True,
        autoincrement=True
    )

    public_id = mapped_column(
        CHAR(36),
        nullable=False,
        unique=True
    )

    first_name = mapped_column(
        String(100),
        nullable=False
    )

    last_name = mapped_column(
        String(100),
        nullable=False
    )

    email = mapped_column(
        String(255),
        nullable=False,
        unique=True
    )

    password_hash = mapped_column(
        String(255),
        nullable=False
    )

    account_type = mapped_column(
        Enum(
            AccountType,
            values_callable=lambda enum_cls: [
                item.value for item in enum_cls
            ],
            name="account_type_enum"
        ),
        nullable=False,
        default=AccountType.STAFF,
        server_default=text("'STAFF'")
    )

    phone_number = mapped_column(
        String(30),
        nullable=True
    )

    is_active = mapped_column(
        Boolean,
        nullable=True,
        server_default=text("1")
    )

    last_login = mapped_column(
        DateTime,
        nullable=True
    )

    created_at = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=True
    )

    updated_at = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        server_onupdate=text("CURRENT_TIMESTAMP"),
        nullable=True
    )