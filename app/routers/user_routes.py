"""Profile + account endpoints. HTTP layer only; the user comes from the JWT, never from the body."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.security import AuthUser, get_current_auth_user
from app.database.connection import get_db
from app.models.user_model import UserProfile
from app.schemas.address_schema import AddressOut
from app.schemas.user_schema import (
    AccountOut, MessageResponse, ProfileCreate, ProfileOut, ProfilePatch, ProfileUpdate,
)
from app.services import address_service, user_service

router = APIRouter(prefix="/api/users", tags=["User Profile"])


@router.post("/profile", response_model=ProfileOut, status_code=status.HTTP_201_CREATED)
def create_profile(data: ProfileCreate, auth: AuthUser = Depends(get_current_auth_user),
                   db: Session = Depends(get_db)):
    return user_service.create_profile(db, auth.user_id, data)


@router.get("/profile", response_model=ProfileOut)
def get_profile(profile: UserProfile = Depends(user_service.get_active_profile)):
    return profile


@router.put("/profile", response_model=ProfileOut)
def update_profile(data: ProfileUpdate, profile: UserProfile = Depends(user_service.get_active_profile),
                   db: Session = Depends(get_db)):
    return user_service.replace_profile(db, profile, data)


@router.patch("/profile", response_model=ProfileOut)
def patch_profile(data: ProfilePatch, profile: UserProfile = Depends(user_service.get_active_profile),
                  db: Session = Depends(get_db)):
    return user_service.patch_profile(db, profile, data)


@router.delete("/profile", response_model=MessageResponse)
def delete_profile(profile: UserProfile = Depends(user_service.get_any_profile),
                   db: Session = Depends(get_db)):
    user_service.delete_profile(db, profile)
    return MessageResponse(message="Profile and saved addresses deleted. Authentication account is unchanged.")


@router.patch("/profile/deactivate", response_model=ProfileOut)
def deactivate_profile(profile: UserProfile = Depends(user_service.get_any_profile),
                       db: Session = Depends(get_db)):
    """Deactivates the PROFILE only. The Authentication Service account is not touched."""
    return user_service.set_active(db, profile, False)


@router.patch("/profile/reactivate", response_model=ProfileOut)
def reactivate_profile(profile: UserProfile = Depends(user_service.get_any_profile),
                       db: Session = Depends(get_db)):
    return user_service.set_active(db, profile, True)


@router.get("/account", response_model=AccountOut)
def get_account(profile: UserProfile = Depends(user_service.get_any_profile),
                db: Session = Depends(get_db)):
    """Account overview (works even when the profile is deactivated, so the status is visible)."""
    addresses = address_service.list_addresses(db, profile)
    return AccountOut(profile=ProfileOut.model_validate(profile), address_count=len(addresses),
                      addresses=[AddressOut.model_validate(a) for a in addresses])
