from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.core.dependencies import require_permission

from app.models.care_case import CareCase
from app.models.intervention_recommendation import (
    InterventionRecommendation
)
from app.models.facility_user import FacilityUser
from app.ai.interventions import save_intervention_recommendations
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.models.user import User
from app.schemas.intervention import (
    InterventionReview,
    InterventionExecutionTask
)
from app.services.audit_service import record_audit_event
from uuid import uuid4
from app.models.task import Task
from app.models.role import Role

router = APIRouter(
    prefix="/api/v1/interventions",
    tags=["Interventions"]
)

@router.get("/cases/{case_id}")
def get_case_interventions(
    case_id: int,
    facility_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("MANAGE_CARE_CASES"))
):
    # Confirm that the care case exists
    care_case = db.query(CareCase).filter(
        CareCase.case_id == case_id
    ).first()

    if not care_case:
        raise HTTPException(
            status_code=404,
            detail="Care case not found."
        )

    # Ensure the selected facility coordinates this case
    if care_case.coordinating_facility_id != facility_id:
        raise HTTPException(
            status_code=403,
            detail="You cannot access recommendations for this care case."
        )

    # Retrieve recommendations for this case
    recommendations = (
        db.query(InterventionRecommendation)
        .filter(
            InterventionRecommendation.case_id == case_id
        )
        .order_by(
            InterventionRecommendation.created_at.desc()
        )
        .all()
    )

    return {
        "case_id": case_id,
        "total_recommendations": len(recommendations),
        "recommendations": [
            {
                "recommendation_id": item.recommendation_id,
                "assessment_id": item.assessment_id,
                "recommendation_type": item.recommendation_type,
                "recommendation": item.recommendation,
                "status": item.recommendation_status,
                "created_at": item.created_at
            }
            for item in recommendations
        ]
    }


@router.post("/{recommendation_id}/review")
def review_intervention_recommendation(
    recommendation_id: int,
    review_data: InterventionReview,
    facility_id: int,
    current_user: User = Depends(
        require_permission("MANAGE_CARE_CASES")
    ),
    db: Session = Depends(get_db)
):
    try:
        # 1. Find and lock the recommendation.
        recommendation = (
            db.query(InterventionRecommendation)
            .filter(
                InterventionRecommendation.recommendation_id
                == recommendation_id
            )
            .with_for_update()
            .first()
        )

        if not recommendation:
            raise HTTPException(
                status_code=404,
                detail="Intervention recommendation not found."
            )

        # 2. Confirm that the case belongs to this coordinating facility.
        care_case = (
            db.query(CareCase)
            .filter(
                CareCase.case_id == recommendation.case_id,
                CareCase.coordinating_facility_id == facility_id
            )
            .with_for_update()
            .first()
        )

        if not care_case:
            raise HTTPException(
                status_code=403,
                detail="This facility is not authorised to review this recommendation."
            )

        # 3. Confirm the reviewer's active facility membership.
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

        # 4. Prevent recommendations from being reviewed twice.
        if recommendation.recommendation_status != "PENDING_REVIEW":
            raise HTTPException(
                status_code=409,
                detail="This intervention recommendation has already been reviewed or processed."
            )

        # 5. Save the review decision.
        previous_status = recommendation.recommendation_status

        recommendation.recommendation_status = review_data.review_status
        recommendation.reviewed_by = membership.facility_user_id
        recommendation.reviewed_at = (
            datetime.now(timezone.utc).replace(tzinfo=None)
        )

        db.flush()

        # 6. Record the review in the audit log.
        record_audit_event(
            db=db,
            actor_user_id=current_user.user_id,
            facility_id=facility_id,
            action="INTERVENTION_RECOMMENDATION_REVIEWED",
            entity_type="INTERVENTION_RECOMMENDATION",
            entity_id=str(recommendation.recommendation_id),
            old_values={
                "recommendation_status": previous_status
            },
            new_values={
                "recommendation_status": recommendation.recommendation_status,
                "reviewed_by": recommendation.reviewed_by,
                "review_notes": review_data.review_notes
            }
        )

        # 7. Save the decision and audit event together.
        db.commit()
        db.refresh(recommendation)

        return {
            "message": "Intervention recommendation reviewed successfully.",
            "recommendation_id": recommendation.recommendation_id,
            "case_id": recommendation.case_id,
            "review_status": recommendation.recommendation_status,
            "reviewed_by": recommendation.reviewed_by,
            "reviewed_at": recommendation.reviewed_at,
            "review_notes": review_data.review_notes
        }

    except HTTPException:
        db.rollback()
        raise

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="The intervention review could not be saved because of a database conflict."
        )

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="A database error occurred while reviewing the intervention recommendation."
        )


