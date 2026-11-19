
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.database.connection import get_db
from app.models.care_case import CareCase
from app.models.user import User
from app.schemas.referral import (
    ReferralCreate,
    ReferralStatusUpdate
)
from app.core.dependencies import require_permission

from app.services.referral_service import (
    create_referral,
    issue_referral
)
from app.models.referral import Referral
from app.models.handoff import Handoff
from app.services.handoff_service import (
    send_referral_handoff,
    receive_referral_handoff,
    decide_referral_handoff
)
from app.schemas.handoff import (
    HandoffSend,
    HandoffReceive,
    HandoffDecision
)

from app.schemas.consultation import (
    ConsultationCreate,
    ConsultationSchedule,
    ConsultationCompletion
)

from app.services.consultation_service import (
    create_consultation,
    schedule_consultation,
    start_consultation,
    complete_consultation
)

from app.models.consultation import Consultation


router = APIRouter(
    prefix="/api/v1/referrals",
    tags=["Referrals"]
)


@router.post("/")
def create_care_referral(
    case_id: int,
    referral_data: ReferralCreate,
    facility_id: int,
    current_user: User = Depends(
        require_permission("MANAGE_REFERRALS")
    ),
    db: Session = Depends(get_db)
):
    # 1. Find the care case within the requesting facility.
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

    # 2. Create the referral.
    try:
        referral = create_referral(
            db=db,
            care_case=care_case,
            receiving_facility_id=(
                referral_data.receiving_facility_id
            ),
            referred_by=current_user.user_id,
            specialty=referral_data.specialty,
            referral_type=referral_data.referral_type,
            referral_reason=referral_data.referral_reason,
            urgency=referral_data.urgency,
            due_at=referral_data.due_at
        )

        db.commit()
        db.refresh(referral)

    except ValueError as error:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail=str(error)
        )

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="The referral could not be saved because of a database conflict."
        )

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="A database error occurred while creating the referral."
        )

    return {
        "message": "Referral created successfully.",
        "referral_id": referral.referral_id,
        "public_id": referral.public_id,
        "case_id": referral.case_id,
        "referring_facility_id": referral.referring_facility_id,
        "receiving_facility_id": referral.receiving_facility_id,
        "referral_status": referral.referral_status,
        "urgency": referral.urgency
    }


@router.post("/{referral_id}/issue")
def issue_care_referral(
    referral_id: int,
    status_data: ReferralStatusUpdate,
    facility_id: int,
    current_user: User = Depends(
        require_permission("MANAGE_REFERRALS")
    ),
    db: Session = Depends(get_db)
):
    referral = (
        db.query(Referral)
        .filter(
            Referral.referral_id == referral_id,
            Referral.referring_facility_id == facility_id
        )
        .with_for_update()
        .first()
    )

    if not referral:
        raise HTTPException(
            status_code=404,
            detail="Referral not found in this facility."
        )

    try:
        referral = issue_referral(
            db=db,
            referral=referral,
            changed_by=current_user.user_id,
            change_reason=status_data.change_reason
        )

        db.commit()
        db.refresh(referral)

    except ValueError as e:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail=str(e)
        )

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to issue referral."
        )

    return {
        "message": "Referral issued successfully.",
        "referral_id": referral.referral_id,
        "referral_status": referral.referral_status
    }

@router.post("/{referral_id}/send")
def send_care_referral(
    referral_id: int,
    handoff_data: HandoffSend,
    facility_id: int,
    current_user: User = Depends(
        require_permission("MANAGE_REFERRALS")
    ),
    db: Session = Depends(get_db)
):
    referral = (
        db.query(Referral)
        .filter(
            Referral.referral_id == referral_id,
            Referral.referring_facility_id == facility_id
        )
        .with_for_update()
        .first()
    )

    if not referral:
        raise HTTPException(
            status_code=404,
            detail="Referral not found in this facility."
        )

    try:
        handoff = send_referral_handoff(
            db=db,
            referral=referral,
            sender_user_id=current_user.user_id,
            event_notes=handoff_data.event_notes,
            external_reference=handoff_data.external_reference
        )

        db.commit()
        db.refresh(handoff)

    except ValueError as e:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail=str(e)
        )

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A database constraint prevented the handoff."
        )

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to send referral handoff."
        )

    return {
        "message": "Referral handoff sent successfully.",
        "handoff_id": handoff.handoff_id,
        "referral_id": handoff.referral_id,
        "sending_facility_id": handoff.sending_facility_id,
        "receiving_facility_id": handoff.receiving_facility_id,
        "handoff_status": handoff.handoff_status,
        "referral_status": referral.referral_status
    }

