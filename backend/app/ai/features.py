from datetime import datetime

from sqlalchemy.orm import Session

from app.models.care_case import CareCase
from app.models.task import Task
from app.models.referral import Referral
from app.models.appointment import Appointment
from app.models.notification import Notification
from app.models.acknowledgement import Acknowledgement
from app.models.case_status_history import CaseStatusHistory

def extract_task_features(db: Session, case_id: int) -> dict:
    """
    Extract task-related features for a care case.
    """

    tasks = db.query(Task).filter(
        Task.case_id == case_id
    ).all()

    now = datetime.now()

    pending_tasks = [
        task for task in tasks
        if task.task_status == "PENDING"
    ]

    in_progress_tasks = [
        task for task in tasks
        if task.task_status == "IN_PROGRESS"
    ]

    overdue_tasks = [
        task for task in tasks
        if task.due_at is not None
        and task.due_at < now
        and task.task_status not in ["COMPLETED", "CANCELLED"]
    ]

    unassigned_tasks = [
        task for task in tasks
        if task.assigned_to is None
        and task.task_status not in ["COMPLETED", "CANCELLED"]
    ]

    completed_tasks = [
        task for task in tasks
        if task.task_status == "COMPLETED"
    ]

    return {
        "total_tasks": len(tasks),
        "pending_tasks": len(pending_tasks),
        "in_progress_tasks": len(in_progress_tasks),
        "overdue_tasks": len(overdue_tasks),
        "unassigned_tasks": len(unassigned_tasks),
        "completed_tasks": len(completed_tasks)
    }

def extract_referral_features(db: Session, case_id: int) -> dict:
    """
    Extract referral-related features for a care case.
    """

    referrals = db.query(Referral).filter(
        Referral.case_id == case_id
    ).all()

    pending_referrals = [
        referral for referral in referrals
        if referral.referral_status in ["DRAFT", "ISSUED", "SENT"]
    ]

    accepted_referrals = [
        referral for referral in referrals
        if referral.referral_status == "ACCEPTED"
    ]

    unacknowledged_referrals = [
        referral for referral in referrals
        if referral.referral_status == "SENT"
    ]

    rejected_referrals = [
        referral for referral in referrals
        if referral.referral_status == "REJECTED"
    ]

    completed_referrals = [
        referral for referral in referrals
        if referral.referral_status == "COMPLETED"
    ]

    return {
        "total_referrals": len(referrals),
        "pending_referrals": len(pending_referrals),
        "unacknowledged_referrals": len(unacknowledged_referrals),
        "rejected_referrals": len(rejected_referrals),
        "completed_referrals": len(completed_referrals),
        "accepted_referrals": len(accepted_referrals)
    }    


def extract_appointment_features(db: Session, case_id: int) -> dict:
    """
    Extract appointment-related features for a care case.
    """

    appointments = db.query(Appointment).filter(
        Appointment.case_id == case_id
    ).all()

    no_show_appointments = [
        appointment for appointment in appointments
        if appointment.appointment_status == "NO_SHOW"
    ]

    cancelled_appointments = [
        appointment for appointment in appointments
        if appointment.appointment_status == "CANCELLED"
    ]

    attended_appointments = [
        appointment for appointment in appointments
        if appointment.appointment_status == "ATTENDED"
    ]

    scheduled_appointments = [
        appointment for appointment in appointments
        if appointment.appointment_status in ["REQUESTED", "SCHEDULED", "CONFIRMED"]
    ]

    return {
        "total_appointments": len(appointments),
        "no_show_appointments": len(no_show_appointments),
        "cancelled_appointments": len(cancelled_appointments),
        "attended_appointments": len(attended_appointments),
        "scheduled_appointments": len(scheduled_appointments)
    }  

