from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from pathlib import Path

from app.config import settings

app = FastAPI(
    title="Owngarnization",
    description="Aplicación web de gestión de tareas con calendario y post-its",
    version="0.1.0",
)

# Sesión firmada
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie="owngarnization_session",
    max_age=14 * 24 * 3600,  # 14 días
    same_site="lax",
    https_only=settings.is_production,
)

BASE_DIR = Path(__file__).resolve().parent

# Montar archivos estáticos
static_dir = BASE_DIR / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/health", tags=["Salud"])
async def health_check():
    return {
        "status": "ok",
        "app": "Owngarnization",
        "env": settings.ENV,
        "version": "0.1.0"
    }
