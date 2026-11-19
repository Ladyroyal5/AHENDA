from sqlalchemy import (
    String,
    Text,
    Enum,
    DateTime,
    TIMESTAMP,
    ForeignKey,
    UniqueConstraint,
    Index,
    text
)
from sqlalchemy.dialects.mysql import BIGINT, CHAR
from sqlalchemy.orm import mapped_column

from app.database.connection import Base


class CaseClosure(Base):
    __tablename__ = "case_closures"
    __table_args__ = ()

    closure_id = mapped_column(
        BIGINT(unsigned=True),
        primary_key=True,
        autoincrement=True
    )

    public_id = mapped_column(
        CHAR(36),
        nullable=False,
        unique=True
    )

    case_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("care_cases.case_id"),
        nullable=False,
        unique=True
    )

    closure_type = mapped_column(
        Enum(
            "CARE_COMPLETED",
            "TRANSFERRED",
            "PATIENT_DECLINED",
            "UNABLE_TO_CONTACT",
            "DUPLICATE_CASE",
            "NOT_CLINICALLY_INDICATED",
            "OTHER_AUTHORISED"
        ),
        nullable=False
    )

    closure_reason = mapped_column(
        Text,
        nullable=False
    )

    evidence_summary = mapped_column(
        Text,
        nullable=True
    )

    authorised_by = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("facility_users.facility_user_id"),
        nullable=False
    )

    authorised_at = mapped_column(
        DateTime,
        nullable=True,
        server_default=text("CURRENT_TIMESTAMP")
    )

    created_at = mapped_column(
        TIMESTAMP,
        nullable=True,
        server_default=text("CURRENT_TIMESTAMP")
    )