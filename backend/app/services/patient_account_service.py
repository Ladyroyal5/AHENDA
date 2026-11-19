
from datetime import datetime
from uuid import uuid4
import secrets
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.patient import PatientUserAccount, Patient
from app.models.user import User, AccountType
from app.models.facility_user import FacilityUser
from app.models.patient_facility_relationship import (
    PatientFacilityRelationship
)
from app.services.permission_service import user_has_permission
from app.services.audit_service import record_audit_event
from app.services.patient_activation_service import (
    create_activation_token
)
from app.core.security import hash_password
from app.models.patient_activation_token import PatientActivationToken



def get_authorised_staff_membership(
    db: Session,
    actor_user_id: int,
    facility_user_id: int
):
    """Verify staff ownership, active membership and permission."""

    membership = db.query(FacilityUser).filter(
        FacilityUser.facility_user_id == facility_user_id,
        FacilityUser.user_id == actor_user_id,
        FacilityUser.employment_status == "ACTIVE"
    ).first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have an active membership for this facility."
        )

    authorised = user_has_permission(
        db=db,
        user_id=actor_user_id,
        facility_id=membership.facility_id,
        permission_name="MANAGE_PATIENT_ACCOUNTS"
    )

    if not authorised:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorised to manage patient accounts."
        )

    return membership


def ensure_patient_facility_access(
    db: Session,
    patient_id: int,
    facility_id: int
):
    """Ensure the patient has an active relationship with the facility."""

    relationship = db.query(PatientFacilityRelationship).filter(
        PatientFacilityRelationship.patient_id == patient_id,
        PatientFacilityRelationship.facility_id == facility_id,
        PatientFacilityRelationship.relationship_status == "ACTIVE"
    ).first()

    if not relationship:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This patient does not have an active relationship with your facility."
        )

    return relationship


def create_patient_account_link(
    db: Session,
    user_id: int,
    patient_id: int,
    facility_user_id: int,
    actor_user_id: int
):
    # 1. Verify the authenticated staff member and membership.
    staff_membership = get_authorised_staff_membership(
        db=db,
        actor_user_id=actor_user_id,
        facility_user_id=facility_user_id
    )

    # 2. Confirm that the patient exists and is active.
    patient = db.query(Patient).filter(
        Patient.patient_id == patient_id,
        Patient.is_active.is_(True)
    ).first()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active patient record not found."
        )

    # 3. Confirm that the patient belongs to this facility.
    ensure_patient_facility_access(
        db=db,
        patient_id=patient_id,
        facility_id=staff_membership.facility_id
    )

    # 4. Confirm that the user exists and is active.
    user = db.query(User).filter(
        User.user_id == user_id,
        User.is_active.is_(True)
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active user account not found."
        )

    # 5. Only PATIENT accounts can be linked.
    if user.account_type != AccountType.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only PATIENT accounts can be linked to patient records."
        )

    # 6. Prevent duplicate account links.
    existing_link = db.query(PatientUserAccount).filter(
        (PatientUserAccount.user_id == user_id) |
        (PatientUserAccount.patient_id == patient_id)
    ).first()

    if existing_link:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This user or patient already has an account link."
        )

    try:
        account_link = PatientUserAccount(
            user_id=user_id,
            patient_id=patient_id,
            account_status="PENDING",
            created_by=facility_user_id
        )

        db.add(account_link)
        db.flush()

        record_audit_event(
            db=db,
            actor_user_id=actor_user_id,
            facility_id=staff_membership.facility_id,
            action="PATIENT_ACCOUNT_LINK_CREATED",
            entity_type="PATIENT_USER_ACCOUNT",
            entity_id=str(account_link.account_link_id),
            new_values={
                "user_id": user_id,
                "patient_id": patient_id,
                "account_status": "PENDING"
            }
        )

        db.commit()
        db.refresh(account_link)

        return account_link

    except Exception:
        db.rollback()
        raise



def verify_patient_account_link(
    db: Session,
    account_link_id: int,
    facility_user_id: int,
    actor_user_id: int
):
    staff_membership = get_authorised_staff_membership(
        db=db,
        actor_user_id=actor_user_id,
        facility_user_id=facility_user_id
    )

    try:
        # 1. Retrieve and lock the account link.
        account_link = db.query(PatientUserAccount).filter(
            PatientUserAccount.account_link_id == account_link_id
        ).with_for_update().first()

        if not account_link:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient account link not found."
            )

        # 2. Confirm facility access.
        ensure_patient_facility_access(
            db=db,
            patient_id=account_link.patient_id,
            facility_id=staff_membership.facility_id
        )

        # 3. Only pending links can be verified.
        if account_link.account_status != "PENDING":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only pending account links can be verified."
            )

        # 4. Retrieve the patient user.
        user = db.query(User).filter(
            User.user_id == account_link.user_id
        ).with_for_update().first()

        if not user or user.account_type != AccountType.PATIENT:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A valid patient user account was not found."
            )

        if user.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Patient account is already active."
            )

        # 5. Confirm password setup was completed.
        password_setup_completed = db.query(
            PatientActivationToken
        ).filter(
            PatientActivationToken.user_id == user.user_id,
            PatientActivationToken.used_at.isnot(None)
        ).first()

        if not password_setup_completed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Patient must complete password setup before verification."
            )

        # 6. Verify the link and activate the user.
        old_status = account_link.account_status

        account_link.account_status = "VERIFIED"
        account_link.verified_by = facility_user_id
        account_link.verified_at = datetime.utcnow()

        user.is_active = True

        # 7. Record the audit event.
        record_audit_event(
            db=db,
            actor_user_id=actor_user_id,
            facility_id=staff_membership.facility_id,
            action="PATIENT_ACCOUNT_LINK_VERIFIED",
            entity_type="PATIENT_USER_ACCOUNT",
            entity_id=str(account_link.account_link_id),
            old_values={
                "account_status": old_status,
                "user_is_active": False
            },
            new_values={
                "account_status": "VERIFIED",
                "user_is_active": True
            }
        )

        db.commit()
        db.refresh(account_link)

        return account_link

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise



