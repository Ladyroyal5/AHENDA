
from fastapi import Depends, HTTPException, status
from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials
)
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.user import User, AccountType
from app.models.patient import PatientUserAccount
from app.core.security import decode_access_token
from app.services.permission_service import user_has_permission


bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> User:

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate authentication credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )

    try:
        token = credentials.credentials
        payload = decode_access_token(token)
        user_id = int(payload.get("sub"))

        if user_id <= 0:
            raise credentials_exception

    except Exception:
        raise credentials_exception

    user = db.query(User).filter(
        User.user_id == user_id
    ).first()

    if user is None or not user.is_active:
        raise credentials_exception

    # Patient accounts must have a verified account link.
    if user.account_type == AccountType.PATIENT:

        verified_link = db.query(PatientUserAccount).filter(
            PatientUserAccount.user_id == user.user_id,
            PatientUserAccount.account_status == "VERIFIED"
        ).first()

        if not verified_link:
            raise credentials_exception

    return user


def require_permission(permission_name: str):
    def permission_checker(
        facility_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ):
        allowed = user_has_permission(
            db=db,
            user_id=current_user.user_id,
            facility_id=facility_id,
            permission_name=permission_name
        )

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action."
            )

        return current_user

    return permission_checker
