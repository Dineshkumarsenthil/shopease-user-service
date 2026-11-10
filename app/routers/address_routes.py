"""Address endpoints. Every route works only on the logged-in user's own addresses."""
from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.user_model import UserProfile
from app.schemas.address_schema import AddressCreate, AddressOut, AddressUpdate
from app.schemas.user_schema import MessageResponse
from app.services import address_service, user_service

router = APIRouter(prefix="/api/users/addresses", tags=["User Addresses"])


@router.post("", response_model=AddressOut, status_code=status.HTTP_201_CREATED)
def add_address(data: AddressCreate, profile: UserProfile = Depends(user_service.get_active_profile),
                db: Session = Depends(get_db)):
    return address_service.create_address(db, profile, data)


@router.get("", response_model=List[AddressOut])
def list_addresses(profile: UserProfile = Depends(user_service.get_active_profile),
                   db: Session = Depends(get_db)):
    return address_service.list_addresses(db, profile)


@router.get("/{address_id}", response_model=AddressOut)
def get_address(address_id: int, profile: UserProfile = Depends(user_service.get_active_profile),
                db: Session = Depends(get_db)):
    return address_service.get_owned_address(db, profile, address_id)


@router.put("/{address_id}", response_model=AddressOut)
def update_address(address_id: int, data: AddressUpdate,
                   profile: UserProfile = Depends(user_service.get_active_profile),
                   db: Session = Depends(get_db)):
    return address_service.update_address(db, profile, address_id, data)


@router.delete("/{address_id}", response_model=MessageResponse)
def delete_address(address_id: int, profile: UserProfile = Depends(user_service.get_active_profile),
                   db: Session = Depends(get_db)):
    address_service.delete_address(db, profile, address_id)
    return MessageResponse(message="Address deleted successfully")


@router.patch("/{address_id}/default", response_model=AddressOut)
def set_default(address_id: int, profile: UserProfile = Depends(user_service.get_active_profile),
                db: Session = Depends(get_db)):
    return address_service.set_default_address(db, profile, address_id)
