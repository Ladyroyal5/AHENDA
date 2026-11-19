import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app.models.care_case import CareCase
from app.models.case_assignment import CaseAssignment
from app.models.case_status_history import CaseStatusHistory
from app.models.facility_user import FacilityUser
from app.models.role import Role
from app.models.task import Task
from app.models.screening_result import ScreeningResult
from app.services.audit_service import record_audit_event
from app.models.user import User
from app.models.case_closure import CaseClosure
from app.models.closure_evidence import ClosureEvidence


def map_clinical_urgency_to_case_priority(
    clinical_urgency: str
) -> str:

    priority_mapping = {
    "ROUTINE": "ROUTINE",
    "SOON": "LOW",
    "URGENT": "HIGH",
    "EMERGENCY": "URGENT"
    }

    priority = priority_mapping.get(clinical_urgency)

    if priority is None:
        raise ValueError(
            f"Unsupported clinical urgency: {clinical_urgency}"
        )

    return priority

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


def create_care_case(
    db: Session,
    screening_result: ScreeningResult,
    reviewed_by: int
):
    # Prevent duplicate care cases.
    existing_case = (
        db.query(CareCase)
        .filter(
            CareCase.result_id == screening_result.result_id
        )
        .first()
    )

    if existing_case:
        raise ValueError(
            "A care case already exists for this screening result."
        )

    # Determine case priority.
    case_priority = map_clinical_urgency_to_case_priority(
        screening_result.clinical_urgency
    )

    # Create the care case.
    care_case = CareCase(
        public_case_id=str(uuid.uuid4()),
        result_id=screening_result.result_id,
        patient_id=screening_result.patient_id,
        coordinating_facility_id=screening_result.facility_id,
        case_status="OPEN",
        priority=case_priority
    )

    db.add(care_case)
    db.flush()

    return care_case

def create_initial_case_history(
    db: Session,
    care_case: CareCase,
    changed_by: int
):
    history = CaseStatusHistory(
        case_id=care_case.case_id,
        previous_status=None,
        new_status="OPEN",
        changed_by=changed_by,
        change_reason="Actionable screening result triggered case creation."
    )

    db.add(history)
    db.flush()

    return history


def create_initial_follow_up_task(
    db: Session,
    care_case: CareCase,
    screening_result: ScreeningResult,
    reviewed_by: int,
    coordinator: FacilityUser | None
):
    task_priority_mapping = {
        "ROUTINE": "NORMAL",
        "SOON": "LOW",
        "URGENT": "HIGH",
        "EMERGENCY": "URGENT"
    }

    task = Task(
        public_id=str(uuid.uuid4()),
        case_id=care_case.case_id,
        assigned_to=(
            coordinator.facility_user_id
            if coordinator else None
        ),
        assigned_by=reviewed_by,
        task_type="PATIENT_CONTACT",
        title="Contact patient regarding screening result",
        description=(
            "Contact the patient to communicate the approved "
            "screening result information and explain the next steps."
        ),
        task_status="PENDING",
        priority=task_priority_mapping[
            screening_result.clinical_urgency
        ],
        due_at=(
            datetime.now(timezone.utc) + timedelta(hours=24)
        ).replace(tzinfo=None)
    )

    db.add(task)
    db.flush()

    return task


def create_case_assignment(
    db: Session,
    care_case: CareCase,
    coordinator: FacilityUser,
    assigned_by: int
):
    assignment = CaseAssignment(
        case_id=care_case.case_id,
        facility_user_id=coordinator.facility_user_id,
        assigned_by=assigned_by,
        assignment_reason=(
            "Initial care coordination assignment following "
            "an actionable screening result."
        ),
        is_current=True
    )

    db.add(assignment)
    db.flush()

    return assignment