@router.post("/handoffs/{handoff_id}/receive")
def receive_care_handoff(
    handoff_id: int,
    handoff_data: HandoffReceive,
    facility_id: int,
    current_user: User = Depends(
        require_permission("MANAGE_REFERRALS")
    ),
    db: Session = Depends(get_db)
):
    handoff = (
        db.query(Handoff)
        .filter(
            Handoff.handoff_id == handoff_id,
            Handoff.receiving_facility_id == facility_id
        )
        .with_for_update()
        .first()
    )

    if not handoff:
        raise HTTPException(
            status_code=404,
            detail="Handoff not found in this facility."
        )

    try:
        handoff = receive_referral_handoff(
            db=db,
            handoff=handoff,
            receiver_user_id=current_user.user_id,
            event_notes=handoff_data.event_notes,
            external_reference=handoff_data.external_reference
        )

        db.commit()
        db.refresh(handoff)

    except ValueError as e:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail=str(e)
        )

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A database constraint prevented handoff receipt."
        )

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to record handoff receipt."
        )

    return {
        "message": "Handoff received successfully.",
        "handoff_id": handoff.handoff_id,
        "referral_id": handoff.referral_id,
        "receiving_facility_id": handoff.receiving_facility_id,
        "handoff_status": handoff.handoff_status,
        "referral_status": "ACKNOWLEDGED"
    }


@router.post("/handoffs/{handoff_id}/decision")
def decide_care_handoff(
    handoff_id: int,
    handoff_data: HandoffDecision,
    facility_id: int,
    current_user: User = Depends(require_permission("MANAGE_REFERRALS")),
    db: Session = Depends(get_db)
):
    handoff = (
        db.query(Handoff)
        .filter(
            Handoff.handoff_id == handoff_id,
            Handoff.receiving_facility_id == facility_id
        )
        .with_for_update()
        .first()
    )

    if not handoff:
        raise HTTPException(
            status_code=404,
            detail="Handoff not found at this facility."
        )

    try:
        handoff = decide_referral_handoff(
            db=db,
            handoff=handoff,
            receiver_user_id=current_user.user_id,
            decision=handoff_data.decision,
            decision_reason=handoff_data.decision_reason
        )

        db.commit()
        db.refresh(handoff)

    except ValueError as e:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail=str(e)
        )

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A database conflict occurred while processing the decision."
        )

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="A database error occurred while processing the decision."
        )

    return {
        "message": f"Handoff {handoff.handoff_status.lower()} successfully.",
        "handoff_id": handoff.handoff_id,
        "referral_id": handoff.referral_id,
        "receiving_facility_id": handoff.receiving_facility_id,
        "handoff_status": handoff.handoff_status,
        "referral_status": handoff_data.decision
    }


@router.post("/{referral_id}/consultations", status_code=201)
def create_referral_consultation(
    referral_id: int,
    consultation_data: ConsultationCreate,
    facility_id: int,
    current_user: User = Depends(
        require_permission("MANAGE_CONSULTATIONS")
    ),
    db: Session = Depends(get_db)
):
    referral = (
        db.query(Referral)
        .filter(
            Referral.referral_id == referral_id,
            Referral.receiving_facility_id == facility_id
        )
        .with_for_update()
        .first()
    )

    if not referral:
        raise HTTPException(
            status_code=404,
            detail="Referral not found at this facility."
        )

    try:
        consultation = create_consultation(
            db=db,
            referral=referral,
            clinician_user_id=current_user.user_id,
            facility_id=facility_id,
            consultation_type=consultation_data.consultation_type,
            consultation_channel=consultation_data.consultation_channel,
            scheduled_at=consultation_data.scheduled_at
        )

        db.commit()
        db.refresh(consultation)

    except ValueError as e:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail=str(e)
        )

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A database conflict occurred while creating the consultation."
        )

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="A database error occurred while creating the consultation."
        )

    return {
        "message": "Consultation created successfully.",
        "consultation_id": consultation.consultation_id,
        "referral_id": referral.referral_id,
        "case_id": consultation.case_id,
        "facility_id": consultation.facility_id,
        "clinician_id": consultation.clinician_id,
        "consultation_type": consultation.consultation_type,
        "consultation_channel": consultation.consultation_channel,
        "consultation_status": consultation.consultation_status,
        "scheduled_at": consultation.scheduled_at
    }


