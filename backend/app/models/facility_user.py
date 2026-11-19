
from sqlalchemy import (
    String,
    TIMESTAMP,
    ForeignKey,
    UniqueConstraint,
    Index,
    text
)

from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import mapped_column

from app.database.connection import Base


class FacilityUser(Base):
    __tablename__ = "facility_users"

    __table_args__ = (
        UniqueConstraint(
            "facility_id",
            "user_id",
            "role_id",
            name="uq_facility_user_role"
        ),
        Index("idx_facility_users_facility", "facility_id"),
        Index("idx_facility_users_user", "user_id"),
    )

    facility_user_id = mapped_column(
        BIGINT(unsigned=True),
        primary_key=True,
        autoincrement=True
    )

    facility_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("facilities.facility_id"),
        nullable=False
    )

    user_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("users.user_id"),
        nullable=False
    )

    role_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("roles.role_id"),
        nullable=False
    )

    employment_status = mapped_column(
        String(30),
        nullable=True,
        server_default=text("'ACTIVE'")
    )

    joined_at = mapped_column(
        TIMESTAMP,
        nullable=True,
        server_default=text("CURRENT_TIMESTAMP")
    )
