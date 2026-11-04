import asyncio
from contextlib import asynccontextmanager
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.routers import auth, pages, tasks, pwa, push, spaces, projects
from app.services.reminder_service import run_due_reminders_session


async def _reminder_scheduler_loop():
    """
    Bucle interno en segundo plano que evalúa y despacha avisos Web Push
    para tareas con hora cada 15 segundos sin requerir que la app esté abierta.
    """
    while True:
        try:
            await asyncio.to_thread(run_due_reminders_session)
        except asyncio.CancelledError:
            break
        except Exception:
            pass
        await asyncio.sleep(15)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler_task = None
    if "pytest" not in sys.modules:
        scheduler_task = asyncio.create_task(_reminder_scheduler_loop())
    try:
        yield
    finally:
        if scheduler_task:
            scheduler_task.cancel()
            try:
                await scheduler_task
            except asyncio.CancelledError:
                pass


app = FastAPI(
    title="Owngarnization",
    description="Aplicación web de gestión de tareas con calendario y post-its",
    version="0.1.0",
    lifespan=lifespan,
)

# Sesión firmada (30 días para experiencia fluida en PWA standalone iOS/Android)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie="owngarnization_session",
    max_age=30 * 24 * 3600,  # 30 días
    same_site="lax",
    https_only=settings.is_production,
)

# Incluir routers
app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(pwa.router)
app.include_router(push.router)
app.include_router(spaces.router)
app.include_router(projects.router)
app.include_router(pages.router)

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