@router.post("/{recommendation_id}/create-task", status_code=201)
def create_intervention_execution_task(
    recommendation_id: int,
    task_data: InterventionExecutionTask,
    facility_id: int,
    current_user: User = Depends(
        require_permission("MANAGE_CARE_CASES")
    ),
    db: Session = Depends(get_db)
):
    try:
        # 1. Find and lock the recommendation.
        recommendation = (
            db.query(InterventionRecommendation)
            .filter(
                InterventionRecommendation.recommendation_id
                == recommendation_id
            )
            .with_for_update()
            .first()
        )

        if not recommendation:
            raise HTTPException(
                status_code=404,
                detail="Intervention recommendation not found."
            )

        # 2. Confirm that the recommendation has been approved.
        if recommendation.recommendation_status != "APPROVED":
            raise HTTPException(
                status_code=409,
                detail="Only approved recommendations can generate execution tasks."
            )

        # 3. Confirm the case belongs to this coordinating facility.
        care_case = (
            db.query(CareCase)
            .filter(
                CareCase.case_id == recommendation.case_id,
                CareCase.coordinating_facility_id == facility_id
            )
            .with_for_update()
            .first()
        )

        if not care_case:
            raise HTTPException(
                status_code=403,
                detail="Only the coordinating facility can create this execution task."
            )

        # 4. Verify the requesting user's active membership.
        requester_membership = db.query(FacilityUser).filter(
            FacilityUser.user_id == current_user.user_id,
            FacilityUser.facility_id == facility_id,
            FacilityUser.employment_status == "ACTIVE"
        ).first()

        if not requester_membership:
            raise HTTPException(
                status_code=403,
                detail="You do not have active membership at this facility."
            )

        # 5. Verify the selected assignee's role and membership.
        assignee = (
            db.query(FacilityUser)
            .join(Role, FacilityUser.role_id == Role.role_id)
            .filter(
                FacilityUser.facility_user_id == task_data.assigned_to,
                FacilityUser.facility_id == facility_id,
                FacilityUser.employment_status == "ACTIVE",
                Role.role_name.in_([
                    "CARE_COORDINATOR",
                    "CLINICIAN"
                ])
            )
            .first()
        )

        if not assignee:
            raise HTTPException(
                status_code=400,
                detail="The selected assignee is not an eligible active member of this facility."
            )

        # 6. Confirm the assignee's user account is active.
        assignee_user = db.query(User).filter(
            User.user_id == assignee.user_id,
            User.is_active == True
        ).first()

        if not assignee_user:
            raise HTTPException(
                status_code=400,
                detail="The selected assignee's user account is inactive."
            )

        # 7. Prevent duplicate execution tasks.
        existing_task = db.query(Task).filter(
            Task.recommendation_id == recommendation_id
        ).first()

        if existing_task:
            raise HTTPException(
                status_code=409,
                detail="An execution task already exists for this recommendation."
            )

        # 8. Create the execution task.
        execution_task = Task(
            public_id=str(uuid4()),
            case_id=recommendation.case_id,
            recommendation_id=recommendation.recommendation_id,
            assigned_to=assignee.facility_user_id,
            assigned_by=current_user.user_id,
            task_type="INTERVENTION_EXECUTION",
            title=task_data.title,
            description=task_data.description,
            task_status="PENDING",
            priority=task_data.priority,
            due_at=task_data.due_at
        )

        db.add(execution_task)
        db.flush()

        # 9. Record the creation in the audit log.
        record_audit_event(
            db=db,
            actor_user_id=current_user.user_id,
            facility_id=facility_id,
            action="INTERVENTION_EXECUTION_TASK_CREATED",
            entity_type="TASK",
            entity_id=str(execution_task.task_id),
            new_values={
                "recommendation_id": recommendation_id,
                "case_id": execution_task.case_id,
                "assigned_to": execution_task.assigned_to,
                "task_type": execution_task.task_type,
                "priority": execution_task.priority
            }
        )

        # 10. Save the task and audit event together.
        db.commit()
        db.refresh(execution_task)

        return {
            "message": "Intervention execution task created successfully.",
            "task_id": execution_task.task_id,
            "recommendation_id": execution_task.recommendation_id,
            "case_id": execution_task.case_id,
            "assigned_to": execution_task.assigned_to,
            "task_status": execution_task.task_status,
            "priority": execution_task.priority,
            "due_at": execution_task.due_at
        }

    except HTTPException:
        db.rollback()
        raise

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="An execution task already exists or a database constraint was violated."
        )

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="A database error occurred while creating the execution task."
        )

