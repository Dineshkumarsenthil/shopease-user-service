"""Address business logic: ownership checks and the single-default-address rule."""
from typing import List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import safe_commit
from app.models.address_model import UserAddress
from app.models.user_model import UserProfile
from app.schemas.address_schema import AddressCreate, AddressUpdate


def get_owned_address(db: Session, profile: UserProfile, address_id: int) -> UserAddress:
    address = db.get(UserAddress, address_id)
    if address is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Address not found")
    if address.user_id != profile.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have access to this address")
    return address


def _clear_default(db: Session, profile: UserProfile, except_id=None) -> None:
    query = db.query(UserAddress).filter(UserAddress.user_id == profile.id, UserAddress.is_default.is_(True))
    if except_id is not None:
        query = query.filter(UserAddress.id != except_id)
    for other in query.all():
        other.is_default = False


def list_addresses(db: Session, profile: UserProfile) -> List[UserAddress]:
    return (db.query(UserAddress).filter(UserAddress.user_id == profile.id)
            .order_by(UserAddress.is_default.desc(), UserAddress.id).all())


def create_address(db: Session, profile: UserProfile, data: AddressCreate) -> UserAddress:
    has_any = db.query(UserAddress).filter(UserAddress.user_id == profile.id).count() > 0
    make_default = data.is_default or not has_any   # the first address is the default automatically
    address = UserAddress(user_id=profile.id, **data.model_dump(exclude={"is_default"}), is_default=False)
    db.add(address)
    db.flush()
    if make_default:
        _clear_default(db, profile, except_id=address.id)
        address.is_default = True
    safe_commit(db)
    db.refresh(address)
    return address


def update_address(db: Session, profile: UserProfile, address_id: int, data: AddressUpdate) -> UserAddress:
    address = get_owned_address(db, profile, address_id)
    for field, value in data.model_dump(exclude={"is_default"}).items():
        setattr(address, field, value)
    if data.is_default:
        _clear_default(db, profile, except_id=address.id)
        address.is_default = True
    safe_commit(db)
    db.refresh(address)
    return address


def set_default_address(db: Session, profile: UserProfile, address_id: int) -> UserAddress:
    address = get_owned_address(db, profile, address_id)
    _clear_default(db, profile, except_id=address.id)
    address.is_default = True
    safe_commit(db)
    db.refresh(address)
    return address


def delete_address(db: Session, profile: UserProfile, address_id: int) -> None:
    address = get_owned_address(db, profile, address_id)
    was_default = address.is_default
    db.delete(address)
    db.flush()
    if was_default:  # keep one default if other addresses remain
        nxt = (db.query(UserAddress).filter(UserAddress.user_id == profile.id)
               .order_by(UserAddress.id).first())
        if nxt is not None:
            nxt.is_default = True
    safe_commit(db)
