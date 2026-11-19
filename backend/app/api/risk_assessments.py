from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.core.dependencies import require_permission

from app.models.care_case import CareCase
from app.models.risk_assessment import RiskAssessment
from app.ai.features import extract_all_case_features
from app.ai.risk_scoring import save_risk_assessment
from app.ai.dropoff_prediction import save_ml_risk_assessment
from app.ai.interventions import save_intervention_recommendations


router = APIRouter(
    prefix="/api/v1/risk-assessments",
    tags=["Risk Assessments"]
)


@router.post(
    "/cases/{case_id}/assess",
    status_code=status.HTTP_201_CREATED
)

def create_risk_assessment(
    case_id: int,
    facility_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission("MANAGE_CARE_CASES")
    )
):
    # 1. Find the care case
    case = db.query(CareCase).filter(
        CareCase.case_id == case_id
    ).first()

    if case is None:
        raise HTTPException(
            status_code=404,
            detail="Care case not found."
        )

    # 2. Verify coordinating facility
    if case.coordinating_facility_id != facility_id:
        raise HTTPException(
            status_code=403,
            detail="Only the coordinating facility can assess this case."
        )

    # 3. Reject inactive cases
    if case.case_status in ["CLOSED", "TRANSFERRED", "CANCELLED"]:
        raise HTTPException(
            status_code=400,
            detail="Cannot assess an inactive care case."
        )

    # 4. Extract operational features
    features = extract_all_case_features(
        db=db,
        case_id=case_id
    )

    try:
        # 5. Save rule-based baseline
        baseline_assessment = save_risk_assessment(
            db=db,
            case_id=case_id,
            features=features,
            commit=False
        )

        # 6. Save Random Forest assessment
        ml_assessment = save_ml_risk_assessment(
            db=db,
            case_id=case_id,
            features=features,
            commit=False
        )

        # 7. Generate recommendations
        recommendations = save_intervention_recommendations(
            db=db,
            assessment_id=baseline_assessment.assessment_id,
            features=features,
            commit=False
        )

        # 8. Commit all three together
        db.commit()

        db.refresh(baseline_assessment)
        db.refresh(ml_assessment)

        for item in recommendations:
            db.refresh(item)

    except Exception:
        db.rollback()
        raise

    # 9. Return assessments and recommendations
    return {
        "message": "Both risk assessments and intervention recommendations created successfully.",
        "assessments": {
            "rule_based_baseline": {
                "assessment_id": baseline_assessment.assessment_id,
                "public_id": baseline_assessment.public_id,
                "risk_score": float(baseline_assessment.risk_score),
                "risk_level": baseline_assessment.risk_level,
                "contributing_factors": baseline_assessment.contributing_factors,
                "model_name": baseline_assessment.model_name,
                "model_version": baseline_assessment.model_version,
                "assessed_at": baseline_assessment.assessed_at
            },
            "random_forest": {
                "assessment_id": ml_assessment.assessment_id,
                "public_id": ml_assessment.public_id,
                "risk_score": float(ml_assessment.risk_score),
                "risk_level": ml_assessment.risk_level,
                "contributing_factors": ml_assessment.contributing_factors,
                "model_name": ml_assessment.model_name,
                "model_version": ml_assessment.model_version,
                "training_data": "SYNTHETIC",
                "clinical_validation": False,
                "assessed_at": ml_assessment.assessed_at
            }
        },
        "intervention_recommendations": {
            "total": len(recommendations),
            "status": "PENDING_REVIEW",
            "items": [
                {
                    "recommendation_id": item.recommendation_id,
                    "recommendation_type": item.recommendation_type,
                    "recommendation": item.recommendation
                }
                for item in recommendations
            ]
        }
    }



@router.get("/cases/{case_id}/history")
def get_risk_assessment_history(
    case_id: int,
    facility_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission("MANAGE_CARE_CASES")
    )
):
    # Find the care case
    case = db.query(CareCase).filter(
        CareCase.case_id == case_id
    ).first()

    if case is None:
        raise HTTPException(
            status_code=404,
            detail="Care case not found."
        )

    # Verify coordinating facility
    if case.coordinating_facility_id != facility_id:
        raise HTTPException(
            status_code=403,
            detail="Only the coordinating facility can view this history."
        )

    # Retrieve previous assessments
    assessments = (
        db.query(RiskAssessment)
        .filter(RiskAssessment.case_id == case_id)
        .order_by(
            RiskAssessment.assessed_at.desc(),
            RiskAssessment.assessment_id.desc()
        )
        .all()
    )

    return {
        "case_id": case_id,
        "total_assessments": len(assessments),
        "assessments": [
            {
                "assessment_id": item.assessment_id,
                "public_id": item.public_id,
                "risk_score": float(item.risk_score),
                "risk_level": item.risk_level,
                "contributing_factors": item.contributing_factors,
                "model_name": item.model_name,
                "model_version": item.model_version,
                "assessed_at": item.assessed_at
            }
            for item in assessments
        ]
    }

@router.get("/facility/latest")
def get_latest_facility_risk_assessments(
    facility_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permission("MANAGE_CARE_CASES")
    )
):
    # Find active care cases belonging to this facility
    cases = db.query(CareCase).filter(
        CareCase.coordinating_facility_id == facility_id,
        CareCase.case_status.notin_(
            ["CLOSED", "TRANSFERRED", "CANCELLED"]
        )
    ).all()

    case_ids = [case.case_id for case in cases]

    if not case_ids:
        return {
            "facility_id": facility_id,
            "total": 0,
            "assessments": []
        }

    # Retrieve risk assessments for these cases
    assessments = (
        db.query(RiskAssessment)
        .filter(RiskAssessment.case_id.in_(case_ids))
        .order_by(
            RiskAssessment.assessed_at.desc(),
            RiskAssessment.assessment_id.desc()
        )
        .all()
    )

    return {
        "facility_id": facility_id,
        "total": len(assessments),
        "assessments": [
            {
                "assessment_id": item.assessment_id,
                "case_id": item.case_id,
                "risk_score": float(item.risk_score),
                "risk_level": item.risk_level,
                "model_name": item.model_name,
                "model_version": item.model_version,
                "contributing_factors": item.contributing_factors,
                "assessed_at": item.assessed_at
            }
            for item in assessments
        ]
    }