def create_care_case_workflow(
    db: Session,
    screening_result: ScreeningResult,
    reviewed_by: int
):
    # 1. Create the care case.
    care_case = create_care_case(
        db=db,
        screening_result=screening_result,
        reviewed_by=reviewed_by
    )

    # 2. Find an active coordinator at the same facility.
    coordinator = find_active_care_coordinator(
        db=db,
        facility_id=screening_result.facility_id
    )

    # 3. Create an assignment if a coordinator is available.
    assignment = None

    if coordinator:
        assignment = create_case_assignment(
            db=db,
            care_case=care_case,
            coordinator=coordinator,
            assigned_by=reviewed_by
        )

    # 4. Create the initial follow-up task.
    task = create_initial_follow_up_task(
        db=db,
        care_case=care_case,
        screening_result=screening_result,
        reviewed_by=reviewed_by,
        coordinator=coordinator
    )

    # 5. Record the initial case history.
    history = create_initial_case_history(
        db=db,
        care_case=care_case,
        changed_by=reviewed_by
    )

    # 6. Record care-case creation in the audit log.
    record_audit_event(
        db=db,
        actor_user_id=reviewed_by,
        facility_id=screening_result.facility_id,
        action="CARE_CASE_CREATED",
        entity_type="CARE_CASE",
        entity_id=str(care_case.case_id),
        new_values={
            "result_id": screening_result.result_id,
            "case_status": "OPEN",
            "priority": care_case.priority
        }
    )

    # 7. Record task creation in the audit log.
    record_audit_event(
        db=db,
        actor_user_id=reviewed_by,
        facility_id=screening_result.facility_id,
        action="FOLLOW_UP_TASK_CREATED",
        entity_type="TASK",
        entity_id=str(task.task_id),
        new_values={
            "case_id": care_case.case_id,
            "task_type": task.task_type,
            "assigned_to": task.assigned_to,
            "priority": task.priority
        }
    )

    # 8. Record assignment or the need for assignment.
    if assignment:
        record_audit_event(
            db=db,
            actor_user_id=reviewed_by,
            facility_id=screening_result.facility_id,
            action="CASE_ASSIGNED",
            entity_type="CASE_ASSIGNMENT",
            entity_id=str(assignment.assignment_id),
            new_values={
                "case_id": care_case.case_id,
                "facility_user_id": coordinator.facility_user_id
            }
        )
    else:
        record_audit_event(
            db=db,
            actor_user_id=reviewed_by,
            facility_id=screening_result.facility_id,
            action="CARE_CASE_UNASSIGNED",
            entity_type="CARE_CASE",
            entity_id=str(care_case.case_id),
            new_values={
                "case_id": care_case.case_id,
                "reason": "No active care coordinator available."
            }
        )

    return {
        "care_case": care_case,
        "assignment": assignment,
        "task": task,
        "history": history
    }

def find_eligible_case_recipient(
    db: Session,
    facility_id: int,
    recipient_facility_user_id: int
):
    eligible_roles = [
        "CARE_COORDINATOR",
        "CLINICIAN"
    ]

    recipient = (
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
            FacilityUser.facility_user_id
            == recipient_facility_user_id,
            FacilityUser.facility_id == facility_id,
            FacilityUser.employment_status == "ACTIVE",
            User.is_active.is_(True),
            Role.role_name.in_(eligible_roles)
        )
        .first()
    )

    return recipient

def assign_existing_care_case(
    db: Session,
    care_case: CareCase,
    recipient: FacilityUser,
    assigned_by: int,
    assignment_reason: str
):
    existing_assignment = (
        db.query(CaseAssignment)
        .filter(
            CaseAssignment.case_id == care_case.case_id,
            CaseAssignment.is_current.is_(True)
        )
        .with_for_update()
        .first()
    )

    if existing_assignment:
        existing_assignment.is_current = False
        existing_assignment.ended_at = (
            datetime.now(timezone.utc).replace(tzinfo=None)
        )

    assignment = CaseAssignment(
        case_id=care_case.case_id,
        facility_user_id=recipient.facility_user_id,
        assigned_by=assigned_by,
        assignment_reason=assignment_reason,
        is_current=True
    )

    db.add(assignment)
    db.flush()

    pending_task = (
        db.query(Task)
        .filter(
            Task.case_id == care_case.case_id,
            Task.task_type == "PATIENT_CONTACT",
            Task.task_status == "PENDING"
        )
        .order_by(Task.task_id.asc())
        .with_for_update()
        .first()
    )

    if pending_task:
        pending_task.assigned_to = recipient.facility_user_id

    db.flush()

    return assignment