@router.patch("/consultations/{consultation_id}/schedule")
def schedule_referral_consultation(
    consultation_id: int,
    schedule_data: ConsultationSchedule,
    facility_id: int,
    current_user: User = Depends(
        require_permission("MANAGE_CONSULTATIONS")
    ),
    db: Session = Depends(get_db)
):
    consultation = (
        db.query(Consultation)
        .filter(
            Consultation.consultation_id == consultation_id,
            Consultation.facility_id == facility_id
        )
        .with_for_update()
        .first()
    )

    if not consultation:
        raise HTTPException(
            status_code=404,
            detail="Consultation not found at this facility."
        )

    try:
        consultation = schedule_consultation(
            db=db,
            consultation=consultation,
            clinician_user_id=current_user.user_id,
            scheduled_at=schedule_data.scheduled_at
        )

        db.commit()
        db.refresh(consultation)

    except ValueError as e:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail=str(e)
        )

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A database conflict occurred while scheduling the consultation."
        )

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="A database error occurred while scheduling the consultation."
        )

    return {
        "message": "Consultation scheduled successfully.",
        "consultation_id": consultation.consultation_id,
        "facility_id": consultation.facility_id,
        "consultation_status": consultation.consultation_status,
        "scheduled_at": consultation.scheduled_at
    }


@router.patch("/consultations/{consultation_id}/start")
def start_referral_consultation(
    consultation_id: int,
    facility_id: int,
    current_user: User = Depends(
        require_permission("MANAGE_CONSULTATIONS")
    ),
    db: Session = Depends(get_db)
):
    consultation = (
        db.query(Consultation)
        .filter(
            Consultation.consultation_id == consultation_id,
            Consultation.facility_id == facility_id
        )
        .with_for_update()
        .first()
    )

    if not consultation:
        raise HTTPException(
            status_code=404,
            detail="Consultation not found at this facility."
        )

    try:
        consultation = start_consultation(
            db=db,
            consultation=consultation,
            clinician_user_id=current_user.user_id
        )

        db.commit()
        db.refresh(consultation)

    except ValueError as e:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail=str(e)
        )

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A database conflict occurred while starting the consultation."
        )

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="A database error occurred while starting the consultation."
        )

    return {
        "message": "Consultation started successfully.",
        "consultation_id": consultation.consultation_id,
        "facility_id": consultation.facility_id,
        "consultation_status": consultation.consultation_status,
        "started_at": consultation.started_at
    }


@router.patch("/consultations/{consultation_id}/complete")
def complete_referral_consultation(
    consultation_id: int,
    completion_data: ConsultationCompletion,
    facility_id: int,
    current_user: User = Depends(
        require_permission("MANAGE_CONSULTATIONS")
    ),
    db: Session = Depends(get_db)
):
    consultation = (
        db.query(Consultation)
        .filter(
            Consultation.consultation_id == consultation_id,
            Consultation.facility_id == facility_id
        )
        .with_for_update()
        .first()
    )

    if not consultation:
        raise HTTPException(
            status_code=404,
            detail="Consultation not found at this facility."
        )

    try:
        consultation = complete_consultation(
            db=db,
            consultation=consultation,
            clinician_user_id=current_user.user_id,
            outcome_summary=completion_data.outcome_summary,
            follow_up_required=completion_data.follow_up_required
        )

        db.commit()
        db.refresh(consultation)

    except ValueError as e:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail=str(e)
        )

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A database conflict occurred while completing the consultation."
        )

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="A database error occurred while completing the consultation."
        )

    return {
        "message": "Consultation completed successfully.",
        "consultation_id": consultation.consultation_id,
        "facility_id": consultation.facility_id,
        "consultation_status": consultation.consultation_status,
        "completed_at": consultation.completed_at,
        "follow_up_required": consultation.follow_up_required
    }
