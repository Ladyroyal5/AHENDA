
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.database.connection import get_db
from app.models.clinical_outcome import ClinicalOutcome
from app.models.care_case import CareCase
from app.models.referral import Referral
from app.models.facility_user import FacilityUser
from app.models.user import User
from app.models.role import Role
from app.models.task import Task
from app.schemas.clinical_outcome import (
    ClinicalOutcomeCreate,
    ClinicalOutcomeReview
)
from app.schemas.task import ClinicalOutcomeFollowUpTask
from app.core.dependencies import require_permission
from app.services.audit_service import record_audit_event


router = APIRouter(
    prefix="/api/v1/clinical-outcomes",
    tags=["Clinical Outcomes"]
)


@router.post("/", status_code=201)
def record_clinical_outcome(
    outcome_data: ClinicalOutcomeCreate,
    facility_id: int,
    current_user: User = Depends(
        require_permission("RECORD_CLINICAL_OUTCOMES")
    ),
    db: Session = Depends(get_db)
):
    try:
        # 1. Find the care case.
        care_case = db.query(CareCase).filter(
            CareCase.case_id == outcome_data.case_id
        ).first()

        if not care_case:
            raise HTTPException(
                status_code=404,
                detail="Care case not found."
            )

        # 2. Confirm the user has an active membership
        # at the selected facility.
        membership = db.query(FacilityUser).filter(
            FacilityUser.user_id == current_user.user_id,
            FacilityUser.facility_id == facility_id,
            FacilityUser.employment_status == "ACTIVE"
        ).first()

        if not membership:
            raise HTTPException(
                status_code=403,
                detail="You do not have active membership at this facility."
            )

        # 3. Confirm that the facility is authorised
        # to record an outcome for this case.
        is_coordinating_facility = (
            care_case.coordinating_facility_id == facility_id
        )

        has_accepted_referral = db.query(Referral).filter(
            Referral.case_id == care_case.case_id,
            Referral.receiving_facility_id == facility_id,
            Referral.referral_status == "ACCEPTED"
        ).first()

        if not is_coordinating_facility and not has_accepted_referral:
            raise HTTPException(
                status_code=403,
                detail="This facility is not authorised to record an outcome for this case."
            )

        # 4. Create the clinical outcome.
        clinical_outcome = ClinicalOutcome(
            public_id=str(uuid.uuid4()),
            case_id=care_case.case_id,
            facility_id=facility_id,
            recorded_by=membership.facility_user_id,
            outcome_type=outcome_data.outcome_type,
            outcome_status=outcome_data.outcome_status,
            outcome_summary=outcome_data.outcome_summary,
            occurred_at=outcome_data.occurred_at,
            follow_up_required=outcome_data.follow_up_required,
            next_follow_up_at=outcome_data.next_follow_up_at
        )

        db.add(clinical_outcome)
        db.flush()

        # 5. Record the audit event.
        record_audit_event(
            db=db,
            actor_user_id=current_user.user_id,
            facility_id=facility_id,
            action="CLINICAL_OUTCOME_RECORDED",
            entity_type="CLINICAL_OUTCOME",
            entity_id=str(clinical_outcome.outcome_id),
            new_values={
                "case_id": clinical_outcome.case_id,
                "facility_id": clinical_outcome.facility_id,
                "outcome_type": clinical_outcome.outcome_type,
                "outcome_status": clinical_outcome.outcome_status,
                "follow_up_required": clinical_outcome.follow_up_required
            }
        )

        # 6. Save the outcome and audit event together.
        db.commit()
        db.refresh(clinical_outcome)

        return {
            "message": "Clinical outcome recorded successfully.",
            "outcome_id": clinical_outcome.outcome_id,
            "case_id": clinical_outcome.case_id,
            "facility_id": clinical_outcome.facility_id,
            "recorded_by": clinical_outcome.recorded_by,
            "outcome_type": clinical_outcome.outcome_type,
            "outcome_status": clinical_outcome.outcome_status,
            "follow_up_required": clinical_outcome.follow_up_required
        }

    except HTTPException:
        db.rollback()
        raise

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="The clinical outcome could not be saved because of a database conflict."
        )

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="A database error occurred while recording the clinical outcome."
        )
    


