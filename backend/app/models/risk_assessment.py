from sqlalchemy import (
    String,
    Enum,
    JSON,
    DateTime,
    ForeignKey,
    Numeric,
    Index,
    text
)
from sqlalchemy.dialects.mysql import BIGINT, CHAR
from sqlalchemy.orm import mapped_column

from app.database.connection import Base


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"
    __table_args__ = (
        Index("idx_risk_assessment_case", "case_id"),
        Index("idx_risk_assessment_level", "risk_level"),
    )

    assessment_id = mapped_column(
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
        nullable=False
    )

    model_name = mapped_column(
        String(100),
        nullable=False
    )

    model_version = mapped_column(
        String(50),
        nullable=False
    )

    risk_score = mapped_column(
        Numeric(6, 5),
        nullable=False
    )

    risk_level = mapped_column(
        Enum("LOW", "MODERATE", "HIGH", "CRITICAL"),
        nullable=False
    )

    contributing_factors = mapped_column(
        JSON,
        nullable=True
    )

    feature_snapshot = mapped_column(
        JSON,
        nullable=True
    )

    assessed_at = mapped_column(
        DateTime,
        nullable=True,
        server_default=text("CURRENT_TIMESTAMP")
    )