def suspend_patient_account_link(
    db: Session,
    account_link_id: int,
    facility_user_id: int,
    actor_user_id: int
):
    # 1. Verify the authenticated staff member.
    staff_membership = get_authorised_staff_membership(
        db=db,
        actor_user_id=actor_user_id,
        facility_user_id=facility_user_id
    )

    try:
        # 2. Retrieve and lock the account link.
        account_link = db.query(PatientUserAccount).filter(
            PatientUserAccount.account_link_id == account_link_id
        ).with_for_update().first()

        if not account_link:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient account link not found."
            )

        # 3. Confirm facility access to the patient.
        ensure_patient_facility_access(
            db=db,
            patient_id=account_link.patient_id,
            facility_id=staff_membership.facility_id
        )

        if account_link.account_status == "SUSPENDED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This patient account is already suspended."
            )

        old_status = account_link.account_status

        account_link.account_status = "SUSPENDED"

        record_audit_event(
            db=db,
            actor_user_id=actor_user_id,
            facility_id=staff_membership.facility_id,
            action="PATIENT_ACCOUNT_LINK_SUSPENDED",
            entity_type="PATIENT_USER_ACCOUNT",
            entity_id=str(account_link.account_link_id),
            old_values={"account_status": old_status},
            new_values={"account_status": "SUSPENDED"}
        )

        db.commit()
        db.refresh(account_link)

        return account_link

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise


def create_patient_onboarding_account(
    db: Session,
    patient_id: int,
    facility_user_id: int,
    actor_user_id: int
):
    """Create a pending patient login and activation token."""

    staff_membership = get_authorised_staff_membership(
        db=db,
        actor_user_id=actor_user_id,
        facility_user_id=facility_user_id
    )

    try:
        # 1. Find the active patient.
        patient = db.query(Patient).filter(
            Patient.patient_id == patient_id,
            Patient.is_active.is_(True)
        ).with_for_update().first()

        if not patient:
            raise HTTPException(
                status_code=404,
                detail="Active patient record not found."
            )

        # 2. Confirm the patient's facility relationship.
        ensure_patient_facility_access(
            db=db,
            patient_id=patient_id,
            facility_id=staff_membership.facility_id
        )

        # 3. Require a registered email.
        if not patient.email or not patient.email.strip():
            raise HTTPException(
                status_code=400,
                detail="The patient has no registered email address."
            )

        email = patient.email.strip().lower()

        # 4. Prevent duplicate patient account links.
        existing_link = db.query(PatientUserAccount).filter(
            PatientUserAccount.patient_id == patient_id
        ).first()

        if existing_link:
            raise HTTPException(
                status_code=409,
                detail="This patient already has an account link."
            )

        # 5. Prevent an existing email account from being reused.
        existing_user = db.query(User).filter(
            User.email == email
        ).first()

        if existing_user:
            raise HTTPException(
                status_code=409,
                detail="An account already exists for this email."
            )

        # 6. Generate an unusable temporary password.
        temporary_password = secrets.token_urlsafe(48)

        user = User(
            public_id=str(uuid4()),
            first_name=patient.first_name,
            last_name=patient.last_name,
            email=email,
            phone_number=patient.phone_number,
            password_hash=hash_password(temporary_password),
            account_type=AccountType.PATIENT,
            is_active=False
        )

        db.add(user)
        db.flush()

        # 7. Create the pending patient-account link.
        account_link = PatientUserAccount(
            user_id=user.user_id,
            patient_id=patient_id,
            account_status="PENDING",
            created_by=facility_user_id
        )

        db.add(account_link)
        db.flush()

        # 8. Generate and store the activation-token hash.
        raw_token = create_activation_token(
            db=db,
            user_id=user.user_id
        )

        # 9. Record the operation.
        record_audit_event(
            db=db,
            actor_user_id=actor_user_id,
            facility_id=staff_membership.facility_id,
            action="PATIENT_ONBOARDING_ACCOUNT_CREATED",
            entity_type="PATIENT_USER_ACCOUNT",
            entity_id=str(account_link.account_link_id),
            new_values={
                "user_id": user.user_id,
                "patient_id": patient_id,
                "account_type": "PATIENT",
                "account_status": "PENDING",
                "is_active": False
            }
        )

        db.commit()

        return {
            "user_id": user.user_id,
            "account_link_id": account_link.account_link_id,
            "patient_id": patient_id,
            "account_status": account_link.account_status,
            "activation_token": raw_token
        }

    except Exception:
        db.rollback()
        raise

