
from datetime import datetime, timezone
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.database.connection import get_db
from app.models.task import Task
from app.models.care_case import CareCase
from app.models.facility_user import FacilityUser
from app.models.role import Role
from app.models.user import User
from app.core.dependencies import require_permission
from app.services.audit_service import record_audit_event
from app.schemas.task import (
    TaskCompletion,
    TaskCreate,
    TaskCancellation
)
from app.models.intervention_recommendation import (
    InterventionRecommendation
)


router = APIRouter(
    prefix="/api/v1/tasks",
    tags=["Tasks"]
)



def verify_task_access(
    db: Session,
    task: Task,
    current_user: User,
    facility_id: int
):
    # Confirm the case exists.
    care_case = db.query(CareCase).filter(
        CareCase.case_id == task.case_id
    ).first()

    if not care_case:
        raise HTTPException(
            status_code=404,
            detail="Task not found."
        )
    if care_case.coordinating_facility_id != facility_id:
        raise HTTPException(
            status_code=403,
            detail="This task does not belong to the selected facility."
        )
    

    # Confirm the logged-in user has active membership
    # at the selected facility.
    membership = db.query(FacilityUser).filter(
        FacilityUser.user_id == current_user.user_id,
        FacilityUser.facility_id == facility_id,
        FacilityUser.employment_status == "ACTIVE"
    ).first()

    if not membership:
        raise HTTPException(
            status_code=403,
            detail="You do not belong to this facility."
        )

    # Confirm the task is assigned to an active member
    # of the selected facility.
    assigned_membership = db.query(FacilityUser).filter(
        FacilityUser.facility_user_id == task.assigned_to,
        FacilityUser.facility_id == facility_id,
        FacilityUser.employment_status == "ACTIVE"
    ).first()

    if not assigned_membership:
        raise HTTPException(
            status_code=404,
            detail="Task not found at this facility."
        )

    # Check whether the logged-in user owns the task.
    is_assigned_user = (
        assigned_membership.user_id == current_user.user_id
    )

    # Check administrator access at this facility.
    is_administrator = db.query(FacilityUser).join(
        Role,
        FacilityUser.role_id == Role.role_id
    ).filter(
        FacilityUser.user_id == current_user.user_id,
        FacilityUser.facility_id == facility_id,
        FacilityUser.employment_status == "ACTIVE",
        Role.role_name.in_(
            ["FACILITY_ADMIN", "PLATFORM_ADMIN"]
        )
    ).first()

    if not is_assigned_user and not is_administrator:
        raise HTTPException(
            status_code=403,
            detail="You are not authorised to manage this task."
        )

    return care_case


@router.post("/", status_code=201)
def create_task(
    task_data: TaskCreate,
    facility_id: int,
    current_user: User = Depends(
        require_permission("MANAGE_CARE_CASES")
    ),
    db: Session = Depends(get_db)
):
    try:
        # Confirm the case exists.
        care_case = db.query(CareCase).filter(
            CareCase.case_id == task_data.case_id
        ).with_for_update().first()

        if not care_case:
            raise HTTPException(
                status_code=404,
                detail="Care case not found."
            )
        if care_case.coordinating_facility_id != facility_id:
            raise HTTPException(
                status_code=403,
                detail="This task does not belong to the selected facility."
            )

        # Confirm the assigned staff member belongs
        # to the selected facility.
        assigned_membership = db.query(FacilityUser).filter(
            FacilityUser.facility_user_id == task_data.assigned_to,
            FacilityUser.facility_id == facility_id,
            FacilityUser.employment_status == "ACTIVE"
        ).first()

        if not assigned_membership:
            raise HTTPException(
                status_code=400,
                detail="Assigned staff member is not active at this facility."
            )

        # Create the task.
        task = Task(
            public_id=str(uuid.uuid4()),
            case_id=task_data.case_id,
            assigned_to=task_data.assigned_to,
            assigned_by=current_user.user_id,
            task_type=task_data.task_type,
            title=task_data.title,
            description=task_data.description,
            task_status="PENDING",
            priority=task_data.priority,
            due_at=task_data.due_at
        )

        db.add(task)
        db.flush()

        # Record the action in the audit trail.
        record_audit_event(
            db=db,
            actor_user_id=current_user.user_id,
            facility_id=facility_id,
            action="TASK_CREATED",
            entity_type="TASK",
            entity_id=str(task.task_id),
            new_values={
                "case_id": task.case_id,
                "assigned_to": task.assigned_to,
                "task_type": task.task_type,
                "task_status": task.task_status,
                "priority": task.priority
            }
        )

        db.commit()
        db.refresh(task)

        return {
            "message": "Task created successfully.",
            "task_id": task.task_id,
            "case_id": task.case_id,
            "assigned_to": task.assigned_to,
            "task_status": task.task_status,
            "priority": task.priority
        }

    except HTTPException:
        db.rollback()
        raise

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to create task."
        )


