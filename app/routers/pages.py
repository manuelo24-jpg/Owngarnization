from pathlib import Path
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.deps import get_optional_current_user
from app.models import User

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(include_in_schema=False)


@router.get("/", response_class=HTMLResponse)
@router.get("/app", response_class=HTMLResponse)
def index(request: Request, current_user: User | None = Depends(get_optional_current_user)):
    """Página principal de la versión Web. Redirige a /login si no hay sesión."""
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(
        request=request,
        name="app.html",
        context={"user": current_user}
    )


@router.get("/m", response_class=HTMLResponse)
def mobile_app_page(request: Request, current_user: User | None = Depends(get_optional_current_user)):
    """Versión dedicada de la App Móvil (PWA standalone). Redirige a /login si no hay sesión."""
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(
        request=request,
        name="mobile_app.html",
        context={"user": current_user}
    )


@router.get("/download", response_class=HTMLResponse)
def download_mobile_page(request: Request, current_user: User | None = Depends(get_optional_current_user)):
    """Página para descargar e instalar la aplicación móvil desde la web en Android e iOS."""
    return templates.TemplateResponse(
        request=request,
        name="download_app.html",
        context={"user": current_user}
    )


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, current_user: User | None = Depends(get_optional_current_user)):
    """Pantalla de inicio de sesión."""
    if current_user:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse(
        request=request,
        name="login.html"
    )


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request, current_user: User | None = Depends(get_optional_current_user)):
    """Pantalla de registro."""
    if current_user:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse(
        request=request,
        name="register.html"
    )


@router.get("/privacy", response_class=HTMLResponse)
def privacy_page(request: Request):
    """Página de Política de Privacidad y Protección de Datos."""
    return templates.TemplateResponse(
        request=request,
        name="privacy.html"
    )


