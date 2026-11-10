from fastapi import HTTPException, status
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    """Yield one session per request and always close it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def safe_commit(db: Session, conflict_message: str = "Database conflict") -> None:
    """Commit, and roll back + return a clean HTTP error if the database rejects the change."""
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, conflict_message)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Database error, please try again")
