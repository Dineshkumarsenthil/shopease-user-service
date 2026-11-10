from sqlalchemy import Boolean, Column, Date, DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.database.connection import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"
    __table_args__ = (UniqueConstraint("auth_user_id", name="uq_user_profiles_auth_user_id"),)

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    # ID of the user in the Authentication Service (the "sub" claim of the JWT)
    auth_user_id = Column(Integer, nullable=False)  # unique constraint declared in __table_args__
    full_name = Column(String(100), nullable=False)
    phone_number = Column(String(20), nullable=False)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(20), nullable=True)
    profile_image = Column(String(255), nullable=True)
    # Profile-level status only. Does NOT change the account in the Authentication Service.
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    addresses = relationship(
        "UserAddress", back_populates="profile",
        cascade="all, delete-orphan", order_by="UserAddress.id",
    )
