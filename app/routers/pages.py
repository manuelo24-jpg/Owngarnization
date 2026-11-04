from pathlib import Path
from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.deps import get_optional_current_user, get_db
from app.models import User
from app.services import project_service

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
    if request.query_params.get("source") == "pwa":
        return RedirectResponse(url="/m/spaces", status_code=302)
    return templates.TemplateResponse(
        request=request,
        name="mobile_app.html",
        context={"user": current_user}
    )


# --- SELECTOR DE ESPACIO (/spaces) ---

@router.get("/spaces", response_class=HTMLResponse)
@router.get("/m/spaces", response_class=HTMLResponse)
def spaces_page(request: Request, current_user: User | None = Depends(get_optional_current_user)):
    """Pantalla selectora de espacio (Organización Personal vs Proyectos)."""
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    user_agent = request.headers.get("user-agent", "").lower()
    is_mobile_ua = any(m in user_agent for m in ["mobile", "android", "iphone", "ipad", "ipod", "webos"])
    is_mobile = request.url.path.startswith("/m") or is_mobile_ua
    return templates.TemplateResponse(
        request=request,
        name="spaces.html",
        context={"user": current_user, "is_mobile": is_mobile}
    )


# --- LISTADO DE PROYECTOS (/projects) ---

@router.get("/projects", response_class=HTMLResponse)
@router.get("/m/projects", response_class=HTMLResponse)
def projects_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user)
):
    """Selector de proyecto: lista todos los proyectos activos del usuario."""
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)

    user_agent = request.headers.get("user-agent", "").lower()
    is_mobile_ua = any(m in user_agent for m in ["mobile", "android", "iphone", "ipad", "ipod", "webos"])
    is_mobile = request.url.path.startswith("/m") or is_mobile_ua
    user_projects = project_service.list_user_projects(db, current_user.id)
    return templates.TemplateResponse(
        request=request,
        name="projects/projects.html",
        context={
            "user": current_user,
            "projects": user_projects,
            "is_mobile": is_mobile
        }
    )


# --- ESPACIO INTERIOR DE UN PROYECTO (/projects/{id}) ---

@router.get("/projects/{project_id}", response_class=HTMLResponse)
@router.get("/m/projects/{project_id}", response_class=HTMLResponse)
def project_detail_page(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user)
):
    """Espacio interior de un proyecto concreto (tablero, horario y personas)."""
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)

    try:
        project_data = project_service.get_project_detail(db, project_id, current_user.id)
    except HTTPException as e:
        if e.status_code in (status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN):
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")
        raise e

    # Recordar último proyecto visitado
    current_user.last_project_id = project_id
    db.commit()

    user_agent = request.headers.get("user-agent", "").lower()
    is_mobile_ua = any(m in user_agent for m in ["mobile", "android", "iphone", "ipad", "ipod", "webos"])
    is_mobile = request.url.path.startswith("/m") or is_mobile_ua
    all_user_projects = project_service.list_user_projects(db, current_user.id)
    return templates.TemplateResponse(
        request=request,
        name="projects/project.html",
        context={
            "user": current_user,
            "project": project_data,
            "user_projects": all_user_projects,
            "is_mobile": is_mobile
        }
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
