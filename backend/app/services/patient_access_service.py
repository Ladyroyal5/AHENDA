from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.models.screening_result import ScreeningResult
from app.models.care_case import CareCase
from app.models.facility_user import FacilityUser
from app.models.referral import Referral
from app.models.handoff import Handoff
from app.models.case_assignment import CaseAssignment

from app.services.permission_service import user_has_permission
from app.models.patient_facility_relationship import PatientFacilityRelationship


def user_can_view_patients(
    db: Session,
    user_id: int,
    facility_id: int
) -> bool:

    return user_has_permission(
        db=db,
        user_id=user_id,
        facility_id=facility_id,
        permission_name="VIEW_PATIENTS"
    )

def patient_has_screening_relationship(
    db: Session,
    patient_id: int,
    facility_id: int
) -> bool:

    screening_record = (
        db.query(ScreeningResult)
        .filter(
            ScreeningResult.patient_id == patient_id,
            ScreeningResult.facility_id == facility_id,
            ScreeningResult.review_status != "CANCELLED"
        )
        .first()
    )

    return screening_record is not None

def patient_has_facility_relationship(
    db: Session,
    patient_id: int,
    facility_id: int
) -> bool:

    relationship = (
        db.query(PatientFacilityRelationship)
        .filter(
            PatientFacilityRelationship.patient_id == patient_id,
            PatientFacilityRelationship.facility_id == facility_id,
            PatientFacilityRelationship.relationship_status == "ACTIVE"
        )
        .first()
    )

    return relationship is not None


def patient_has_care_case_relationship(
    db: Session,
    patient_id: int,
    facility_id: int
) -> bool:

    care_case = (
        db.query(CareCase)
        .filter(
            CareCase.patient_id == patient_id,
            CareCase.coordinating_facility_id == facility_id,
            CareCase.case_status.notin_([
                "CANCELLED",
                "CLOSED",
                "RESOLVED"
            ])
        )
        .first()
    )

    return care_case is not None


def user_has_assigned_patient_case(
    db: Session,
    user_id: int,
    patient_id: int,
    facility_id: int
) -> bool:

    assignment = (
        db.query(CaseAssignment)
        .join(
            CareCase,
            CaseAssignment.case_id == CareCase.case_id
        )
        .join(
            FacilityUser,
            CaseAssignment.facility_user_id == FacilityUser.facility_user_id
        )
        .filter(
            FacilityUser.user_id == user_id,
            FacilityUser.facility_id == facility_id,
            FacilityUser.employment_status == "ACTIVE",
            CaseAssignment.is_current.is_(True),
            CareCase.patient_id == patient_id,
            CareCase.coordinating_facility_id == facility_id,
            CareCase.case_status.notin_([
                "CANCELLED",
                "CLOSED",
                "RESOLVED"
            ])
        )
        .first()
    )

    return assignment is not None

def patient_has_referral_relationship(
    db: Session,
    patient_id: int,
    facility_id: int
) -> bool:

    referral = (
        db.query(Referral)
        .join(
            CareCase,
            Referral.case_id == CareCase.case_id
        )
        .filter(
            CareCase.patient_id == patient_id,
            Referral.receiving_facility_id == facility_id,
            Referral.referral_status.in_([
                "ISSUED",
                "SENT",
                "ACKNOWLEDGED",
                "ACCEPTED"
            ])
        )
        .first()
    )

    return referral is not None


def patient_has_handoff_relationship(
    db: Session,
    patient_id: int,
    facility_id: int
) -> bool:

    handoff = (
        db.query(Handoff)
        .join(
            Referral,
            Handoff.referral_id == Referral.referral_id
        )
        .join(
            CareCase,
            Referral.case_id == CareCase.case_id
        )
        .filter(
            CareCase.patient_id == patient_id,
            Handoff.receiving_facility_id == facility_id,
            Handoff.handoff_status.in_([
                "RECEIVED",
                "ACCEPTED"
            ]),
            Handoff.sending_facility_id == Referral.referring_facility_id,
            Handoff.receiving_facility_id == Referral.receiving_facility_id,
            Referral.referral_status.notin_(["DRAFT", "CANCELLED", "REJECTED"])
        )
        .first()
    )

    return handoff is not None


def user_can_access_patient(
    db: Session,
    user_id: int,
    patient_id: int,
    facility_id: int
) -> bool:

    patient = db.query(Patient).filter(
        Patient.patient_id == patient_id,
        Patient.is_active.is_(True)
    ).first()

    if not patient:
        return False

    # First, check whether the user has permission to view patients.
    if not user_can_view_patients(db, user_id, facility_id):
        return False

    # Then check whether the patient has a legitimate
    # relationship with the facility or assigned staff member.
    return any([
        patient_has_facility_relationship(
        db, patient_id, facility_id
        ),
        patient_has_screening_relationship(
            db, patient_id, facility_id
        ),
        patient_has_care_case_relationship(
            db, patient_id, facility_id
        ),
        user_has_assigned_patient_case(
            db, user_id, patient_id, facility_id
        ),
        patient_has_referral_relationship(
            db, patient_id, facility_id
        ),
        patient_has_handoff_relationship(
            db, patient_id, facility_id
        )
        
    ])    