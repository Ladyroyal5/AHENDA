
import hashlib
import hmac
import os
import re
import unicodedata

from sqlalchemy.orm import Session

from app.models.patient_identifier import PatientIdentifier

from app.models.identity_review import IdentityReviewCase


def normalise_identifier(identifier_type: str, value: str) -> str:
    """
    Standardise an identifier before hashing it.
    This helps equivalent values produce the same hash.
    """

    identifier_type = identifier_type.strip().upper()
    value = unicodedata.normalize("NFKC", value).strip()

    if identifier_type == "EMAIL":
        return value.lower()

    if identifier_type == "PHONE":
        # Remove spaces and common formatting characters.
        # Use a consistent international format when entering phone numbers.
        return re.sub(r"[\s\-()]", "", value)

    # General identifier normalisation.
    return value.upper()


def hash_identifier(identifier_type: str, value: str) -> str:
    """
    Create a secure, repeatable HMAC-SHA256 hash.
    The original identifier is never stored in this hash field.
    """

    secret_key = os.getenv("AHENDA_IDENTITY_HMAC_KEY")

    if not secret_key:
        raise RuntimeError(
            "AHENDA_IDENTITY_HMAC_KEY is missing from the environment."
        )

    identifier_type = identifier_type.strip().upper()
    normalised_value = normalise_identifier(identifier_type, value)

    if not normalised_value:
        raise ValueError("Identifier cannot be empty.")

    payload = f"{identifier_type}:{normalised_value}".encode("utf-8")

    return hmac.new(
        secret_key.encode("utf-8"),
        payload,
        hashlib.sha256
    ).hexdigest()


def find_identifier_matches(
    db: Session,
    identifier_type: str,
    value: str
):
    """
    Find existing records with the same identifier hash.
    A match is a signal for review, not proof of patient identity.
    """

    identifier_hash = hash_identifier(identifier_type, value)

    matches = db.query(PatientIdentifier).filter(
        PatientIdentifier.identifier_type == identifier_type.strip().upper(),
        PatientIdentifier.identifier_hash == identifier_hash
    ).all()

    return matches




def register_identifier(
    db: Session,
    patient_id: int,
    identifier_type: str,
    identifier_value: str,
    facility_id: int | None = None
):
    """
    Register a hashed identifier for an existing patient.

    If another patient has the same identifier, create
    a pending identity review instead of linking records.
    """

    identifier_type = identifier_type.strip().upper()

    identifier_hash = hash_identifier(
        identifier_type,
        identifier_value
    )

    matches = db.query(PatientIdentifier).filter(
        PatientIdentifier.identifier_type == identifier_type,
        PatientIdentifier.identifier_hash == identifier_hash
    ).all()

    other_patient_matches = [
        match for match in matches
        if match.patient_id != patient_id
    ]

    # A possible match exists: create a review case.
    if other_patient_matches:

        created_reviews = 0

        for match in other_patient_matches:

            existing_review = db.query(IdentityReviewCase).filter(
                IdentityReviewCase.patient_id == patient_id,
                IdentityReviewCase.matched_patient_id == match.patient_id,
                IdentityReviewCase.identifier_type == identifier_type,
                IdentityReviewCase.identifier_hash == identifier_hash,
                IdentityReviewCase.review_status == "PENDING"
            ).first()

            if existing_review:
                continue

            review_case = IdentityReviewCase(
                patient_id=patient_id,
                matched_patient_id=match.patient_id,
                identifier_type=identifier_type,
                identifier_hash=identifier_hash,
                review_status="PENDING"
            )

            db.add(review_case)
            created_reviews += 1

        db.flush()

        return {
            "status": "review_required",
            "message": "A possible existing patient match requires review.",
            "review_cases_created": created_reviews
        }

    # Check whether this patient already has this identifier
    # at the same facility.
    same_facility_match = any(
        match.patient_id == patient_id
        and match.facility_id == facility_id
        for match in matches
    )

    if same_facility_match:
        return {
            "status": "already_registered",
            "message": "This identifier is already registered."
        }

    # No conflicting patient record was found.
    new_identifier = PatientIdentifier(
        patient_id=patient_id,
        facility_id=facility_id,
        identifier_type=identifier_type,
        identifier_hash=identifier_hash
    )

    db.add(new_identifier)
    db.flush()

    return {
        "status": "registered",
        "message": "Identifier registered successfully."
    }


    