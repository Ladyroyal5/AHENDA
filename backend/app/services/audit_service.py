from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def record_audit_event(
    db: Session,
    actor_user_id: int | None,
    facility_id: int | None,
    action: str,
    entity_type: str,
    entity_id: str,
    old_values: dict | None = None,
    new_values: dict | None = None,
    ip_address: str | None = None
):
    audit_record = AuditLog(
        actor_user_id=actor_user_id,
        facility_id=facility_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        old_values=old_values,
        new_values=new_values,
        ip_address=ip_address
    )

    db.add(audit_record)

    return audit_record