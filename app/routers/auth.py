from fastapi import APIRouter, Depends, HTTPException, status
from starlette.requests import Request
from sqlalchemy.orm import Session

from app.deps import get_db, get_current_user
from app.models import User
from app.schemas import UserCreate, UserLogin, UserResponse
from app.security import hash_password, verify_password, set_session_user, clear_session

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, request: Request, db: Session = Depends(get_db)):
    """Registra un nuevo usuario e inicia sesión automáticamente."""
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo electrónico ya está registrado"
        )

    user = User(
        email=user_in.email,
        username=user_in.username,
        password_hash=hash_password(user_in.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Iniciar sesión automáticamente
    set_session_user(request, user.id)
    return user


@router.post("/login")
def login(user_in: UserLogin, request: Request, db: Session = Depends(get_db)):
    """Inicia sesión validando credenciales y creando la cookie de sesión."""
    user = db.query(User).filter(User.email == user_in.email).first()
    if not user or not verify_password(user_in.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas"
        )

    set_session_user(request, user.id)
    return {
        "message": "Inicio de sesión exitoso",
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "created_at": user.created_at
        }
    }


@router.post("/logout")
def logout(request: Request):
    """Cierra la sesión activa del usuario."""
    clear_session(request)
    return {"message": "Sesión cerrada correctamente"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Obtiene los datos del usuario actualmente autenticado."""
    return current_user
