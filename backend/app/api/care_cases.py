from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.database.connection import get_db
from app.models.care_case import CareCase
from app.models.user import User

from app.schemas.care_case import (
    CareCaseAssignmentCreate,
    CareCaseStatusUpdate,
    CareCaseClosureCreate
)
from app.core.dependencies import require_permission

from app.services.care_case_service import (
    find_eligible_case_recipient,
    assign_existing_care_case,
    transition_care_case_status,
    close_care_case
)
from app.services.audit_service import record_audit_event
from app.models.facility_user import FacilityUser
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.permission import Permission

router = APIRouter(
    prefix="/api/v1/care-cases",
    tags=["Care Cases"]
)

@router.post("/{case_id}/assign")
def assign_care_case(
    case_id: int,
    assignment_data: CareCaseAssignmentCreate,
    facility_id: int,
    current_user: User = Depends(
        require_permission("ASSIGN_CASES")
    ),
    db: Session = Depends(get_db)
):
    # 1. Find the case within the requesting facility.
    care_case = (
        db.query(CareCase)
        .filter(
            CareCase.case_id == case_id,
            CareCase.coordinating_facility_id == facility_id
        )
        .with_for_update()
        .first()
    )

    if not care_case:
        raise HTTPException(
            status_code=404,
            detail="Care case not found."
        )

    # 2. Find an eligible recipient at the same facility.
    recipient = find_eligible_case_recipient(
        db=db,
        facility_id=facility_id,
        recipient_facility_user_id=(
            assignment_data.recipient_facility_user_id
        )
    )

    if not recipient:
        raise HTTPException(
            status_code=422,
            detail=(
                "The selected user is not an active, "
                "eligible member of this facility."
            )
        )

    # 3. Create the assignment and update the pending task.
    try:
        assignment = assign_existing_care_case(
            db=db,
            care_case=care_case,
            recipient=recipient,
            assigned_by=current_user.user_id,
            assignment_reason=assignment_data.assignment_reason
        )

        # 4. Record the assignment in the audit log.
        record_audit_event(
            db=db,
            actor_user_id=current_user.user_id,
            facility_id=facility_id,
            action="CASE_ASSIGNED",
            entity_type="CASE_ASSIGNMENT",
            entity_id=str(assignment.assignment_id),
            new_values={
                "case_id": care_case.case_id,
                "facility_user_id": recipient.facility_user_id,
                "assigned_by": current_user.user_id,
                "assignment_reason": assignment_data.assignment_reason
            }
        )

        db.commit()
        db.refresh(assignment)

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="The case assignment could not be saved because of a database conflict."
        )

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="A database error occurred while assigning the care case."
        )

    return {
        "message": "Care case assigned successfully.",
        "case_id": care_case.case_id,
        "assignment_id": assignment.assignment_id,
        "facility_user_id": recipient.facility_user_id,
        "assigned_by": current_user.user_id
    }



@router.patch("/{case_id}/status")
def update_care_case_status(
    case_id: int,
    status_data: CareCaseStatusUpdate,
    facility_id: int,
    current_user: User = Depends(
        require_permission("MANAGE_CARE_CASES")
    ),
    db: Session = Depends(get_db)
):
    # 1. Find and lock the case within the requesting facility.
    care_case = (
        db.query(CareCase)
        .filter(
            CareCase.case_id == case_id,
            CareCase.coordinating_facility_id == facility_id
        )
        .with_for_update()
        .first()
    )

    if not care_case:
        raise HTTPException(
            status_code=404,
            detail="Care case not found."
        )

    # 2. Validate and perform the status transition.
    try:
        previous_status = care_case.case_status

        transition_care_case_status(
            db=db,
            care_case=care_case,
            new_status=status_data.new_status,
            changed_by=current_user.user_id,
            change_reason=status_data.change_reason
        )

        # 3. Commit the status, history and audit record together.
        db.commit()
        db.refresh(care_case)

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
            detail="The status change could not be saved because of a database conflict."
        )

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="A database error occurred while updating the care case."
        )

    return {
        "message": "Care case status updated successfully.",
        "case_id": care_case.case_id,
        "previous_status": previous_status,
        "new_status": care_case.case_status,
        "changed_by": current_user.user_id
    }


@router.post("/{case_id}/close")
def close_care_case_endpoint(
    case_id: int,
    closure_data: CareCaseClosureCreate,
    facility_id: int,
    current_user: User = Depends(
        require_permission("CLOSE_CASES")
    ),
    db: Session = Depends(get_db)
):
    # 1. Find and lock the case within the requesting facility.
    care_case = (
        db.query(CareCase)
        .filter(
            CareCase.case_id == case_id,
            CareCase.coordinating_facility_id == facility_id
        )
        .with_for_update()
        .first()
    )

    if not care_case:
        raise HTTPException(
            status_code=404,
            detail="Care case not found."
        )

    # 2. Find the active facility membership authorised to close cases.
    authorising_membership = (
        db.query(FacilityUser)
        .join(
            Role,
            FacilityUser.role_id == Role.role_id
        )
        .join(
            RolePermission,
            Role.role_id == RolePermission.role_id
        )
        .join(
            Permission,
            RolePermission.permission_id == Permission.permission_id
        )
        .filter(
            FacilityUser.user_id == current_user.user_id,
            FacilityUser.facility_id == facility_id,
            FacilityUser.employment_status == "ACTIVE",
            Permission.permission_name == "CLOSE_CASES"
        )
        .first()
    )

    if not authorising_membership:
        raise HTTPException(
            status_code=403,
            detail="No authorised facility membership found."
        )

    # 3. Create the formal closure and update the case.
    try:
        closure = close_care_case(
            db=db,
            care_case=care_case,
            closure_type=closure_data.closure_type,
            closure_reason=closure_data.closure_reason,
            evidence_summary=closure_data.evidence_summary,
            authorised_by=current_user.user_id,
            authorised_facility_user_id=(
                authorising_membership.facility_user_id
            )
        )

        # 4. Commit all changes together.
        db.commit()
        db.refresh(closure)
        db.refresh(care_case)

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
            detail="The case closure could not be saved because of a database conflict."
        )

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="A database error occurred while closing the care case."
        )

    return {
        "message": "Care case closed successfully.",
        "case_id": care_case.case_id,
        "closure_id": closure.closure_id,
        "closure_type": closure.closure_type,
        "case_status": care_case.case_status,
        "authorised_by": current_user.user_id,
        "authorised_facility_user_id": (
            authorising_membership.facility_user_id
        )
    }

