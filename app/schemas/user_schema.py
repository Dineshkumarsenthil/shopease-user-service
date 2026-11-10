"""Pydantic models for profile endpoints."""
import re
from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.address_schema import AddressOut

Gender = Literal["Male", "Female", "Other"]
_PHONE_RE = re.compile(r"^\+?\d{10,15}$")


def clean_phone(value: str) -> str:
    cleaned = re.sub(r"[\s\-()]", "", value)
    if not _PHONE_RE.match(cleaned):
        raise ValueError("Phone number must have 10 to 15 digits (optional leading +)")
    return cleaned


class _Strict(BaseModel):
    # extra="forbid": a client cannot send auth_user_id / is_active etc. in the body
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class _ProfileFields(_Strict):
    @field_validator("phone_number", check_fields=False)
    @classmethod
    def _phone(cls, v):
        return clean_phone(v) if v is not None else v

    @field_validator("gender", mode="before", check_fields=False)
    @classmethod
    def _gender(cls, v):
        return v.strip().capitalize() if isinstance(v, str) else v

    @field_validator("date_of_birth", check_fields=False)
    @classmethod
    def _dob(cls, v):
        if v is not None and v > date.today():
            raise ValueError("Date of birth cannot be in the future")
        return v


class ProfileCreate(_ProfileFields):
    full_name: str = Field(min_length=2, max_length=100)
    phone_number: str
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    profile_image: Optional[str] = Field(default=None, max_length=255)


class ProfileUpdate(ProfileCreate):
    """PUT: full replacement of the editable fields."""


class ProfilePatch(_ProfileFields):
    """PATCH: send only the fields to change."""
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    phone_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    profile_image: Optional[str] = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def at_least_one(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update")
        if "full_name" in self.model_fields_set and self.full_name is None:
            raise ValueError("full_name cannot be null")
        if "phone_number" in self.model_fields_set and self.phone_number is None:
            raise ValueError("phone_number cannot be null")
        return self


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    auth_user_id: int
    full_name: str
    phone_number: str
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    profile_image: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AccountOut(BaseModel):
    profile: ProfileOut
    address_count: int
    addresses: List[AddressOut]


class MessageResponse(BaseModel):
    message: str