@router.get("/my-tasks")
def get_my_tasks(
    facility_id: int,
    current_user: User = Depends(
        require_permission("MANAGE_CARE_CASES")
    ),
    db: Session = Depends(get_db)
):
    memberships = db.query(
        FacilityUser.facility_user_id
    ).filter(
        FacilityUser.user_id == current_user.user_id,
        FacilityUser.facility_id == facility_id,
        FacilityUser.employment_status == "ACTIVE"
    ).all()

    facility_user_ids = [
        membership[0] for membership in memberships
    ]

    if not facility_user_ids:
        raise HTTPException(
            status_code=403,
            detail="You do not have active membership at this facility."
        )

    try:
        
        tasks = db.query(Task).filter(
            Task.assigned_to.in_(facility_user_ids),
            Task.task_status.in_(
                ["PENDING", "IN_PROGRESS", "OVERDUE"]
            )
        ).order_by(
            Task.due_at.is_(None).asc(),
            Task.due_at.asc()
        ).all()
        now = datetime.now(timezone.utc).replace(tzinfo=None)


        return [
            {
                "task_id": task.task_id,
                "case_id": task.case_id,
                "title": task.title,
                "description": task.description,
                "task_type": task.task_type,
                "task_status": task.task_status,
                "priority": task.priority,
                "due_at": task.due_at,
                "is_overdue": bool(
                    task.due_at
                    and task.due_at < now
                    and task.task_status in [
                        "PENDING", "IN_PROGRESS", "OVERDUE"
                    ]
                )
            }
            for task in tasks
        ]

    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve your tasks."
        )

@router.post("/{task_id}/start")
def start_task(
    task_id: int,
    facility_id: int,
    current_user: User = Depends(
        require_permission("MANAGE_CARE_CASES")
    ),
    db: Session = Depends(get_db)
):
    try:
        task = db.query(Task).filter(
            Task.task_id == task_id
        ).with_for_update().first()

        if not task:
            raise HTTPException(
                status_code=404,
                detail="Task not found."
            )

        verify_task_access(
            db, task, current_user, facility_id
        )

        if task.task_status != "PENDING":
            raise HTTPException(
                status_code=409,
                detail="Only pending tasks can be started."
            )

        old_status = task.task_status
        task.task_status = "IN_PROGRESS"

        record_audit_event(
            db=db,
            actor_user_id=current_user.user_id,
            facility_id=facility_id,
            action="TASK_STARTED",
            entity_type="TASK",
            entity_id=str(task.task_id),
            old_values={"task_status": old_status},
            new_values={"task_status": "IN_PROGRESS"}
        )

        db.commit()
        db.refresh(task)

        return {
            "message": "Task started successfully.",
            "task_id": task.task_id,
            "task_status": task.task_status
        }

    except HTTPException:
        db.rollback()
        raise

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to start task."
        )