@router.post("/{outcome_id}/review")
def review_clinical_outcome(
    outcome_id: int,
    review_data: ClinicalOutcomeReview,
    facility_id: int,
    current_user: User = Depends(
        require_permission("REVIEW_CLINICAL_OUTCOMES")
    ),
    db: Session = Depends(get_db)
):
    try:
        # 1. Find and lock the clinical outcome.
        clinical_outcome = (
            db.query(ClinicalOutcome)
            .filter(
                ClinicalOutcome.outcome_id == outcome_id
            )
            .with_for_update()
            .first()
        )

        if not clinical_outcome:
            raise HTTPException(
                status_code=404,
                detail="Clinical outcome not found."
            )

        # 2. Confirm the outcome belongs to this facility.
        if clinical_outcome.facility_id != facility_id:
            raise HTTPException(
                status_code=403,
                detail="This facility is not authorised to review this outcome."
            )

        # 3. Find the reviewer's active facility membership.
        membership = db.query(FacilityUser).filter(
            FacilityUser.user_id == current_user.user_id,
            FacilityUser.facility_id == facility_id,
            FacilityUser.employment_status == "ACTIVE"
        ).first()

        if not membership:
            raise HTTPException(
                status_code=403,
                detail="You do not have active membership at this facility."
            )

        # 4. Prevent an outcome from being reviewed twice.
        if clinical_outcome.review_status != "PENDING":
            raise HTTPException(
                status_code=409,
                detail="This clinical outcome has already been reviewed."
            )

        # 5. Save the clinical review.
        previous_review_status = clinical_outcome.review_status

        clinical_outcome.review_status = review_data.review_status
        clinical_outcome.reviewed_by = membership.facility_user_id
        clinical_outcome.reviewed_at = (
            datetime.now(timezone.utc).replace(tzinfo=None)
        )
        clinical_outcome.review_notes = review_data.review_notes

        db.flush()

        # 6. Record the review in the audit log.
        record_audit_event(
            db=db,
            actor_user_id=current_user.user_id,
            facility_id=facility_id,
            action="CLINICAL_OUTCOME_REVIEWED",
            entity_type="CLINICAL_OUTCOME",
            entity_id=str(clinical_outcome.outcome_id),
            old_values={
                "review_status": previous_review_status
            },
            new_values={
                "review_status": clinical_outcome.review_status,
                "reviewed_by": clinical_outcome.reviewed_by,
                "review_notes": clinical_outcome.review_notes
            }
        )

        # 7. Save the review and audit event together.
        db.commit()
        db.refresh(clinical_outcome)

        return {
            "message": "Clinical outcome reviewed successfully.",
            "outcome_id": clinical_outcome.outcome_id,
            "review_status": clinical_outcome.review_status,
            "reviewed_by": clinical_outcome.reviewed_by,
            "reviewed_at": clinical_outcome.reviewed_at,
            "review_notes": clinical_outcome.review_notes
        }

    except HTTPException:
        db.rollback()
        raise

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="The clinical outcome review could not be saved because of a database conflict."
        )

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="A database error occurred while reviewing the clinical outcome."
        )


@router.get("/cases/{case_id}")
def get_case_clinical_outcomes(
    case_id: int,
    facility_id: int,
    current_user: User = Depends(
        require_permission("MANAGE_CARE_CASES")
    ),
    db: Session = Depends(get_db)
):
    # 1. Confirm this facility coordinates the care case.
    care_case = db.query(CareCase).filter(
        CareCase.case_id == case_id,
        CareCase.coordinating_facility_id == facility_id
    ).first()

    if not care_case:
        raise HTTPException(
            status_code=404,
            detail="Care case not found at this coordinating facility."
        )

    # 2. Retrieve outcomes recorded by all authorised facilities.
    outcomes = (
        db.query(ClinicalOutcome)
        .filter(
            ClinicalOutcome.case_id == case_id
        )
        .order_by(ClinicalOutcome.created_at.desc())
        .all()
    )

    # 3. Return the clinical outcomes and review information.
    return {
        "case_id": case_id,
        "coordinating_facility_id": facility_id,
        "total_outcomes": len(outcomes),
        "clinical_outcomes": [
            {
                "outcome_id": outcome.outcome_id,
                "recording_facility_id": outcome.facility_id,
                "recorded_by": outcome.recorded_by,
                "outcome_type": outcome.outcome_type,
                "outcome_status": outcome.outcome_status,
                "outcome_summary": outcome.outcome_summary,
                "occurred_at": outcome.occurred_at,
                "review_status": outcome.review_status,
                "reviewed_by": outcome.reviewed_by,
                "reviewed_at": outcome.reviewed_at,
                "review_notes": outcome.review_notes,
                "follow_up_required": outcome.follow_up_required,
                "next_follow_up_at": outcome.next_follow_up_at
            }
            for outcome in outcomes
        ]
    }


