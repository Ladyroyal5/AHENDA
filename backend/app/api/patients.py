
import os
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.database.connection import get_db

from app.models.patient import Patient
from app.models.patient_facility_relationship import PatientFacilityRelationship
from app.models.identity_review import IdentityReviewCase
from app.models.facility_user import FacilityUser

from app.schemas.patient import (
    PatientCreate,
    PatientResponse,
    PatientIdentifierCreate
)

from app.core.dependencies import (
    get_current_user,
    require_permission
)

from app.services.identity_service import register_identifier
from app.services.patient_access_service import user_can_access_patient
from app.services.patient_account_service import (
    create_patient_account_link,
    create_patient_onboarding_account,
    verify_patient_account_link
)

router = APIRouter(
    prefix="/api/v1/patients",
    tags=["Patients"]
)

# REQUEST SCHEMAS

class PatientAccountLinkCreate(BaseModel):
    user_id: int = Field(gt=0)
    patient_id: int = Field(gt=0)


class PatientOnboardingCreate(BaseModel):
    patient_id: int = Field(gt=0)


# PATIENT REGISTRATION

@router.post(
    "/",
    response_model=PatientResponse,
    status_code=status.HTTP_201_CREATED
)
def register_patient(
    patient_data: PatientCreate,
    facility_id: int,
    current_user=Depends(require_permission("REGISTER_PATIENTS")),
    db: Session = Depends(get_db)
):

    new_patient = Patient(
        public_id=str(uuid4()),
        first_name=patient_data.first_name.strip(),
        last_name=patient_data.last_name.strip(),
        middle_name=patient_data.middle_name,
        date_of_birth=patient_data.date_of_birth,
        sex=patient_data.sex,
        phone_number=patient_data.phone_number,
        email=patient_data.email,
        preferred_language=patient_data.preferred_language
    )

    try:
        db.add(new_patient)

        db.flush()

        patient_relationship = PatientFacilityRelationship(
            patient_id=new_patient.patient_id,
            facility_id=facility_id,
            relationship_type="REGISTRATION",
            relationship_status="ACTIVE",
            established_by=current_user.user_id
        )

        db.add(patient_relationship)

        db.commit()
        db.refresh(new_patient)

        return new_patient

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Patient registration could not be completed."
        )

# RETRIEVE PATIENT

@router.get(
    "/{public_id}",
    response_model=PatientResponse
)
def get_patient(
    public_id: str,
    facility_id: int,
    current_user=Depends(require_permission("VIEW_PATIENTS")),
    db: Session = Depends(get_db)
):

    patient = db.query(Patient).filter(
        Patient.public_id == public_id,
        Patient.is_active.is_(True)
    ).first()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active patient not found."
        )

    allowed = user_can_access_patient(
        db=db,
        user_id=current_user.user_id,
        patient_id=patient.patient_id,
        facility_id=facility_id
    )

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorised to access this patient's record."
        )

    return patient

# REGISTER PATIENT IDENTIFIER

@router.post("/{public_id}/identifiers")
def add_patient_identifier(
    public_id: str,
    identifier_data: PatientIdentifierCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    patient = db.query(Patient).filter(
        Patient.public_id == public_id,
        Patient.is_active.is_(True)
    ).first()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active patient not found."
        )

    try:
        result = register_identifier(
            db=db,
            patient_id=patient.patient_id,
            identifier_type=identifier_data.identifier_type,
            identifier_value=identifier_data.identifier_value,
            facility_id=identifier_data.facility_id
        )

        if result["status"] == "review_required":
            db.commit()
            return result

        if result["status"] == "already_registered":
            db.rollback()
            return result

        db.commit()
        return result

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Identifier could not be registered because of a database conflict."
        )

# PENDING IDENTITY REVIEWS

@router.get("/identity-reviews/pending")
def get_pending_identity_reviews(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    reviews = db.query(IdentityReviewCase).filter(
        IdentityReviewCase.review_status == "PENDING"
    ).order_by(
        IdentityReviewCase.created_at.desc()
    ).all()

    return {
        "total": len(reviews),
        "reviews": [
            {
                "review_id": review.review_id,
                "patient_id": review.patient_id,
                "matched_patient_id": review.matched_patient_id,
                "identifier_type": review.identifier_type,
                "review_status": review.review_status,
                "created_at": review.created_at
            }
            for review in reviews
        ]
    }


# LINK AN EXISTING PATIENT USER ACCOUNT

@router.post(
    "/accounts/link",
    status_code=status.HTTP_201_CREATED
)
def link_patient_account(
    account_data: PatientAccountLinkCreate,
    facility_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    membership = db.query(FacilityUser).filter(
        FacilityUser.user_id == current_user.user_id,
        FacilityUser.facility_id == facility_id,
        FacilityUser.employment_status == "ACTIVE"
    ).first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have an active membership at this facility."
        )

    try:
        account_link = create_patient_account_link(
            db=db,
            user_id=account_data.user_id,
            patient_id=account_data.patient_id,
            facility_user_id=membership.facility_user_id,
            actor_user_id=current_user.user_id
        )

        return {
            "message": "Patient account link created successfully.",
            "account_link_id": account_link.account_link_id,
            "user_id": account_link.user_id,
            "patient_id": account_link.patient_id,
            "account_status": account_link.account_status
        }

    except HTTPException:
        raise

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while linking the patient account."
        )

# CREATE PATIENT ONBOARDING ACCOUNT

@router.post(
    "/accounts/onboard",
    status_code=status.HTTP_201_CREATED
)
def onboard_patient_account(
    account_data: PatientOnboardingCreate,
    facility_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    # Activation-token delivery is currently development-only.
    if os.getenv("APP_ENV", "development").lower() != "development":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Patient activation email delivery is not configured."
        )

    # Find the authenticated staff member's active facility membership.
    membership = db.query(FacilityUser).filter(
        FacilityUser.user_id == current_user.user_id,
        FacilityUser.facility_id == facility_id,
        FacilityUser.employment_status == "ACTIVE"
    ).first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have an active membership at this facility."
        )

    try:
        result = create_patient_onboarding_account(
            db=db,
            patient_id=account_data.patient_id,
            facility_user_id=membership.facility_user_id,
            actor_user_id=current_user.user_id
        )

        return {
            "message": "Patient onboarding account created successfully.",
            "patient_id": result["patient_id"],
            "user_id": result["user_id"],
            "account_link_id": result["account_link_id"],
            "account_status": result["account_status"],
            "activation_token": result["activation_token"],
            "activation_endpoint": "/api/v1/auth/activate-patient"
        }

    except HTTPException:
        raise

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred during patient onboarding."
        )

# VERIFY PATIENT ACCOUNT

@router.post(
    "/accounts/{account_link_id}/verify",
    status_code=status.HTTP_200_OK
)
def verify_patient_account(
    account_link_id: int,
    facility_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Find the authenticated staff member's active facility membership.
    membership = db.query(FacilityUser).filter(
        FacilityUser.user_id == current_user.user_id,
        FacilityUser.facility_id == facility_id,
        FacilityUser.employment_status == "ACTIVE"
    ).first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have an active membership at this facility."
        )

    try:
        verify_patient_account_link(
            db=db,
            account_link_id=account_link_id,
            facility_user_id=membership.facility_user_id,
            actor_user_id=current_user.user_id
        )

        return {
            "message": "Patient account verified successfully.",
            "account_link_id": account_link_id,
            "account_status": "VERIFIED"
        }

    except HTTPException:
        raise

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while verifying the patient account."
        )
