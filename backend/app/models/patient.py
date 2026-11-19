
from sqlalchemy import (
    String, Date, Boolean, TIMESTAMP, DateTime,
    ForeignKey, text
)
from sqlalchemy.dialects.mysql import BIGINT, CHAR, ENUM
from sqlalchemy.orm import mapped_column

from app.database.connection import Base


class Patient(Base):
    __tablename__ = "patients"

    patient_id = mapped_column(
        BIGINT(unsigned=True),
        primary_key=True,
        autoincrement=True
    )

    public_id = mapped_column(
    CHAR(36),
    nullable=False,
    unique=True
    )



    first_name = mapped_column(String(100), nullable=False)
    last_name = mapped_column(String(100), nullable=False)
    middle_name = mapped_column(String(100), nullable=True)

    date_of_birth = mapped_column(Date, nullable=True)
    sex = mapped_column(String(30), nullable=True)

    phone_number = mapped_column(String(30), nullable=True)
    email = mapped_column(String(255), nullable=True)

    preferred_language = mapped_column(
    String(50),
    nullable=True,
    server_default=text("'English'")
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

    is_active = mapped_column(
        Boolean,
        nullable=True,
        server_default=text("1")
    )



class PatientUserAccount(Base):
    __tablename__ = "patient_user_accounts"

    account_link_id = mapped_column(
        BIGINT(unsigned=True),
        primary_key=True,
        autoincrement=True
    )

    user_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("users.user_id"),
        nullable=False,
        unique=True
    )

    patient_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("patients.patient_id"),
        nullable=False,
        unique=True
    )

    account_status = mapped_column(
        ENUM("PENDING", "VERIFIED", "SUSPENDED"),
        nullable=False,
        server_default=text("'PENDING'")
    )

    created_by = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("facility_users.facility_user_id"),
        nullable=False
    )

    verified_by = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("facility_users.facility_user_id"),
        nullable=True
    )

    created_at = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP")
    )

    verified_at = mapped_column(
        DateTime,
        nullable=True
    )