def transition_care_case_status(
    db: Session,
    care_case: CareCase,
    new_status: str,
    changed_by: int,
    change_reason: str
):
    allowed_transitions = {
        "OPEN": {
            "IN_PROGRESS",
            "AWAITING_PATIENT",
            "AWAITING_FACILITY"
        },
        "IN_PROGRESS": {
            "AWAITING_PATIENT",
            "AWAITING_FACILITY",
            "AWAITING_TEST",
            "AWAITING_APPOINTMENT",
            "UNDER_TREATMENT",
            "UNDER_SURVEILLANCE",
            "RESOLVED"
        },
        "AWAITING_PATIENT": {
            "IN_PROGRESS",
            "AWAITING_TEST",
            "AWAITING_APPOINTMENT"
        },
        "AWAITING_FACILITY": {
            "IN_PROGRESS",
            "AWAITING_TEST",
            "AWAITING_APPOINTMENT"
        },
        "AWAITING_TEST": {
            "IN_PROGRESS",
            "AWAITING_APPOINTMENT",
            "UNDER_TREATMENT"
        },
        "AWAITING_APPOINTMENT": {
            "IN_PROGRESS",
            "UNDER_TREATMENT"
        },
        "UNDER_TREATMENT": {
            "IN_PROGRESS",
            "UNDER_SURVEILLANCE",
            "RESOLVED"
        },
        "UNDER_SURVEILLANCE": {
            "IN_PROGRESS",
            "RESOLVED"
        }
    }

    previous_status = care_case.case_status

    if previous_status not in allowed_transitions:
        raise ValueError(
            f"Case status '{previous_status}' cannot be changed "
            "through the ordinary status-transition workflow."
        )

    if new_status not in allowed_transitions[previous_status]:
        raise ValueError(
            f"Transition from '{previous_status}' "
            f"to '{new_status}' is not permitted."
        )

    care_case.case_status = new_status

    if new_status == "RESOLVED":
        care_case.resolved_at = (
            datetime.now(timezone.utc).replace(tzinfo=None)
        )

    history = CaseStatusHistory(
        case_id=care_case.case_id,
        previous_status=previous_status,
        new_status=new_status,
        changed_by=changed_by,
        change_reason=change_reason
    )

    db.add(history)

    record_audit_event(
        db=db,
        actor_user_id=changed_by,
        facility_id=care_case.coordinating_facility_id,
        action="CARE_CASE_STATUS_CHANGED",
        entity_type="CARE_CASE",
        entity_id=str(care_case.case_id),
        old_values={
            "case_status": previous_status
        },
        new_values={
            "case_status": new_status,
            "change_reason": change_reason
        }
    )

    db.flush()

    return care_case


def close_care_case(
    db: Session,
    care_case: CareCase,
    closure_type: str,
    closure_reason: str,
    evidence_summary: str,
    authorised_by: int,
    authorised_facility_user_id: int
):
    previous_status = care_case.case_status

    if previous_status in {
        "CLOSED",
        "TRANSFERRED",
        "CANCELLED"
    }:
        raise ValueError(
            "This care case is already in a terminal status."
        )

    if closure_type == "TRANSFERRED":
        raise ValueError(
            "Case transfers must use the dedicated transfer workflow."
        )

    if closure_type == "CARE_COMPLETED":
        if previous_status != "RESOLVED":
            raise ValueError(
                "A case must be RESOLVED before it can be closed "
                "as CARE_COMPLETED."
            )

    closure = CaseClosure(
        public_id=str(uuid.uuid4()),
        case_id=care_case.case_id,
        closure_type=closure_type,
        closure_reason=closure_reason,
        evidence_summary=evidence_summary,
        authorised_by=authorised_facility_user_id
    )

    db.add(closure)
    db.flush()

    care_case.case_status = "CLOSED"
    care_case.closed_at = (
        datetime.now(timezone.utc).replace(tzinfo=None)
    )

    history = CaseStatusHistory(
        case_id=care_case.case_id,
        previous_status=previous_status,
        new_status="CLOSED",
        changed_by=authorised_by,
        change_reason=closure_reason
    )

    db.add(history)

    record_audit_event(
        db=db,
        actor_user_id=authorised_by,
        facility_id=care_case.coordinating_facility_id,
        action="CARE_CASE_CLOSED",
        entity_type="CARE_CASE",
        entity_id=str(care_case.case_id),
        old_values={
            "case_status": previous_status
        },
        new_values={
            "case_status": "CLOSED",
            "closure_type": closure_type,
            "closure_reason": closure_reason,
            "closure_id": closure.closure_id
        }
    )

    db.flush()

    return closure


