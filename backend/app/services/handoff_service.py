import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.handoff import Handoff
from app.models.handoff_event import HandoffEvent
from app.models.referral import Referral
from app.models.referral_status_history import ReferralStatusHistory
from app.models.facility_user import FacilityUser
from app.models.user import User

from app.services.audit_service import record_audit_event
from app.models.permission import Permission
from app.models.role_permission import RolePermission

def send_referral_handoff(
    db: Session,
    referral: Referral,
    sender_user_id: int,
    event_notes: str | None = None,
    external_reference: str | None = None
):
    if referral.referral_status != "ISSUED":
        raise ValueError(
            "Only issued referrals can be sent."
        )

    sender_membership = (
        db.query(FacilityUser)
        .join(User, User.user_id == FacilityUser.user_id)
        .filter(
            FacilityUser.user_id == sender_user_id,
            FacilityUser.facility_id == referral.referring_facility_id,
            FacilityUser.employment_status == "ACTIVE",
            User.is_active.is_(True)
        )
        .first()
    )

    if not sender_membership:
        raise ValueError(
            "You do not have an active membership at the referring facility."
        )

    existing_handoff = (
        db.query(Handoff)
        .filter(
            Handoff.referral_id == referral.referral_id,
            Handoff.handoff_status.in_([
                "PREPARED",
                "SENT",
                "RECEIVED",
                "ACCEPTED"
            ])
        )
        .first()
    )

    if existing_handoff:
        raise ValueError(
            "An active handoff already exists for this referral."
        )

    now = datetime.now(timezone.utc)

    handoff = Handoff(
        public_id=str(uuid.uuid4()),
        referral_id=referral.referral_id,
        sending_facility_id=referral.referring_facility_id,
        receiving_facility_id=referral.receiving_facility_id,
        sent_by=sender_membership.facility_user_id,
        handoff_status="SENT",
        sent_at=now
    )

    db.add(handoff)
    db.flush()

    handoff_event = HandoffEvent(
        handoff_id=handoff.handoff_id,
        actor_facility_user_id=sender_membership.facility_user_id,
        event_type="SENT",
        event_notes=event_notes,
        external_reference=external_reference,
        event_at=now
    )

    db.add(handoff_event)

    referral.referral_status = "SENT"

    referral_history = ReferralStatusHistory(
        referral_id=referral.referral_id,
        previous_status="ISSUED",
        new_status="SENT",
        changed_by=sender_user_id,
        change_reason="Referral handoff sent to receiving facility."
    )

    db.add(referral_history)

    record_audit_event(
        db=db,
        actor_user_id=sender_user_id,
        facility_id=referral.referring_facility_id,
        action="REFERRAL_HANDOFF_SENT",
        entity_type="HANDOFF",
        entity_id=str(handoff.handoff_id),
        new_values={
            "referral_id": referral.referral_id,
            "sending_facility_id": referral.referring_facility_id,
            "receiving_facility_id": referral.receiving_facility_id,
            "handoff_status": "SENT"
        }
    )

    db.flush()

    return handoff