@router.post("/{task_id}/complete")
def complete_task(
    task_id: int,
    completion_data: TaskCompletion,
    facility_id: int,
    current_user: User = Depends(
        require_permission("MANAGE_CARE_CASES")
    ),
    db: Session = Depends(get_db)
):
    try:
        # 1. Find and lock the task.
        task = (
            db.query(Task)
            .filter(Task.task_id == task_id)
            .with_for_update()
            .first()
        )

        if not task:
            raise HTTPException(
                status_code=404,
                detail="Task not found."
            )

        # 2. Verify task access.
        verify_task_access(
            db, task, current_user, facility_id
        )

        if task.task_status != "IN_PROGRESS":
            raise HTTPException(
                status_code=409,
                detail="Only in-progress tasks can be completed."
            )

        # 3. If this is an intervention task,
        # find and lock its recommendation.
        recommendation = None
        membership = None

        if task.recommendation_id is not None:

            recommendation = (
                db.query(InterventionRecommendation)
                .filter(
                    InterventionRecommendation.recommendation_id
                    == task.recommendation_id
                )
                .with_for_update()
                .first()
            )

            if not recommendation:
                raise HTTPException(
                    status_code=404,
                    detail="Linked intervention recommendation not found."
                )

            # Confirm the recommendation belongs to this task's case.
            if recommendation.case_id != task.case_id:
                raise HTTPException(
                    status_code=409,
                    detail="The intervention recommendation does not match this task's care case."
                )

            # Only approved recommendations can be implemented.
            if recommendation.recommendation_status != "APPROVED":
                raise HTTPException(
                    status_code=409,
                    detail="The linked intervention recommendation is not approved."
                )

            # Find the actual user completing the task.
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

        # 4. Complete the task.
        old_status = task.task_status

        completed_at = datetime.now(
            timezone.utc
        ).replace(tzinfo=None)

        task.task_status = "COMPLETED"
        task.completed_at = completed_at

        # 5. Record the task completion audit event.
        record_audit_event(
            db=db,
            actor_user_id=current_user.user_id,
            facility_id=facility_id,
            action="TASK_COMPLETED",
            entity_type="TASK",
            entity_id=str(task.task_id),
            old_values={
                "task_status": old_status
            },
            new_values={
                "task_status": "COMPLETED",
                "completion_notes": completion_data.completion_notes
            }
        )

        # 6. If linked to an intervention,
        # mark the recommendation as implemented.
        if recommendation is not None:

            previous_recommendation_status = (
                recommendation.recommendation_status
            )

            recommendation.recommendation_status = "IMPLEMENTED"
            recommendation.executed_by = membership.facility_user_id
            recommendation.executed_at = completed_at
            recommendation.execution_notes = (
                completion_data.completion_notes
            )

            db.flush()

            # Record intervention execution in the audit log.
            record_audit_event(
                db=db,
                actor_user_id=current_user.user_id,
                facility_id=facility_id,
                action="INTERVENTION_RECOMMENDATION_IMPLEMENTED",
                entity_type="INTERVENTION_RECOMMENDATION",
                entity_id=str(recommendation.recommendation_id),
                old_values={
                    "recommendation_status": previous_recommendation_status
                },
                new_values={
                    "recommendation_status": "IMPLEMENTED",
                    "executed_by": recommendation.executed_by,
                    "executed_at": recommendation.executed_at.isoformat(),
                    "execution_notes": recommendation.execution_notes,
                    "task_id": task.task_id
                }
            )

        # 7. Save all changes together.
        db.commit()
        db.refresh(task)

        if recommendation is not None:
            db.refresh(recommendation)

        return {
            "message": "Task completed successfully.",
            "task_id": task.task_id,
            "task_status": task.task_status,
            "completed_at": task.completed_at,
            "recommendation_id": (
                recommendation.recommendation_id
                if recommendation else None
            ),
            "recommendation_status": (
                recommendation.recommendation_status
                if recommendation else None
            )
        }

    except HTTPException:
        db.rollback()
        raise

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="The task or intervention update could not be saved because of a database conflict."
        )

    except SQLAlchemyError as exc:
        import traceback
        traceback.print_exc()

        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="A database error occurred while completing the task."
        )

@router.post("/{task_id}/cancel")
def cancel_task(
    task_id: int,
    cancellation_data: TaskCancellation,
    facility_id: int,
    current_user: User = Depends(
        require_permission("MANAGE_CARE_CASES")
    ),
    db: Session = Depends(get_db)
):
    try:
        task = (
            db.query(Task)
            .filter(Task.task_id == task_id)
            .with_for_update()
            .first()
        )

        if not task:
            raise HTTPException(
                status_code=404,
                detail="Task not found."
            )

        verify_task_access(
            db, task, current_user, facility_id
        )

        if task.task_status != "PENDING":
            raise HTTPException(
                status_code=409,
                detail="Only pending tasks can be cancelled."
            )

        old_status = task.task_status
        task.task_status = "CANCELLED"

        record_audit_event(
            db=db,
            actor_user_id=current_user.user_id,
            facility_id=facility_id,
            action="TASK_CANCELLED",
            entity_type="TASK",
            entity_id=str(task.task_id),
            old_values={
                "task_status": old_status
            },
            new_values={
                "task_status": "CANCELLED",
                "cancellation_reason": (
                    cancellation_data.cancellation_reason
                )
            }
        )

        db.commit()
        db.refresh(task)

        return {
            "message": "Task cancelled successfully.",
            "task_id": task.task_id,
            "task_status": task.task_status
        }

    except HTTPException:
        db.rollback()
        raise

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="The task cancellation could not be saved."
        )

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="A database error occurred while cancelling the task."
        )