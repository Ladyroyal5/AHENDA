
from uuid import uuid4
from sqlalchemy.orm import Session
from app.models.risk_assessment import RiskAssessment


def calculate_dropoff_risk(features: dict) -> dict:
    """
    Calculate a transparent, rule-based care coordination
    drop-off risk score.

    This is an operational baseline, not a clinically
    validated machine-learning prediction.
    """

    score = 0
    contributing_factors = []

    def add_risk(points: int, reason: str):
        nonlocal score
        score += points
        contributing_factors.append({
            "factor": reason,
            "points": points
        })

    # Overdue tasks
    if features.get("overdue_tasks", 0) > 0:
        add_risk(20, "Overdue tasks")

    # Unassigned tasks
    if features.get("unassigned_tasks", 0) > 0:
        add_risk(15, "Unassigned tasks")

    # Failed notifications
    if features.get("failed_notifications", 0) > 0:
        add_risk(15, "Failed patient notifications")

    # Patient communication difficulties
    if features.get("unable_to_respond_acknowledgements", 0) > 0:
        add_risk(15, "Patient unable to respond")

    if features.get("needs_clarification_acknowledgements", 0) > 0:
        add_risk(10, "Patient needs clarification")

    # Missed appointments
    if features.get("no_show_appointments", 0) > 0:
        add_risk(15, "Missed appointments")

    # Rejected referrals
    if features.get("rejected_referrals", 0) > 0:
        add_risk(15, "Rejected referrals")

    # Pending referrals
    if features.get("pending_referrals", 0) > 0:
        add_risk(10, "Pending referrals")

    # Time spent in the current status
    if features.get("status_history_matches_current_status") is True:
        days = features.get("days_in_current_status")

        if days is not None:
            if days >= 7:
                add_risk(20, "Case stuck in current status for 7+ days")
            elif days >= 5:
                add_risk(15, "Case stuck in current status for 5–6 days")
            elif days >= 3:
                add_risk(10, "Case stuck in current status for 3–4 days")

    # Cap score at 100
    score = min(score, 100)

    # Determine risk level
    if score >= 75:
        risk_level = "CRITICAL"
    elif score >= 50:
        risk_level = "HIGH"
    elif score >= 25:
        risk_level = "MODERATE"
    else:
        risk_level = "LOW"

    return {
        "risk_score": round(score / 100, 5),
        "risk_level": risk_level,
        "contributing_factors": contributing_factors,
        "model_name": "AHENDA_RULE_BASED_BASELINE",
        "model_version": "1.0"
    }

def save_risk_assessment(
    db: Session,
    case_id: int,
    features: dict,
    commit: bool = True
):
    """
    Calculate and save a care coordination risk assessment.
    """

    risk_result = calculate_dropoff_risk(features)

    assessment = RiskAssessment(
        public_id=str(uuid4()),
        case_id=case_id,
        model_name=risk_result["model_name"],
        model_version=risk_result["model_version"],
        risk_score=risk_result["risk_score"],
        risk_level=risk_result["risk_level"],
        contributing_factors=risk_result["contributing_factors"],
        feature_snapshot=features
    )

    try:
        db.add(assessment)

        if commit:
            db.commit()
            db.refresh(assessment)
        else:
            db.flush()

        return assessment

    except Exception:
        db.rollback()
        raise