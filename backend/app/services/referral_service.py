
import uuid

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.referral import Referral
from app.models.referral_status_history import ReferralStatusHistory
from app.models.care_case import CareCase
from app.models.facility import Facility

from app.services.audit_service import record_audit_event


def create_referral(
    db: Session,
    care_case: CareCase,
    receiving_facility_id: int,
    referred_by: int,
    specialty: str | None,
    referral_type: str,
    referral_reason: str,
    urgency: str,
    due_at: datetime | None
):
    # 1. Ensure the care case is eligible for referral.
    if care_case.case_status in {
        "RESOLVED",
        "CLOSED",
        "TRANSFERRED",
        "CANCELLED"
    }:
        raise ValueError(
            "A referral cannot be created for a resolved "
            "or inactive care case."
        )

    # 2. Validate the receiving facility.
    receiving_facility = (
        db.query(Facility)
        .filter(
            Facility.facility_id == receiving_facility_id,
            Facility.is_active.is_(True)
        )
        .first()
    )

    if not receiving_facility:
        raise ValueError(
            "The receiving facility does not exist "
            "or is inactive."
        )

    # 3. Prevent a facility from referring to itself.
    if (
        receiving_facility_id
        == care_case.coordinating_facility_id
    ):
        raise ValueError(
            "The receiving facility must be different "
            "from the referring facility."
        )

    # 4. Create the referral.
    referral = Referral(
        public_id=str(uuid.uuid4()),
        case_id=care_case.case_id,
        consultation_id=None,
        referring_facility_id=(
            care_case.coordinating_facility_id
        ),
        receiving_facility_id=receiving_facility_id,
        referred_by=referred_by,
        specialty=specialty,
        referral_type=referral_type,
        referral_reason=referral_reason,
        urgency=urgency,
        referral_status="DRAFT",
        due_at=due_at
    )

    db.add(referral)
    db.flush()

    # 5. Record the initial referral history.
    history = ReferralStatusHistory(
        referral_id=referral.referral_id,
        previous_status=None,
        new_status="DRAFT",
        changed_by=referred_by,
        change_reason="Referral created."
    )

    db.add(history)

    # 6. Record the creation in the audit log.
    record_audit_event(
        db=db,
        actor_user_id=referred_by,
        facility_id=care_case.coordinating_facility_id,
        action="REFERRAL_CREATED",
        entity_type="REFERRAL",
        entity_id=str(referral.referral_id),
        new_values={
            "case_id": care_case.case_id,
            "referring_facility_id": (
                care_case.coordinating_facility_id
            ),
            "receiving_facility_id": receiving_facility_id,
            "referral_status": "DRAFT",
            "urgency": urgency
        }
    )

    db.flush()

    return referral

def issue_referral(
    db: Session,
    referral: Referral,
    changed_by: int,
    change_reason: str
):
    if referral.referral_status != "DRAFT":
        raise ValueError(
            "Only draft referrals can be issued."
        )

    previous_status = referral.referral_status

    referral.referral_status = "ISSUED"

    history = ReferralStatusHistory(
        referral_id=referral.referral_id,
        previous_status=previous_status,
        new_status="ISSUED",
        changed_by=changed_by,
        change_reason=change_reason
    )

    db.add(history)

    record_audit_event(
        db=db,
        actor_user_id=changed_by,
        facility_id=referral.referring_facility_id,
        action="REFERRAL_ISSUED",
        entity_type="REFERRAL",
        entity_id=str(referral.referral_id),
        old_values={
            "referral_status": previous_status
        },
        new_values={
            "referral_status": "ISSUED",
            "change_reason": change_reason
        }
    )

    db.flush()

    return referral