def extract_notification_features(db: Session, case_id: int) -> dict:
    """
    Extract notification-related features for a care case.
    """

    notifications = db.query(Notification).filter(
        Notification.case_id == case_id
    ).all()

    failed_notifications = [
        notification for notification in notifications
        if notification.delivery_status == "FAILED"
    ]

    delivered_notifications = [
        notification for notification in notifications
        if notification.delivery_status == "DELIVERED"
    ]

    pending_notifications = [
        notification for notification in notifications
        if notification.delivery_status == "PENDING"
    ]

    sent_notifications = [
        notification for notification in notifications
        if notification.delivery_status == "SENT"
    ]

    return {
        "total_notifications": len(notifications),
        "failed_notifications": len(failed_notifications),
        "delivered_notifications": len(delivered_notifications),
        "pending_notifications": len(pending_notifications),
        "sent_notifications": len(sent_notifications)
    }    

def extract_acknowledgement_features(db: Session, case_id: int) -> dict:
    """
    Extract patient acknowledgement features for a care case.
    """

    acknowledgements = (
        db.query(Acknowledgement)
        .join(
            Notification,
            Acknowledgement.notification_id == Notification.notification_id
        )
        .filter(Notification.case_id == case_id)
        .all()
    )

    understood = [
        item for item in acknowledgements
        if item.acknowledgement_status == "UNDERSTOOD"
    ]

    needs_clarification = [
        item for item in acknowledgements
        if item.acknowledgement_status == "NEEDS_CLARIFICATION"
    ]

    unable_to_respond = [
        item for item in acknowledgements
        if item.acknowledgement_status == "UNABLE_TO_RESPOND"
    ]

    received = [
        item for item in acknowledgements
        if item.acknowledgement_status == "RECEIVED"
    ]

    return {
        "total_acknowledgements": len(acknowledgements),
        "understood_acknowledgements": len(understood),
        "needs_clarification_acknowledgements": len(needs_clarification),
        "unable_to_respond_acknowledgements": len(unable_to_respond),
        "received_acknowledgements": len(received)
    }

def extract_case_features(db: Session, case_id: int) -> dict:
    """
    Extract general care-case features.
    """

    case = db.query(CareCase).filter(
        CareCase.case_id == case_id
    ).first()

    if case is None:
        raise ValueError(f"Care case {case_id} was not found.")

    now = datetime.now()

    case_age_days = (now - case.opened_at).days

    days_until_due = None
    if case.due_at is not None:
        days_until_due = (case.due_at - now).days

    return {
        "case_status": case.case_status,
        "case_priority": case.priority,
        "case_age_days": case_age_days,
        "has_due_date": case.due_at is not None,
        "days_until_due": days_until_due
    }

def extract_all_case_features(db: Session, case_id: int) -> dict:
    """
    Combine all predictive features for a care case.
    """

    features = {}

    features.update(extract_case_features(db, case_id))
    features.update(extract_status_duration_features(db, case_id))
    features.update(extract_task_features(db, case_id))
    features.update(extract_referral_features(db, case_id))
    features.update(extract_appointment_features(db, case_id))
    features.update(extract_notification_features(db, case_id))
    features.update(extract_acknowledgement_features(db, case_id))

    return features

def extract_status_duration_features(db: Session, case_id: int) -> dict:
    """
    Calculate how long a care case has remained in its current status.
    """

    case = db.query(CareCase).filter(
        CareCase.case_id == case_id
    ).first()

    if case is None:
        raise ValueError(f"Care case {case_id} was not found.")

    latest_history = (
        db.query(CaseStatusHistory)
        .filter(
            CaseStatusHistory.case_id == case_id,
            CaseStatusHistory.changed_at.isnot(None)
        )
        .order_by(
            CaseStatusHistory.changed_at.desc(),
            CaseStatusHistory.history_id.desc()
        )
        .first()
    )

    if latest_history is None:
        return {
            "days_in_current_status": None,
            "status_history_matches_current_status": False
        }

    if latest_history.new_status != case.case_status:
        return {
            "days_in_current_status": None,
            "status_history_matches_current_status": False
        }

    days_in_status = (
        datetime.now() - latest_history.changed_at
    ).days

    return {
        "days_in_current_status": max(0, days_in_status),
        "status_history_matches_current_status": True
    }