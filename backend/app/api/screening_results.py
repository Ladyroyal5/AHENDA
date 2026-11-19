import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.database.connection import get_db
from app.models.patient import Patient
from app.models.screening_programme import ScreeningProgramme
from app.models.screening_result import ScreeningResult
from app.models.user import User

from app.schemas.screening_result import (
    ScreeningResultCreate,
    ScreeningResultResponse,
    ScreeningResultReview
)

from app.core.dependencies import (
    require_permission
)

from app.services.patient_access_service import patient_has_facility_relationship
from datetime import datetime, timezone
from app.services.audit_service import record_audit_event
from app.services.care_case_service import create_care_case_workflow


router = APIRouter(
    prefix="/api/v1/screening-results",
    tags=["Screening Results"]
)


@router.post(
    "/",
    response_model=ScreeningResultResponse,
    status_code=status.HTTP_201_CREATED
)
def submit_screening_result(
    result_data: ScreeningResultCreate,
    facility_id: int,
    current_user: User = Depends(
        require_permission("UPLOAD_SCREENING_RESULTS")
    ),
    db: Session = Depends(get_db)
):

    # 1. Find the patient using their public ID.
    patient = db.query(Patient).filter(
        Patient.public_id == result_data.patient_public_id,
        Patient.is_active.is_(True)
    ).first()

    if not patient:
        raise HTTPException(
            status_code=404,
            detail="Active patient not found."
        )
    # Verify that the patient has an active relationship
    # with the submitting facility.
    if not patient_has_facility_relationship(
        db=db,
        patient_id=patient.patient_id,
        facility_id=facility_id
    ):
        raise HTTPException(
            status_code=403,
            detail="This patient has no active relationship with your facility."
        )
    

    # 2. Check whether the programme exists and is active.
    programme = db.query(ScreeningProgramme).filter(
        ScreeningProgramme.programme_id == result_data.programme_id,
        ScreeningProgramme.is_active.is_(True)
    ).first()

    if not programme:
        raise HTTPException(
            status_code=404,
            detail="Active screening programme not found."
        )

    # 3. Check for an existing external result reference.
    if result_data.external_result_reference:
        existing_result = db.query(ScreeningResult).filter(
            ScreeningResult.facility_id == facility_id,
            ScreeningResult.external_result_reference
            == result_data.external_result_reference
        ).first()

        if existing_result:
            raise HTTPException(
                status_code=409,
                detail="This external result reference already exists."
            )

    # 4. Create the screening result.
    screening_result = ScreeningResult(
        public_id=str(uuid.uuid4()),
        patient_id=patient.patient_id,
        facility_id=facility_id,
        programme_id=programme.programme_id,
        submitted_by=current_user.user_id,
        external_result_reference=result_data.external_result_reference,
        test_name=result_data.test_name,
        result_value=result_data.result_value,
        result_unit=result_data.result_unit,
        reference_range=result_data.reference_range,
        result_classification=result_data.result_classification,
        review_status="PENDING",
        actionability_status="PENDING",
        clinical_urgency=None,
        issued_at=result_data.issued_at
    )

    try:
        db.add(screening_result)
        db.commit()
        db.refresh(screening_result)

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="The screening result could not be saved because of a database conflict."
        )

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="A database error occurred while saving the screening result."
        )

    return screening_result

@router.patch(
    "/{result_id}/review",
    response_model=ScreeningResultResponse
)
def review_screening_result(
    result_id: int,
    review_data: ScreeningResultReview,
    facility_id: int,
    current_user: User = Depends(
        require_permission("REVIEW_SCREENING_RESULTS")
    ),
    db: Session = Depends(get_db)
):

    # 1. Find the screening result belonging to this facility.
    screening_result = (
        db.query(ScreeningResult)
        .filter(
            ScreeningResult.result_id == result_id,
            ScreeningResult.facility_id == facility_id
        )
        .with_for_update()
        .first()
    )

    if not screening_result:
        raise HTTPException(
            status_code=404,
            detail="Screening result not found."
        )

    # 2. Only pending results can be reviewed.
    if screening_result.review_status != "PENDING":
        raise HTTPException(
            status_code=409,
            detail="This screening result is not pending review."
        )

    # 3. An actionable result must have a clinical urgency.
    if (
        review_data.actionability_status == "ACTIONABLE"
        and review_data.clinical_urgency is None
    ):
        raise HTTPException(
            status_code=422,
            detail="Clinical urgency is required for actionable results."
        )

    # 4. Non-actionable results should not have a clinical urgency.
    if (
        review_data.actionability_status == "NOT_ACTIONABLE"
        and review_data.clinical_urgency is not None
    ):
        raise HTTPException(
            status_code=422,
            detail="Non-actionable results cannot have a clinical urgency."
        )

    if (
        review_data.actionability_status == "NEEDS_REVIEW"
        and review_data.clinical_urgency is not None
    ):
        raise HTTPException(
            status_code=422,
            detail="Results needing further review cannot have a clinical urgency assigned yet."
        )
    

    # 5. Record the clinical review.
    old_values = {
        "review_status": screening_result.review_status,
        "actionability_status": screening_result.actionability_status,
        "clinical_urgency": screening_result.clinical_urgency,
        "reviewed_by": screening_result.reviewed_by
    }

    screening_result.review_status = "REVIEWED"
    screening_result.actionability_status = review_data.actionability_status
    screening_result.clinical_urgency = review_data.clinical_urgency
    screening_result.reviewed_by = current_user.user_id
    screening_result.reviewed_at = datetime.now(timezone.utc).replace(tzinfo=None)

    new_values = {
        "review_status": screening_result.review_status,
        "actionability_status": screening_result.actionability_status,
        "clinical_urgency": screening_result.clinical_urgency,
        "reviewed_by": screening_result.reviewed_by
    }

    record_audit_event(
        db=db,
        actor_user_id=current_user.user_id,
        facility_id=facility_id,
        action="SCREENING_RESULT_REVIEWED",
        entity_type="SCREENING_RESULT",
        entity_id=screening_result.result_id,
        old_values=old_values,
        new_values=new_values
    )

    try:
    # Create a care case only when the result is actionable.
        if screening_result.actionability_status == "ACTIONABLE":
            create_care_case_workflow(
                db=db,
                screening_result=screening_result,
                reviewed_by=current_user.user_id
            )

        # Save all related records together.
        db.commit()
        db.refresh(screening_result)

    except ValueError as error:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=str(error)
        )

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="The clinical review or care-case creation could not be saved because of a database conflict."
        )

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="A database error occurred while saving the clinical review and care workflow."
        )

    return screening_result
