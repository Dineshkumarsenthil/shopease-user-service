"""Profile business logic + the dependencies that resolve the current user's profile."""
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import AuthUser, get_current_auth_user
from app.database.connection import get_db, safe_commit
from app.models.user_model import UserProfile
from app.schemas.user_schema import ProfileCreate, ProfilePatch, ProfileUpdate


def find_profile(db: Session, auth_user_id: int):
    return db.query(UserProfile).filter(UserProfile.auth_user_id == auth_user_id).first()


# ---- dependencies: the profile is ALWAYS looked up from the token's user id ----
def get_any_profile(auth: AuthUser = Depends(get_current_auth_user),
                    db: Session = Depends(get_db)) -> UserProfile:
    profile = find_profile(db, auth.user_id)
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profile not found. Create your profile first.")
    return profile


def get_active_profile(profile: UserProfile = Depends(get_any_profile)) -> UserProfile:
    if not profile.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Profile is deactivated")
    return profile


# ---- operations ----
def create_profile(db: Session, auth_user_id: int, data: ProfileCreate) -> UserProfile:
    if find_profile(db, auth_user_id):
        raise HTTPException(status.HTTP_409_CONFLICT, "Profile already exists for this user")
    profile = UserProfile(auth_user_id=auth_user_id, **data.model_dump())
    db.add(profile)
    safe_commit(db, "Profile already exists for this user")  # unique(auth_user_id) is the final guard
    db.refresh(profile)
    return profile


def replace_profile(db: Session, profile: UserProfile, data: ProfileUpdate) -> UserProfile:
    for field, value in data.model_dump().items():
        setattr(profile, field, value)
    safe_commit(db)
    db.refresh(profile)
    return profile


def patch_profile(db: Session, profile: UserProfile, data: ProfilePatch) -> UserProfile:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    safe_commit(db)
    db.refresh(profile)
    return profile


def delete_profile(db: Session, profile: UserProfile) -> None:
    db.delete(profile)  # addresses are removed by the cascade
    safe_commit(db)


def set_active(db: Session, profile: UserProfile, active: bool) -> UserProfile:
    if profile.is_active == active:
        state = "active" if active else "deactivated"
        raise HTTPException(status.HTTP_409_CONFLICT, f"Profile is already {state}")
    profile.is_active = active
    safe_commit(db)
    db.refresh(profile)
    return profile
