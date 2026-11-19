from pydantic import BaseModel
from datetime import datetime


class DashboardSummary(BaseModel):
    active_cases: int
    overdue_tasks: int
    unassigned_cases: int
    open_escalations: int
    recommendations_pending_review: int
    recommendations_approved: int
    recommendations_implemented: int
    recommendations_rejected: int

class DashboardInterventionItem(BaseModel):
    recommendation_id: int
    recommendation_type: str
    recommendation: str
    recommendation_status: str
    created_at: datetime
    reviewed_at: datetime | None = None
    executed_at: datetime | None = None    


class DashboardCaseItem(BaseModel):
    case_id: int
    patient_reference: str
    test_name: str
    result_classification: str | None
    clinical_urgency: str | None
    case_status: str
    case_priority: str
    current_owner: str | None
    next_task: str | None
    task_due_at: datetime | None
    pending_tasks_count: int
    overdue_tasks_count: int
    is_overdue: bool
    risk_score: float | None = None
    risk_level: str | None = None
    contributing_factors: list[dict] | None = None
    risk_assessed_at: datetime | None = None
    intervention_recommendations: list[DashboardInterventionItem] = []
    ml_risk_score: float | None = None
    ml_risk_level: str | None = None
    ml_contributing_factors: list[dict] | None = None
    ml_risk_assessed_at: datetime | None = None
    ml_training_data: str | None = None
    ml_clinical_validation: bool | None = None


class CareCoordinationDashboardResponse(BaseModel):
    summary: DashboardSummary
    cases: list[DashboardCaseItem]