from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.database.connection import get_db
from app.models.escalation import Escalation
from app.models.care_case import CareCase
from app.models.facility_user import FacilityUser
from app.models.role import Role
from app.models.user import User
from app.core.dependencies import require_permission
from app.services.escalation_service import (
    acknowledge_escalation,
    resolve_escalation,
)
from app.schemas.escalation import EscalationResolve


router = APIRouter(
    prefix="/api/v1/escalations",
    tags=["Escalations"]
)


def get_authorised_escalation(
    db: Session,
    escalation: Escalation,
    current_user: User,
    facility_id: int
):
    # Check whether the current user is the assigned staff member.
    is_assigned_user = db.query(FacilityUser).filter(
        FacilityUser.facility_user_id == escalation.assigned_to,
        FacilityUser.user_id == current_user.user_id,
        FacilityUser.facility_id == facility_id,
        FacilityUser.employment_status == "ACTIVE"
    ).first()

    # Facility and platform administrators may also oversee escalations.
    is_administrator = db.query(FacilityUser).join(
        Role,
        FacilityUser.role_id == Role.role_id
    ).filter(
        FacilityUser.user_id == current_user.user_id,
        FacilityUser.facility_id == facility_id,
        FacilityUser.employment_status == "ACTIVE",
        Role.role_name.in_(["FACILITY_ADMIN", "PLATFORM_ADMIN"])
    ).first()

    if not is_assigned_user and not is_administrator:
        raise HTTPException(
            status_code=403,
            detail="You are not authorised to manage this escalation."
        )


def get_escalation_for_facility(
    db: Session,
    escalation_id: int,
    facility_id: int
):
    return db.query(Escalation).join(
        CareCase,
        Escalation.case_id == CareCase.case_id
    ).filter(
        Escalation.escalation_id == escalation_id,
        CareCase.coordinating_facility_id == facility_id
    ).with_for_update().first()


@router.post("/{escalation_id}/acknowledge")
def acknowledge_escalation_endpoint(
    escalation_id: int,
    facility_id: int,
    current_user: User = Depends(
        require_permission("MANAGE_ESCALATIONS")
    ),
    db: Session = Depends(get_db)
):
    try:
        escalation = get_escalation_for_facility(
            db, escalation_id, facility_id
        )

        if not escalation:
            raise HTTPException(
                status_code=404,
                detail="Escalation not found."
            )

        get_authorised_escalation(
            db, escalation, current_user, facility_id
        )

        result = acknowledge_escalation(
            db, escalation, current_user.user_id
        )

        db.commit()
        db.refresh(result)

        return result

    except HTTPException:
        db.rollback()
        raise

    except ValueError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(error))

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to acknowledge escalation."
        )


@router.post("/{escalation_id}/resolve")
def resolve_escalation_endpoint(
    escalation_id: int,
    resolution_data: EscalationResolve,
    facility_id: int,
    current_user: User = Depends(
        require_permission("MANAGE_ESCALATIONS")
    ),
    db: Session = Depends(get_db)
):
    try:
        escalation = get_escalation_for_facility(
            db, escalation_id, facility_id
        )

        if not escalation:
            raise HTTPException(
                status_code=404,
                detail="Escalation not found."
            )

        get_authorised_escalation(
            db, escalation, current_user, facility_id
        )

        result = resolve_escalation(
            db,
            escalation,
            current_user.user_id,
            resolution_data.resolution_notes
        )

        db.commit()
        db.refresh(result)

        return result

    except HTTPException:
        db.rollback()
        raise

    except ValueError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(error))

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to resolve escalation."
        )