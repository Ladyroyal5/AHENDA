
from uuid import uuid4
from sqlalchemy.orm import Session
from app.models.risk_assessment import RiskAssessment
from pathlib import Path
import joblib
import pandas as pd


MODEL_PATH = Path(__file__).with_name("dropoff_model.joblib")

_model_package = None


def load_dropoff_model():
    global _model_package

    if _model_package is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                "AHENDA drop-off prediction model has not been trained."
            )

        _model_package = joblib.load(MODEL_PATH)

    return _model_package


def prepare_prediction_input(features: dict) -> pd.DataFrame:
    package = load_dropoff_model()

    numeric_features = package["numeric_features"]
    categorical_features = package["categorical_features"]
    feature_columns = package["feature_columns"]

    row = {}

    for feature in numeric_features:
        value = features.get(feature, 0)

        if value is None:
            value = 0

        row[feature] = int(value) if isinstance(value, bool) else float(value)

    for feature in categorical_features:
        value = features.get(feature)

        if value is None:
            value = "UNKNOWN"

        row[feature] = str(value)

    return pd.DataFrame([row], columns=feature_columns)


def identify_operational_signals(features: dict) -> list:
    signals = []

    signal_rules = [
        ("overdue_tasks", "Overdue follow-up tasks"),
        ("unassigned_tasks", "Unassigned follow-up tasks"),
        ("failed_notifications", "Failed patient notifications"),
        ("unable_to_respond_acknowledgements", "Patient unable to respond"),
        ("needs_clarification_acknowledgements", "Patient needs clarification"),
        ("no_show_appointments", "Missed appointments"),
        ("rejected_referrals", "Rejected referrals"),
        ("pending_referrals", "Pending referrals"),
    ]

    for feature, description in signal_rules:
        if features.get(feature, 0) > 0:
            signals.append({
                "factor": description,
                "observed_value": features[feature]
            })

    days = features.get("days_in_current_status")

    if (
        features.get("status_history_matches_current_status") is True
        and days is not None
        and days >= 3
    ):
        signals.append({
            "factor": "Extended time in current case status",
            "observed_value": days
        })

    return signals


def predict_dropoff_risk(features: dict) -> dict:
    package = load_dropoff_model()
    model = package["pipeline"]

    input_data = prepare_prediction_input(features)
    probability = float(model.predict_proba(input_data)[0][1])

    if probability >= 0.75:
        risk_level = "CRITICAL"
    elif probability >= 0.50:
        risk_level = "HIGH"
    elif probability >= 0.25:
        risk_level = "MODERATE"
    else:
        risk_level = "LOW"

    return {
        "risk_score": round(probability, 5),
        "risk_level": risk_level,
        "contributing_factors": identify_operational_signals(features),
        "model_name": package["model_name"],
        "model_version": package["model_version"],
        "training_data": package["training_data"],
        "clinical_validation": package["clinical_validation"],
    }


def save_ml_risk_assessment(
    db: Session,
    case_id: int,
    features: dict,
    commit: bool = True
):
    """
    Generate and save a Random Forest drop-off risk assessment.

    This is a synthetic-data-trained operational prototype,
    not a clinically validated prediction.
    """

    risk_result = predict_dropoff_risk(features)

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