@router.post("/{outcome_id}/create-follow-up-task", status_code=201)
def create_follow_up_task_from_outcome(
    outcome_id: int,
    task_data: ClinicalOutcomeFollowUpTask,
    facility_id: int,
    current_user: User = Depends(
        require_permission("MANAGE_CARE_CASES")
    ),
    db: Session = Depends(get_db)
):
    try:
        # 1. Find and lock the clinical outcome.
        clinical_outcome = (
            db.query(ClinicalOutcome)
            .filter(ClinicalOutcome.outcome_id == outcome_id)
            .with_for_update()
            .first()
        )

        if not clinical_outcome:
            raise HTTPException(
                status_code=404,
                detail="Clinical outcome not found."
            )

        # 2. Only the coordinating facility can create this task.
        care_case = db.query(CareCase).filter(
            CareCase.case_id == clinical_outcome.case_id,
            CareCase.coordinating_facility_id == facility_id
        ).with_for_update().first()

        if not care_case:
            raise HTTPException(
                status_code=403,
                detail="Only the coordinating facility can create this follow-up task."
            )

        # 3. Confirm the outcome requires action.
        if clinical_outcome.review_status != "REQUIRES_ACTION":
            raise HTTPException(
                status_code=409,
                detail="This clinical outcome does not require further action."
            )

        # 4. Confirm the requesting user's active membership.
        requester_membership = db.query(FacilityUser).filter(
            FacilityUser.user_id == current_user.user_id,
            FacilityUser.facility_id == facility_id,
            FacilityUser.employment_status == "ACTIVE"
        ).first()

        if not requester_membership:
            raise HTTPException(
                status_code=403,
                detail="You do not have active membership at the coordinating facility."
            )

        # 5. Confirm the selected assignee belongs to the coordinating facility.
        assignee = (
            db.query(FacilityUser)
            .join(Role, FacilityUser.role_id == Role.role_id)
            .filter(
                FacilityUser.facility_user_id == task_data.assigned_to,
                FacilityUser.facility_id == facility_id,
                FacilityUser.employment_status == "ACTIVE",
                Role.role_name.in_(["CARE_COORDINATOR", "CLINICIAN"])
            )
            .first()
            )

        if not assignee:
            raise HTTPException(
                status_code=400,
                detail="The selected assignee is not an active member of this facility."
            )

        # 6. Confirm the assignee is an active user.
        assignee_user = db.query(User).filter(
            User.user_id == assignee.user_id,
            User.is_active == True
        ).first()

        if not assignee_user:
            raise HTTPException(
                status_code=400,
                detail="The selected assignee's user account is inactive."
            )

        # 7. Prevent duplicate follow-up tasks.
        existing_task = db.query(Task).filter(
            Task.clinical_outcome_id == outcome_id
        ).first()

        if existing_task:
            raise HTTPException(
                status_code=409,
                detail="A follow-up task already exists for this clinical outcome."
            )

        # 8. Create the follow-up task.
        follow_up_task = Task(
            public_id=str(uuid.uuid4()),
            case_id=clinical_outcome.case_id,
            clinical_outcome_id=clinical_outcome.outcome_id,
            assigned_to=assignee.facility_user_id,
            assigned_by=current_user.user_id,
            task_type="CLINICAL_OUTCOME_FOLLOW_UP",
            title=task_data.title,
            description=task_data.description,
            task_status="PENDING",
            priority=task_data.priority,
            due_at=task_data.due_at
        )

        db.add(follow_up_task)
        db.flush()

        # 9. Record the audit event.
        record_audit_event(
            db=db,
            actor_user_id=current_user.user_id,
            facility_id=facility_id,
            action="CLINICAL_OUTCOME_FOLLOW_UP_TASK_CREATED",
            entity_type="TASK",
            entity_id=str(follow_up_task.task_id),
            new_values={
                "case_id": follow_up_task.case_id,
                "clinical_outcome_id": follow_up_task.clinical_outcome_id,
                "assigned_to": follow_up_task.assigned_to,
                "task_type": follow_up_task.task_type,
                "priority": follow_up_task.priority
            }
        )

        # 10. Save the task and audit event together.
        db.commit()
        db.refresh(follow_up_task)

        return {
            "message": "Follow-up task created successfully.",
            "task_id": follow_up_task.task_id,
            "clinical_outcome_id": follow_up_task.clinical_outcome_id,
            "case_id": follow_up_task.case_id,
            "assigned_to": follow_up_task.assigned_to,
            "task_status": follow_up_task.task_status,
            "priority": follow_up_task.priority,
            "due_at": follow_up_task.due_at
        }

    except HTTPException:
        db.rollback()
        raise

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A follow-up task already exists or a database constraint was violated."
        )

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="A database error occurred while creating the follow-up task."
        ) 
