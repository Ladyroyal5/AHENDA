
from datetime import date
from pydantic import BaseModel, Field, ConfigDict


class PatientCreate(BaseModel):
    first_name: str = Field(min_length=2, max_length=100)
    last_name: str = Field(min_length=2, max_length=100)

    middle_name: str | None = Field(default=None, max_length=100)

    date_of_birth: date | None = None
    sex: str | None = Field(default=None, max_length=30)

    phone_number: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=255)

    preferred_language: str = Field(
        default="English",
        max_length=50
    )


class PatientResponse(BaseModel):
    public_id: str
    first_name: str
    last_name: str
    middle_name: str | None
    date_of_birth: date | None
    sex: str | None
    phone_number: str | None
    email: str | None
    preferred_language: str | None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
    

class PatientIdentifierCreate(BaseModel):
    identifier_type: str = Field(min_length=2, max_length=50)
    identifier_value: str = Field(min_length=1, max_length=255)
    facility_id: int | None = None