def receive_referral_handoff(
    db: Session,
    handoff: Handoff,
    receiver_user_id: int,
    event_notes: str | None = None,
    external_reference: str | None = None
):
    if handoff.handoff_status != "SENT":
        raise ValueError(
            "Only sent handoffs can be received."
        )

    referral = (
        db.query(Referral)
        .filter(
            Referral.referral_id == handoff.referral_id
        )
        .with_for_update()
        .first()
    )

    if not referral or referral.referral_status != "SENT":
        raise ValueError(
            "The associated referral must have SENT status."
        )

    receiver_membership = (
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
            FacilityUser.user_id == receiver_user_id,
            FacilityUser.facility_id == handoff.receiving_facility_id,
            FacilityUser.employment_status == "ACTIVE",
            User.is_active.is_(True),
            Permission.permission_name == "MANAGE_REFERRALS"
        )
        .first()
    )

    if not receiver_membership:
        raise ValueError(
            "You must have active referral-management access at the receiving facility."
        )

    now = datetime.now(timezone.utc)

    handoff.handoff_status = "RECEIVED"
    handoff.received_by = receiver_membership.facility_user_id
    handoff.received_at = now

    db.add(
        HandoffEvent(
            handoff_id=handoff.handoff_id,
            actor_facility_user_id=receiver_membership.facility_user_id,
            event_type="RECEIVED",
            event_notes=event_notes,
            external_reference=external_reference,
            event_at=now
        )
    )

    previous_status = referral.referral_status

    referral.referral_status = "ACKNOWLEDGED"

    db.add(
        ReferralStatusHistory(
            referral_id=referral.referral_id,
            previous_status=previous_status,
            new_status="ACKNOWLEDGED",
            changed_by=receiver_user_id,
            change_reason="Receiving facility acknowledged receipt of referral."
        )
    )

    record_audit_event(
        db=db,
        actor_user_id=receiver_user_id,
        facility_id=handoff.receiving_facility_id,
        action="REFERRAL_HANDOFF_RECEIVED",
        entity_type="HANDOFF",
        entity_id=str(handoff.handoff_id),
        old_values={
            "handoff_status": "SENT",
            "referral_status": previous_status
        },
        new_values={
            "handoff_status": "RECEIVED",
            "referral_status": "ACKNOWLEDGED"
        }
    )

    db.flush()

    return handoff


def decide_referral_handoff(
    db: Session,
    handoff: Handoff,
    receiver_user_id: int,
    decision: str,
    decision_reason: str
):
    if decision not in ["ACCEPTED", "REJECTED"]:
        raise ValueError(
            "Decision must be ACCEPTED or REJECTED."
        )

    if handoff.handoff_status != "RECEIVED":
        raise ValueError(
            "Only received handoffs can be accepted or rejected."
        )

    referral = (
        db.query(Referral)
        .filter(
            Referral.referral_id == handoff.referral_id
        )
        .with_for_update()
        .first()
    )

    if not referral or referral.referral_status != "ACKNOWLEDGED":
        raise ValueError(
            "The associated referral must have ACKNOWLEDGED status."
        )

    receiver_membership = (
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
            FacilityUser.user_id == receiver_user_id,
            FacilityUser.facility_id == handoff.receiving_facility_id,
            FacilityUser.employment_status == "ACTIVE",
            User.is_active.is_(True),
            Permission.permission_name == "MANAGE_REFERRALS"
        )
        .first()
    )

    if not receiver_membership:
        raise ValueError(
            "You must have active referral-management access "
            "at the receiving facility."
        )

    now = datetime.now(timezone.utc)

    previous_handoff_status = handoff.handoff_status
    previous_referral_status = referral.referral_status

    handoff.handoff_status = decision
    referral.referral_status = decision

    if decision == "ACCEPTED":
        handoff.accepted_by = receiver_membership.facility_user_id
        handoff.accepted_at = now
        event_type = "ACCEPTED"
        audit_action = "REFERRAL_HANDOFF_ACCEPTED"

    else:
        handoff.rejected_at = now
        handoff.rejection_reason = decision_reason
        event_type = "REJECTED"
        audit_action = "REFERRAL_HANDOFF_REJECTED"

    db.add(
        HandoffEvent(
            handoff_id=handoff.handoff_id,
            actor_facility_user_id=receiver_membership.facility_user_id,
            event_type=event_type,
            event_notes=decision_reason,
            event_at=now
        )
    )

    db.add(
        ReferralStatusHistory(
            referral_id=referral.referral_id,
            previous_status=previous_referral_status,
            new_status=decision,
            changed_by=receiver_user_id,
            change_reason=decision_reason
        )
    )

    record_audit_event(
        db=db,
        actor_user_id=receiver_user_id,
        facility_id=handoff.receiving_facility_id,
        action=audit_action,
        entity_type="HANDOFF",
        entity_id=str(handoff.handoff_id),
        old_values={
            "handoff_status": previous_handoff_status,
            "referral_status": previous_referral_status
        },
        new_values={
            "handoff_status": decision,
            "referral_status": decision,
            "decision_reason": decision_reason
        }
    )

    db.flush()

    return handoff
