import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.task import Task
from app.models.escalation import Escalation
from app.models.care_case import CareCase
from app.models.case_assignment import CaseAssignment
from app.services.audit_service import record_audit_event
from app.models.facility_user import FacilityUser
from app.models.role import Role
from app.models.user import User


def map_task_priority_to_escalation_severity(
    task_priority: str
) -> str:

    severity_mapping = {
        "NORMAL": "LOW",
        "LOW": "MEDIUM",
        "HIGH": "HIGH",
        "URGENT": "CRITICAL"
    }

    severity = severity_mapping.get(task_priority)

    if severity is None:
        raise ValueError(
            f"Unsupported task priority: {task_priority}"
        )

    return severity

def find_active_care_coordinator(
    db: Session,
    facility_id: int
):
    coordinator = (
        db.query(FacilityUser)
        .join(
            Role,
            FacilityUser.role_id == Role.role_id
        )
        .join(
            User,
            FacilityUser.user_id == User.user_id
        )
        .filter(
            FacilityUser.facility_id == facility_id,
            FacilityUser.employment_status == "ACTIVE",
            User.is_active.is_(True),
            Role.role_name == "CARE_COORDINATOR"
        )
        .order_by(FacilityUser.facility_user_id.asc())
        .first()
    )

    return coordinator

def find_active_escalation_admins(
    db: Session,
    facility_id: int
):
    administrators = (
        db.query(FacilityUser)
        .join(
            Role,
            FacilityUser.role_id == Role.role_id
        )
        .join(
            User,
            FacilityUser.user_id == User.user_id
        )
        .filter(
            FacilityUser.facility_id == facility_id,
            FacilityUser.employment_status == "ACTIVE",
            User.is_active.is_(True),
            Role.role_name.in_([
                "FACILITY_ADMIN",
                "PLATFORM_ADMIN"
            ])
        )
        .order_by(FacilityUser.facility_user_id.asc())
        .all()
    )

    return administrators


def find_overdue_tasks(db: Session):
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    overdue_tasks = (
        db.query(Task)
        .filter(
            Task.due_at.isnot(None),
            Task.due_at < now,
            Task.task_status.in_(["PENDING", "IN_PROGRESS"])
        )
        .order_by(Task.due_at.asc())
        .all()
    )

    return overdue_tasks


def create_task_escalation(
    db: Session,
    task: Task
):
    existing_escalation = (
        db.query(Escalation)
        .filter(
            Escalation.task_id == task.task_id,
            Escalation.escalation_status.in_(
                ["OPEN", "ACKNOWLEDGED", "IN_PROGRESS"]
            )
        )
        .first()
    )

    if existing_escalation:
        return existing_escalation

    care_case = (
        db.query(CareCase)
        .filter(CareCase.case_id == task.case_id)
        .first()
    )

    if not care_case:
        raise ValueError(
            f"Care case not found for task {task.task_id}."
        )

    severity = map_task_priority_to_escalation_severity(
        task.priority
    )

    assigned_to = task.assigned_to
    assignment_source = "EXISTING_TASK_ASSIGNEE"
    administrators = []

    if not assigned_to:
        coordinator = find_active_care_coordinator(
            db=db,
            facility_id=care_case.coordinating_facility_id
        )

        if coordinator:
            assigned_to = coordinator.facility_user_id
            assignment_source = "CARE_COORDINATOR"

    administrators = []

    if not assigned_to:
        administrators = find_active_escalation_admins(
            db=db,
            facility_id=care_case.coordinating_facility_id
    )

    if administrators:
        assigned_to = administrators[0].facility_user_id
        assignment_source = "ADMIN_OVERSIGHT"
    else:
        assignment_source = "UNASSIGNED_ADMIN_FALLBACK"

    escalation = Escalation(
        public_id=str(uuid.uuid4()),
        case_id=task.case_id,
        task_id=task.task_id,
        assigned_to=assigned_to,
        triggered_by=None,
        escalation_type="OVERDUE_TASK",
        severity=severity,
        escalation_reason=(
            f"The task '{task.title}' passed its deadline "
            f"without being completed."
        ),
        escalation_status="OPEN"
    )

    db.add(escalation)
    db.flush()

    record_audit_event(
        db=db,
        actor_user_id=None,
        facility_id=care_case.coordinating_facility_id,
        action="TASK_ESCALATED",
        entity_type="ESCALATION",
        entity_id=str(escalation.escalation_id),
        new_values={
            "case_id": task.case_id,
            "task_id": task.task_id,
            "severity": severity,
            "assigned_to": assigned_to,
            "assignment_source": assignment_source,
            "administrator_fallback_count": len(administrators)
        }
    )

    return escalation


def process_overdue_tasks(db: Session):
    overdue_tasks = find_overdue_tasks(db)

    created_escalations = []

    for task in overdue_tasks:
        escalation = create_task_escalation(
            db=db,
            task=task
        )

        created_escalations.append(escalation)

    return created_escalations


def acknowledge_escalation(
    db: Session,
    escalation: Escalation,
    acknowledged_by: int
):
    if escalation.escalation_status != "OPEN":
        raise ValueError(
            "Only open escalations can be acknowledged."
        )

    escalation.escalation_status = "ACKNOWLEDGED"

    escalation.acknowledged_at = (
        datetime.now(timezone.utc).replace(tzinfo=None)
    )

    care_case = (
        db.query(CareCase)
        .filter(CareCase.case_id == escalation.case_id)
        .first()
    )

    record_audit_event(
        db=db,
        actor_user_id=acknowledged_by,
        facility_id=(
            care_case.coordinating_facility_id
            if care_case else None
        ),
        action="ESCALATION_ACKNOWLEDGED",
        entity_type="ESCALATION",
        entity_id=str(escalation.escalation_id),
        new_values={
            "escalation_status": "ACKNOWLEDGED",
            "acknowledged_by": acknowledged_by
        }
    )

    db.flush()

    return escalation

def resolve_escalation(
    db: Session,
    escalation: Escalation,
    resolved_by: int,
    resolution_notes: str
):
    if escalation.escalation_status not in [
        "ACKNOWLEDGED",
        "IN_PROGRESS"
    ]:
        raise ValueError(
            "Only acknowledged or in-progress escalations can be resolved."
        )

    escalation.escalation_status = "RESOLVED"

    escalation.resolved_at = (
        datetime.now(timezone.utc).replace(tzinfo=None)
    )

    escalation.resolution_notes = resolution_notes

    care_case = (
        db.query(CareCase)
        .filter(CareCase.case_id == escalation.case_id)
        .first()
    )

    record_audit_event(
        db=db,
        actor_user_id=resolved_by,
        facility_id=(
            care_case.coordinating_facility_id
            if care_case else None
        ),
        action="ESCALATION_RESOLVED",
        entity_type="ESCALATION",
        entity_id=str(escalation.escalation_id),
        new_values={
            "escalation_status": "RESOLVED",
            "resolved_by": resolved_by,
            "resolution_notes": resolution_notes
        }
    )

    db.flush()

    return escalation