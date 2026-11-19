
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from openai import OpenAIError

from app.database.connection import get_db
from app.core.dependencies import get_current_user
from app.models.user import User, AccountType
from app.models.patient import Patient, PatientUserAccount
from app.ai.communication_assistant import generate_patient_response


router = APIRouter(
    prefix="/api/v1/communication",
    tags=["Patient Communication"]
)


class PatientMessage(BaseModel):
    message: str = Field(
        min_length=2,
        max_length=2000
    )


@router.post("/chat")
def patient_communication(
    request: PatientMessage,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Only patient accounts can use this endpoint.
    if current_user.account_type != AccountType.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is available only to patients."
        )

    # Resolve the patient from the authenticated account.
    account_link = db.query(PatientUserAccount).filter(
        PatientUserAccount.user_id == current_user.user_id,
        PatientUserAccount.account_status == "VERIFIED"
    ).first()

    if not account_link:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A verified patient account is required."
        )

    patient = db.query(Patient).filter(
        Patient.patient_id == account_link.patient_id,
        Patient.is_active.is_(True)
    ).first()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active patient record not found."
        )

    # No clinical information is passed until an approved,
    # access-controlled context retrieval service is implemented.
    approved_context = (
        "No patient-specific clinical information has been "
        "approved for this conversation. Do not invent "
        "screening results, appointments or referrals."
    )

    try:
        answer = generate_patient_response(
            patient_message=request.message,
            approved_context=approved_context
        )

        return {
            "message": "Response generated successfully.",
            "answer": answer
        }

    except OpenAIError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI assistant is temporarily unavailable."
        )
