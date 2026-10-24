import bcrypt
from starlette.requests import Request


def hash_password(password: str) -> str:
    """Hashea una contraseña utilizando bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si la contraseña coincide con el hash almacenado."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def set_session_user(request: Request, user_id: int) -> None:
    """Guarda el ID del usuario en la sesión cifrada."""
    request.session["user_id"] = user_id


def get_session_user_id(request: Request) -> int | None:
    """Obtiene el ID del usuario desde la sesión firmada."""
    return request.session.get("user_id")


def clear_session(request: Request) -> None:
    """Limpia los datos de sesión (logout)."""
    request.session.clear()
