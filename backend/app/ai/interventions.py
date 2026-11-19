from sqlalchemy.orm import Session

from app.models.intervention_recommendation import (
    InterventionRecommendation
)
from app.models.risk_assessment import RiskAssessment

def generate_intervention_suggestions(features: dict) -> list[dict]:
    """
    Generate care coordination intervention suggestions
    based on identified risk factors.
    """

    suggestions = []

    # 1. Overdue tasks
    if features.get("overdue_tasks", 0) > 0:
        suggestions.append({
            "recommendation_type": "OVERDUE_TASK_FOLLOW_UP",
            "recommendation": (
                "Review overdue tasks and prompt the assigned "
                "care coordinator to complete the outstanding actions."
            )
        })

    # 2. Unassigned tasks
    if features.get("unassigned_tasks", 0) > 0:
        suggestions.append({
            "recommendation_type": "TASK_ASSIGNMENT",
            "recommendation": (
                "Assign outstanding tasks to an eligible care "
                "coordinator or clinician."
            )
        })

    # 3. Failed notifications
    if features.get("failed_notifications", 0) > 0:
        suggestions.append({
            "recommendation_type": "COMMUNICATION_RETRY",
            "recommendation": (
                "Review failed patient notifications and consider "
                "an alternative approved communication channel."
            )
        })

    # 4. Patient needs clarification
    if features.get("needs_clarification_acknowledgements", 0) > 0:
        suggestions.append({
            "recommendation_type": "PATIENT_CLARIFICATION",
            "recommendation": (
                "Arrange follow-up communication to clarify the "
                "approved screening information and next steps."
            )
        })

    # 5. Patient unable to respond
    if features.get("unable_to_respond_acknowledgements", 0) > 0:
        suggestions.append({
            "recommendation_type": "PATIENT_CONTACT_FOLLOW_UP",
            "recommendation": (
                "Ask an authorised care coordinator to review "
                "the communication barrier and determine an "
                "appropriate follow-up approach."
            )
        })

    # 6. Missed appointments
    if features.get("no_show_appointments", 0) > 0:
        suggestions.append({
            "recommendation_type": "APPOINTMENT_RESCHEDULING",
            "recommendation": (
                "Contact the patient through an approved channel "
                "to establish whether the appointment should be rescheduled."
            )
        })

    # 7. Rejected referrals
    if features.get("rejected_referrals", 0) > 0:
        suggestions.append({
            "recommendation_type": "REFERRAL_REVIEW",
            "recommendation": (
                "Review the referral rejection reason and determine "
                "the appropriate next care-coordination action."
            )
        })

    # 8. Pending referrals
    if features.get("pending_referrals", 0) > 0:
        suggestions.append({
            "recommendation_type": "REFERRAL_FOLLOW_UP",
            "recommendation": (
                "Contact the receiving facility to establish "
                "the status of the outstanding referral."
            )
        })

    # 9. Prolonged status
    if (
        features.get("status_history_matches_current_status") is True
        and features.get("days_in_current_status") is not None
        and features["days_in_current_status"] >= 3
    ):
        suggestions.append({
            "recommendation_type": "CASE_DELAY_REVIEW",
            "recommendation": (
                "Review the case for delays and identify what is "
                "preventing progression to the next care milestone."
            )
        })

    return suggestions


def save_intervention_recommendations(
    db: Session,
    assessment_id: int,
    features: dict,
    commit: bool = True
):
    """
    Generate and save case-level intervention recommendations.

    Prevent duplicate active recommendations across different
    risk assessments while preserving recommendation history.
    """

    assessment = db.query(RiskAssessment).filter(
        RiskAssessment.assessment_id == assessment_id
    ).first()

    if assessment is None:
        raise ValueError("Risk assessment not found.")

    suggestions = generate_intervention_suggestions(features)

    try:
        for suggestion in suggestions:

            # Prevent duplicate active recommendations
            # across all assessments belonging to this case.
            existing = db.query(
                InterventionRecommendation
            ).filter(
                InterventionRecommendation.case_id
                == assessment.case_id,
                InterventionRecommendation.recommendation_type
                == suggestion["recommendation_type"],
                InterventionRecommendation.recommendation_status.in_(
                    ["PENDING_REVIEW", "APPROVED"]
                )
            ).first()

            if existing:
                continue

            recommendation = InterventionRecommendation(
                case_id=assessment.case_id,
                assessment_id=assessment_id,
                recommendation_type=suggestion["recommendation_type"],
                recommendation=suggestion["recommendation"],
                recommendation_status="PENDING_REVIEW"
            )

            db.add(recommendation)

        if commit:
            db.commit()
        else:
            db.flush()

        return db.query(
            InterventionRecommendation
        ).filter(
            InterventionRecommendation.assessment_id == assessment_id
        ).all()

    except Exception:
        db.rollback()
        raise
