from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from app.database.connection import get_db
from app.models.care_case import CareCase
from app.models.task import Task
from app.models.case_assignment import CaseAssignment
from app.models.facility_user import FacilityUser
from app.models.role import Role
from app.models.user import User
from app.models.patient import Patient
from app.models.screening_result import ScreeningResult
from app.models.escalation import Escalation
from app.models.risk_assessment import RiskAssessment
from app.models.intervention_recommendation import InterventionRecommendation
from app.core.dependencies import require_permission
from app.schemas.dashboard import (
    DashboardSummary,
    DashboardCaseItem,
    DashboardInterventionItem,
    CareCoordinationDashboardResponse,
)


router = APIRouter(
    prefix="/api/v1/dashboard",
    tags=["Dashboard"]
)

@router.get(
    "/care-coordination",
    response_model=CareCoordinationDashboardResponse
)
def get_care_coordination_dashboard(
    facility_id: int,
    current_user: User = Depends(
        require_permission("VIEW_ANALYTICS")
    ),
    db: Session = Depends(get_db)
):
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    active_statuses = [
        "OPEN",
        "IN_PROGRESS",
        "AWAITING_PATIENT",
        "AWAITING_FACILITY",
        "AWAITING_TEST",
        "AWAITING_APPOINTMENT",
        "UNDER_TREATMENT",
        "UNDER_SURVEILLANCE"
    ]

    try:
        # 1. Count active cases at this facility.
        active_cases = db.query(func.count(CareCase.case_id)).filter(
            CareCase.coordinating_facility_id == facility_id,
            CareCase.case_status.in_(active_statuses)
        ).scalar() or 0

        # 2. Count overdue pending or in-progress tasks.
        overdue_tasks = db.query(func.count(Task.task_id)).join(
            CareCase,
            Task.case_id == CareCase.case_id
        ).filter(
            CareCase.coordinating_facility_id == facility_id,
            Task.task_status.in_(["PENDING", "IN_PROGRESS"]),
            Task.due_at.isnot(None),
            Task.due_at < now
        ).scalar() or 0

        # 3. Count active cases without a current owner.
        current_assignments = db.query(
            CaseAssignment.case_id
        ).join(
            CareCase,
            CaseAssignment.case_id == CareCase.case_id
        ).filter(
            CareCase.coordinating_facility_id == facility_id,
            CaseAssignment.is_current.is_(True)
        ).subquery()

        unassigned_cases = db.query(
            func.count(CareCase.case_id)
        ).filter(
            CareCase.coordinating_facility_id == facility_id,
            CareCase.case_status.in_(active_statuses),
            ~CareCase.case_id.in_(
                db.query(current_assignments.c.case_id)
            )
        ).scalar() or 0

        # 4. Count open escalations.
        open_escalations = db.query(
            func.count(Escalation.escalation_id)
        ).join(
            CareCase,
            Escalation.case_id == CareCase.case_id
        ).filter(
            CareCase.coordinating_facility_id == facility_id,
            Escalation.escalation_status.in_(
                ["OPEN", "ACKNOWLEDGED", "IN_PROGRESS"]
            )
        ).scalar() or 0

        # 5. Count intervention recommendations by status.
        recommendations_pending_review = db.query(
            func.count(InterventionRecommendation.recommendation_id)
        ).join(
            CareCase,
            InterventionRecommendation.case_id == CareCase.case_id
        ).filter(
            CareCase.coordinating_facility_id == facility_id,
            InterventionRecommendation.recommendation_status == "PENDING_REVIEW"
        ).scalar() or 0

        recommendations_approved = db.query(
            func.count(InterventionRecommendation.recommendation_id)
        ).join(
            CareCase,
            InterventionRecommendation.case_id == CareCase.case_id
        ).filter(
            CareCase.coordinating_facility_id == facility_id,
            InterventionRecommendation.recommendation_status == "APPROVED"
        ).scalar() or 0

        recommendations_implemented = db.query(
            func.count(InterventionRecommendation.recommendation_id)
        ).join(
            CareCase,
            InterventionRecommendation.case_id == CareCase.case_id
        ).filter(
            CareCase.coordinating_facility_id == facility_id,
            InterventionRecommendation.recommendation_status == "IMPLEMENTED"
        ).scalar() or 0

        recommendations_rejected = db.query(
            func.count(InterventionRecommendation.recommendation_id)
        ).join(
            CareCase,
            InterventionRecommendation.case_id == CareCase.case_id
        ).filter(
            CareCase.coordinating_facility_id == facility_id,
            InterventionRecommendation.recommendation_status == "REJECTED"
        ).scalar() or 0

        summary = DashboardSummary(
            active_cases=active_cases,
            overdue_tasks=overdue_tasks,
            unassigned_cases=unassigned_cases,
            open_escalations=open_escalations,
            recommendations_pending_review=recommendations_pending_review,
            recommendations_approved=recommendations_approved,
            recommendations_implemented=recommendations_implemented,
            recommendations_rejected=recommendations_rejected
        )

                # 5. Retrieve active cases and their screening information.
        case_records = db.query(
            CareCase,
            Patient.public_id,
            ScreeningResult.test_name,
            ScreeningResult.result_classification,
            ScreeningResult.clinical_urgency
        ).join(
            Patient,
            CareCase.patient_id == Patient.patient_id
        ).join(
            ScreeningResult,
            CareCase.result_id == ScreeningResult.result_id
        ).filter(
            CareCase.coordinating_facility_id == facility_id,
            CareCase.case_status.in_(active_statuses)
        ).order_by(
            CareCase.opened_at.desc()
        ).all()

        case_items = []

        for care_case, patient_reference, test_name, classification, urgency in case_records:

            # Find the current active case owner.
            owner = db.query(
                User.first_name,
                User.last_name
            ).join(
                FacilityUser,
                User.user_id == FacilityUser.user_id
            ).join(
                CaseAssignment,
                FacilityUser.facility_user_id == CaseAssignment.facility_user_id
            ).filter(
                CaseAssignment.case_id == care_case.case_id,
                CaseAssignment.is_current.is_(True),
                FacilityUser.facility_id == facility_id,
                FacilityUser.employment_status == "ACTIVE",
                User.is_active.is_(True)
            ).first()

            current_owner = (
                f"{owner.first_name} {owner.last_name}"
                if owner else None
            )

            # Find the next pending or in-progress task.
            next_task = db.query(Task).filter(
                Task.case_id == care_case.case_id,
                Task.task_status.in_(["PENDING", "IN_PROGRESS"])
            ).order_by(
                Task.due_at.is_(None).asc(),
                Task.due_at.asc(),
                Task.created_at.asc()
            ).first()

            task_title = next_task.title if next_task else None
            task_due_at = next_task.due_at if next_task else None

             # Count all outstanding tasks for this case.
            pending_tasks_count = db.query(
                func.count(Task.task_id)
            ).filter(
                Task.case_id == care_case.case_id,
                Task.task_status.in_(["PENDING", "IN_PROGRESS"])
            ).scalar() or 0

            # Count outstanding tasks whose deadlines have passed.
            overdue_tasks_count = db.query(
                func.count(Task.task_id)
            ).filter(
                Task.case_id == care_case.case_id,
                Task.task_status.in_(["PENDING", "IN_PROGRESS"]),
                Task.due_at.isnot(None),
                Task.due_at < now
            ).scalar() or 0

            is_overdue = bool(
                next_task
                and next_task.task_status in ["PENDING", "IN_PROGRESS"]
                and task_due_at
                and task_due_at < now
            )

            # Retrieve the latest saved risk assessment for this case.
            baseline_risk = db.query(RiskAssessment).filter(
                RiskAssessment.case_id == care_case.case_id,
                RiskAssessment.model_name == "AHENDA_RULE_BASED_BASELINE"
            ).order_by(
                RiskAssessment.assessed_at.desc(),
                RiskAssessment.assessment_id.desc()
            ).first()

            ml_risk = db.query(RiskAssessment).filter(
                RiskAssessment.case_id == care_case.case_id,
                RiskAssessment.model_name == "AHENDA_RANDOM_FOREST_DROPOFF"
            ).order_by(
                RiskAssessment.assessed_at.desc(),
                RiskAssessment.assessment_id.desc()
            ).first()

            # Retrieve intervention recommendations for this case.
            recommendations = db.query(
                InterventionRecommendation
            ).filter(
                InterventionRecommendation.case_id == care_case.case_id
            ).order_by(
                InterventionRecommendation.created_at.desc()
            ).all()

            intervention_items = [
                DashboardInterventionItem(
                    recommendation_id=item.recommendation_id,
                    recommendation_type=item.recommendation_type,
                    recommendation=item.recommendation,
                    recommendation_status=item.recommendation_status,
                    created_at=item.created_at,
                    reviewed_at=item.reviewed_at,
                    executed_at=item.executed_at
                )
                for item in recommendations
            ]

            case_items.append(
                DashboardCaseItem(
                    case_id=care_case.case_id,
                    patient_reference=patient_reference,
                    test_name=test_name,
                    result_classification=classification,
                    clinical_urgency=urgency,
                    case_status=care_case.case_status,
                    case_priority=care_case.priority,
                    current_owner=current_owner,
                    next_task=task_title,
                    task_due_at=task_due_at,
                    pending_tasks_count=pending_tasks_count,
                    overdue_tasks_count=overdue_tasks_count,
                    is_overdue=is_overdue,
                    # Rule-based baseline assessment
                    risk_score=float(baseline_risk.risk_score) if baseline_risk else None,
                    risk_level=baseline_risk.risk_level if baseline_risk else None,
                    contributing_factors=baseline_risk.contributing_factors if baseline_risk else None,
                    risk_assessed_at=baseline_risk.assessed_at if baseline_risk else None,
                    # Random Forest ML assessment
                    ml_risk_score=float(ml_risk.risk_score) if ml_risk else None,
                    ml_risk_level=ml_risk.risk_level if ml_risk else None,
                    ml_contributing_factors=ml_risk.contributing_factors if ml_risk else None,
                    ml_risk_assessed_at=ml_risk.assessed_at if ml_risk else None,
                    ml_training_data="SYNTHETIC" if ml_risk else None,
                    ml_clinical_validation=False if ml_risk else None,
                    intervention_recommendations=intervention_items
                )
            )

        return CareCoordinationDashboardResponse(
            summary=summary,
            cases=case_items
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to load the care coordination dashboard."
        )