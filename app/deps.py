from typing import Generator
from fastapi import Depends, HTTPException, status
from starlette.requests import Request
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User
from app.security import get_session_user_id


def get_db() -> Generator[Session, None, None]:
    """Generador de sesiones de base de datos."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_optional_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> User | None:
    """Retorna el usuario actual si hay sesión activa, o None."""
    user_id = get_session_user_id(request)
    if not user_id:
        return None
    return db.query(User).filter(User.id == user_id).first()


def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    """Retorna el usuario autenticado o lanza HTTP 401 si no hay sesión."""
    user = get_optional_current_user(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión no iniciada o inválida"
        )
    return user
