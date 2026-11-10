"""Pydantic models for address endpoints."""
import re
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

AddressType = Literal["Home", "Office", "Other"]
_PHONE_RE = re.compile(r"^\+?\d{10,15}$")
_POSTAL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9\- ]{2,9}$")


class _AddressBase(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    address_type: AddressType
    full_name: str = Field(min_length=2, max_length=100)
    phone_number: str
    address_line_1: str = Field(min_length=3, max_length=255)
    address_line_2: Optional[str] = Field(default=None, max_length=255)
    city: str = Field(min_length=2, max_length=100)
    state: str = Field(min_length=2, max_length=100)
    country: str = Field(min_length=2, max_length=100)
    postal_code: str

    @field_validator("address_type", mode="before")
    @classmethod
    def _type(cls, v):
        return v.strip().capitalize() if isinstance(v, str) else v

    @field_validator("phone_number")
    @classmethod
    def _phone(cls, v):
        cleaned = re.sub(r"[\s\-()]", "", v)
        if not _PHONE_RE.match(cleaned):
            raise ValueError("Phone number must have 10 to 15 digits (optional leading +)")
        return cleaned

    @field_validator("postal_code")
    @classmethod
    def _postal(cls, v):
        if not _POSTAL_RE.match(v):
            raise ValueError("Postal code must be 3 to 10 letters, digits, spaces or hyphens")
        return v


class AddressCreate(_AddressBase):
    is_default: bool = False


class AddressUpdate(_AddressBase):
    # True -> make this the default address. False/omitted -> default status unchanged.
    # (Use PATCH /{id}/default to switch the default address.)
    is_default: Optional[bool] = None


class AddressOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    address_type: str
    full_name: str
    phone_number: str
    address_line_1: str
    address_line_2: Optional[str] = None
    city: str
    state: str
    country: str
    postal_code: str
    is_default: bool
    created_at: Optional[datetime] = None
