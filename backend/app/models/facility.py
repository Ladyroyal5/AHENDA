
from sqlalchemy import (
    String,
    Boolean,
    TIMESTAMP,
    Text
)
from sqlalchemy.dialects.mysql import BIGINT, CHAR
from sqlalchemy.orm import mapped_column
from sqlalchemy import text

from app.database.connection import Base


class Facility(Base):
    __tablename__ = "facilities"

    facility_id = mapped_column(
        BIGINT(unsigned=True),
        primary_key=True,
        autoincrement=True
    )

    public_id = mapped_column(
    CHAR(36),
    nullable=False,
    unique=True
    )


    facility_name = mapped_column(String(200), nullable=False)

    facility_code = mapped_column(
    String(50),
    nullable=False,
    unique=True
    )

    facility_type = mapped_column(String(50), nullable=False)

    address = mapped_column(Text, nullable=True)




    address = mapped_column(
    Text,
    nullable=True
    )
    city = mapped_column(String(100), nullable=True)
    state = mapped_column(String(100), nullable=True)
    country = mapped_column(String(100), nullable=True)

    email = mapped_column(String(255), nullable=True)
    phone_number = mapped_column(String(30), nullable=True)

    is_active = mapped_column(
        Boolean,
        nullable=True,
        server_default=text("1")
    )

    created_at = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP")
    )

    updated_at = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        server_onupdate=text("CURRENT_TIMESTAMP")
    )
