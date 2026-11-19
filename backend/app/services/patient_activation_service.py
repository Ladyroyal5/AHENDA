from fastapi import HTTPException, status
from app.models.user import User, AccountType
from app.models.patient import PatientUserAccount
from app.core.security import hash_password
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.models.patient_activation_token import PatientActivationToken


ACTIVATION_TOKEN_EXPIRY_HOURS = 24


def generate_activation_token():
    """Generate a cryptographically secure activation token."""
    raw_token = secrets.token_urlsafe(32)

    token_hash = hashlib.sha256(
        raw_token.encode("utf-8")
    ).hexdigest()

    return raw_token, token_hash


def create_activation_token(
    db: Session,
    user_id: int
):
    """Create a new activation token and revoke previous unused tokens."""

    now = datetime.now(timezone.utc)

    # Revoke existing unused activation tokens.
    db.query(PatientActivationToken).filter(
        PatientActivationToken.user_id == user_id,
        PatientActivationToken.used_at.is_(None),
        PatientActivationToken.revoked_at.is_(None)
    ).update(
        {"revoked_at": now.replace(tzinfo=None)},
        synchronize_session=False
    )

    raw_token, token_hash = generate_activation_token()

    activation_record = PatientActivationToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=(
            now + timedelta(hours=ACTIVATION_TOKEN_EXPIRY_HOURS)
        ).replace(tzinfo=None)
    )

    db.add(activation_record)
    db.flush()

    return raw_token


def validate_activation_token(
    db: Session,
    raw_token: str
):
    """Validate an activation token without consuming it."""

    token_hash = hashlib.sha256(
        raw_token.encode("utf-8")
    ).hexdigest()

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    activation_record = db.query(
        PatientActivationToken
    ).filter(
        PatientActivationToken.token_hash == token_hash,
        PatientActivationToken.used_at.is_(None),
        PatientActivationToken.revoked_at.is_(None),
        PatientActivationToken.expires_at > now
    ).first()

    return activation_record


def complete_patient_activation(
    db: Session,
    raw_token: str,
    new_password: str
):
    """Allow a patient to set their password using a valid token."""

    if len(new_password) < 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least 12 characters."
        )

    token_hash = hashlib.sha256(
        raw_token.encode("utf-8")
    ).hexdigest()

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    try:
        # Lock the token to prevent simultaneous reuse.
        activation_record = db.query(
            PatientActivationToken
        ).filter(
            PatientActivationToken.token_hash == token_hash
        ).with_for_update().first()

        if (
            not activation_record
            or activation_record.used_at is not None
            or activation_record.revoked_at is not None
            or activation_record.expires_at <= now
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Activation link is invalid or expired."
            )

        # Lock and retrieve the associated user.
        user = db.query(User).filter(
            User.user_id == activation_record.user_id
        ).with_for_update().first()

        if (
            not user
            or user.account_type != AccountType.PATIENT
            or user.is_active
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Patient account cannot be activated."
            )

        # Confirm that the patient account link is still pending.
        account_link = db.query(PatientUserAccount).filter(
            PatientUserAccount.user_id == user.user_id,
            PatientUserAccount.account_status == "PENDING"
        ).with_for_update().first()

        if not account_link:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pending patient account link not found."
            )

        # Save the patient's chosen password.
        user.password_hash = hash_password(new_password)

        # Consume the activation token.
        activation_record.used_at = now

        # Do not activate the user yet.
        db.commit()

        return {
            "message": "Password setup completed. Your identity must still be verified before you can sign in."
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise

