
from sqlalchemy.orm import Session

from app.models.facility_user import FacilityUser
from app.models.role import Role
from app.models.permission import Permission
from app.models.role_permission import RolePermission


def user_has_permission(
    db: Session,
    user_id: int,
    facility_id: int,
    permission_name: str
) -> bool:

    permission = (
        db.query(Permission)
        .join(
            RolePermission,
            Permission.permission_id == RolePermission.permission_id
        )
        .join(
            Role,
            Role.role_id == RolePermission.role_id
        )
        .join(
            FacilityUser,
            FacilityUser.role_id == Role.role_id
        )
        .filter(
            FacilityUser.user_id == user_id,
            FacilityUser.facility_id == facility_id,
            FacilityUser.employment_status == "ACTIVE",
            Permission.permission_name == permission_name
        )
        .first()
    )

    return permission is not None
