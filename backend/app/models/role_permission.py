from sqlalchemy import ForeignKey
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import mapped_column

from app.database.connection import Base


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("roles.role_id"),
        primary_key=True
    )

    permission_id = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("permissions.permission_id"),
        primary_key=True
    )