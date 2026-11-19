
import uuid

from sqlalchemy.orm import Session

from app.models.consultation import Consultation
from app.models.referral import Referral
from app.models.facility_user import FacilityUser
from app.models.user import User
from app.models.permission import Permission
from app.models.role_permission import RolePermission
from datetime import datetime, timezone
from app.services.audit_service import record_audit_event
from pydantic import BaseModel, Field
from datetime import datetime


def create_consultation(
    db: Session,
    referral: Referral,
    clinician_user_id: int,
    facility_id: int,
    consultation_type: str,
    consultation_channel: str,
    scheduled_at=None
):
    if referral.referral_status != "ACCEPTED":
        raise ValueError(
            "Only accepted referrals can have consultations created."
        )

    if referral.receiving_facility_id != facility_id:
        raise ValueError(
            "Consultation must be created at the receiving facility."
        )

    if referral.consultation_id is not None:
        raise ValueError(
            "A consultation already exists for this referral."
        )

    clinician_membership = (
        db.query(FacilityUser)
        .join(User, User.user_id == FacilityUser.user_id)
        .join(
            RolePermission,
            RolePermission.role_id == FacilityUser.role_id
        )
        .join(
            Permission,
            Permission.permission_id == RolePermission.permission_id
        )
        .filter(
            FacilityUser.user_id == clinician_user_id,
            FacilityUser.facility_id == facility_id,
            FacilityUser.employment_status == "ACTIVE",
            User.is_active.is_(True),
            Permission.permission_name == "MANAGE_CONSULTATIONS"
        )
        .first()
    )

    if not clinician_membership:
        raise ValueError(
            "You must have active consultation-management access "
            "at this facility."
        )

    consultation_status = (
        "SCHEDULED" if scheduled_at else "REQUESTED"
    )

    consultation = Consultation(
        public_id=str(uuid.uuid4()),
        case_id=referral.case_id,
        facility_id=facility_id,
        clinician_id=clinician_membership.facility_user_id,
        consultation_type=consultation_type,
        consultation_channel=consultation_channel,
        consultation_status=consultation_status,
        scheduled_at=scheduled_at
    )

    db.add(consultation)
    db.flush()

    referral.consultation_id = consultation.consultation_id

    db.flush()

    return consultation


def schedule_consultation(
    db: Session,
    consultation: Consultation,
    clinician_user_id: int,
    scheduled_at: datetime
):
    if consultation.consultation_status != "REQUESTED":
        raise ValueError(
            "Only requested consultations can be scheduled."
        )

    clinician_membership = (
        db.query(FacilityUser)
        .join(User, User.user_id == FacilityUser.user_id)
        .filter(
            FacilityUser.facility_user_id == consultation.clinician_id,
            FacilityUser.user_id == clinician_user_id,
            FacilityUser.facility_id == consultation.facility_id,
            FacilityUser.employment_status == "ACTIVE",
            User.is_active.is_(True)
        )
        .first()
    )

    if not clinician_membership:
        raise ValueError(
            "Only the assigned active clinician can schedule this consultation."
        )

    if scheduled_at <= datetime.now(timezone.utc):
        raise ValueError(
            "The scheduled time must be in the future."
        )

    previous_status = consultation.consultation_status

    consultation.consultation_status = "SCHEDULED"
    consultation.scheduled_at = scheduled_at

    record_audit_event(
        db=db,
        actor_user_id=clinician_user_id,
        facility_id=consultation.facility_id,
        action="CONSULTATION_SCHEDULED",
        entity_type="CONSULTATION",
        entity_id=str(consultation.consultation_id),
        old_values={
            "consultation_status": previous_status
        },
        new_values={
            "consultation_status": "SCHEDULED",
            "scheduled_at": scheduled_at.isoformat()
        }
    )

    db.flush()

    return consultation  



def start_consultation(
    db: Session,
    consultation: Consultation,
    clinician_user_id: int
):
    if consultation.consultation_status != "SCHEDULED":
        raise ValueError(
            "Only scheduled consultations can be started."
        )

    clinician_membership = (
        db.query(FacilityUser)
        .join(User, User.user_id == FacilityUser.user_id)
        .filter(
            FacilityUser.facility_user_id == consultation.clinician_id,
            FacilityUser.user_id == clinician_user_id,
            FacilityUser.facility_id == consultation.facility_id,
            FacilityUser.employment_status == "ACTIVE",
            User.is_active.is_(True)
        )
        .first()
    )

    if not clinician_membership:
        raise ValueError(
            "Only the assigned active clinician can start this consultation."
        )

    now = datetime.now(timezone.utc)
    previous_status = consultation.consultation_status

    consultation.consultation_status = "IN_PROGRESS"
    consultation.started_at = now

    record_audit_event(
        db=db,
        actor_user_id=clinician_user_id,
        facility_id=consultation.facility_id,
        action="CONSULTATION_STARTED",
        entity_type="CONSULTATION",
        entity_id=str(consultation.consultation_id),
        old_values={
            "consultation_status": previous_status
        },
        new_values={
            "consultation_status": "IN_PROGRESS",
            "started_at": now.isoformat()
        }
    )

    db.flush()

    return consultation


def complete_consultation(
    db: Session,
    consultation: Consultation,
    clinician_user_id: int,
    outcome_summary: str,
    follow_up_required: bool
):
    if consultation.consultation_status != "IN_PROGRESS":
        raise ValueError(
            "Only consultations in progress can be completed."
        )

    clinician_membership = (
        db.query(FacilityUser)
        .join(User, User.user_id == FacilityUser.user_id)
        .filter(
            FacilityUser.facility_user_id == consultation.clinician_id,
            FacilityUser.user_id == clinician_user_id,
            FacilityUser.facility_id == consultation.facility_id,
            FacilityUser.employment_status == "ACTIVE",
            User.is_active.is_(True)
        )
        .first()
    )

    if not clinician_membership:
        raise ValueError(
            "Only the assigned active clinician can complete this consultation."
        )

    now = datetime.now(timezone.utc)
    previous_status = consultation.consultation_status

    consultation.consultation_status = "COMPLETED"
    consultation.completed_at = now
    consultation.outcome_summary = outcome_summary
    consultation.follow_up_required = follow_up_required

    record_audit_event(
        db=db,
        actor_user_id=clinician_user_id,
        facility_id=consultation.facility_id,
        action="CONSULTATION_COMPLETED",
        entity_type="CONSULTATION",
        entity_id=str(consultation.consultation_id),
        old_values={
            "consultation_status": previous_status
        },
        new_values={
            "consultation_status": "COMPLETED",
            "completed_at": now.isoformat(),
            "follow_up_required": follow_up_required
        }
    )

    db.flush()

    return consultation