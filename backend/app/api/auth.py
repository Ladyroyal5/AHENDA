
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.user import User, AccountType
from app.models.patient import PatientUserAccount
from app.core.security import (
    verify_password,
    create_access_token
)
from app.services.patient_activation_service import (
    complete_patient_activation
)


router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"]
)


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=1, max_length=128)

class PatientActivationRequest(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    new_password: str = Field(min_length=12, max_length=128)


@router.post("/login")
def login(
    credentials: LoginRequest,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.email == credentials.email.strip().lower()
    ).first()

    # Use the same response for invalid credentials
    # and inactive accounts.
    if (
        not user
        or not user.is_active
        or not verify_password(
            credentials.password,
            user.password_hash
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Patient accounts must have a verified account link.
    if user.account_type == AccountType.PATIENT:

        verified_link = db.query(PatientUserAccount).filter(
            PatientUserAccount.user_id == user.user_id,
            PatientUserAccount.account_status == "VERIFIED"
        ).first()

        if not verified_link:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"}
            )

    user.last_login = datetime.now(timezone.utc).replace(
        tzinfo=None
    )

    db.commit()

    access_token = create_access_token(user.user_id)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "public_id": user.public_id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "account_type": user.account_type.value
        }
    }

@router.post("/activate-patient")
def activate_patient(
    request: PatientActivationRequest,
    db: Session = Depends(get_db)
):
    result = complete_patient_activation(
        db=db,
        raw_token=request.token,
        new_password=request.new_password
    )

    return result
