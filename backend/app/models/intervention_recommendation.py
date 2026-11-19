from sqlalchemy import (
    String,
    Text,
    Enum,
    DateTime,
    TIMESTAMP,
    ForeignKey,
    Index,
    text
)
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import mapped_column

from app.database.connection import Base


class InterventionRecommendation(Base):
    __tablename__ = "intervention_recommendations"
    __table_args__ = (
        Index("idx_intervention_case", "case_id"),
        Index("idx_intervention_status", "recommendation_status"),
    )

    recommendation_id = mapped_column(
        BIGINT(unsigned=True),
        primary_key=True,
        autoincrement=True
    )

    case_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("care_cases.case_id"),
        nullable=False
    )

    assessment_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("risk_assessments.assessment_id"),
        nullable=True
    )

    recommendation_type = mapped_column(
        String(100),
        nullable=False
    )

    recommendation = mapped_column(
        Text,
        nullable=False
    )

    recommendation_status = mapped_column(
        Enum(
            "PENDING_REVIEW",
            "APPROVED",
            "REJECTED",
            "IMPLEMENTED",
            "CANCELLED"
        ),
        nullable=True,
        server_default=text("'PENDING_REVIEW'")
    )

    reviewed_by = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("facility_users.facility_user_id"),
        nullable=True
    )

    reviewed_at = mapped_column(
        DateTime,
        nullable=True
    )

    created_at = mapped_column(
        TIMESTAMP,
        nullable=True,
        server_default=text("CURRENT_TIMESTAMP")
    )


    executed_by = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("facility_users.facility_user_id"),
        nullable=True
    )

    executed_at = mapped_column(
        DateTime,
        nullable=True
    )

    execution_notes = mapped_column(
        Text,
        nullable=True
    )