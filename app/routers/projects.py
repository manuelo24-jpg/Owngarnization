from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.deps import get_db, get_current_user
from app.models import User
from app.schemas import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectDetailResponse,
    ProjectMemberInvite,
    ProjectMemberUpdate,
    ProjectMemberResponse,
    ProjectRoleCreate,
    ProjectRoleUpdate,
    ProjectRoleResponse,
    ProjectColumnCreate,
    ProjectColumnUpdate,
    ProjectColumnReorder,
    ProjectColumnResponse,
    ProjectTaskCreate,
    ProjectTaskUpdate,
    ProjectTaskMove,
    ProjectTaskResponse,
    ProjectScheduleResponse,
    ProjectWorkloadResponse,
)
from app.services import project_service, project_task_service, project_schedule_service

router = APIRouter(prefix="/api/projects", tags=["Proyectos"])


# --- PROYECTOS ---

@router.get("", response_model=List[ProjectResponse])
def list_projects(
    archived: bool = Query(False, description="Incluir proyectos archivados"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista todos los proyectos a los que pertenece el usuario."""
    return project_service.list_user_projects(db, current_user.id, include_archived=archived)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Crea un nuevo proyecto inicializando columnas y rol por defecto."""
    proj = project_service.create_project(db, current_user, payload)
    detail = project_service.get_project_detail(db, proj.id, current_user.id)
    return detail


@router.get("/{project_id}", response_model=ProjectDetailResponse)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtiene los detalles completos del proyecto, columnas y tareas."""
    return project_service.get_project_detail(db, project_id, current_user.id)


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualiza datos del proyecto (nombre, descripción, color, archivo)."""
    proj = project_service.update_project(db, project_id, current_user.id, payload)
    return project_service.get_project_detail(db, proj.id, current_user.id)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Borrado lógico del proyecto (exclusivo para owner)."""
    project_service.delete_project(db, project_id, current_user.id)
    return None


# --- MIEMBROS ---

@router.get("/{project_id}/members", response_model=List[ProjectMemberResponse])
def list_members(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista los miembros del proyecto con sus roles y permisos."""
    detail = project_service.get_project_detail(db, project_id, current_user.id)
    return detail["all_members"]


@router.post("/{project_id}/members", response_model=ProjectMemberResponse, status_code=status.HTTP_201_CREATED)
def invite_member(
    project_id: int,
    payload: ProjectMemberInvite,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Invita a un usuario registrado al proyecto."""
    new_mem = project_service.invite_member(db, project_id, current_user.id, payload)
    return {
        "id": new_mem.id,
        "project_id": new_mem.project_id,
        "user_id": new_mem.user.id,
        "username": new_mem.user.username,
        "email": new_mem.user.email,
        "permission": new_mem.permission,
        "role_id": new_mem.role_id,
        "role_name": new_mem.role.name if new_mem.role else None,
        "role_color": new_mem.role.color if new_mem.role else None,
        "weekly_hours": new_mem.weekly_hours,
        "joined_at": new_mem.joined_at,
    }


@router.patch("/{project_id}/members/{user_id}", response_model=ProjectMemberResponse)
def update_member(
    project_id: int,
    user_id: int,
    payload: ProjectMemberUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Modifica permisos, rol de equipo o capacidad de un miembro."""
    mem = project_service.update_member(db, project_id, current_user.id, user_id, payload)
    return {
        "id": mem.id,
        "project_id": mem.project_id,
        "user_id": mem.user.id,
        "username": mem.user.username,
        "email": mem.user.email,
        "permission": mem.permission,
        "role_id": mem.role_id,
        "role_name": mem.role.name if mem.role else None,
        "role_color": mem.role.color if mem.role else None,
        "weekly_hours": mem.weekly_hours,
        "joined_at": mem.joined_at,
    }


@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    project_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Expulsa o abandona un proyecto asegurando que permanezca al menos 1 owner."""
    project_service.remove_member(db, project_id, current_user.id, user_id)
    return None


# --- ROLES ---

@router.get("/{project_id}/roles", response_model=List[ProjectRoleResponse])
def list_roles(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista todos los roles de equipo del proyecto."""
    detail = project_service.get_project_detail(db, project_id, current_user.id)
    return detail["roles"]


@router.post("/{project_id}/roles", response_model=ProjectRoleResponse, status_code=status.HTTP_201_CREATED)
def create_role(
    project_id: int,
    payload: ProjectRoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Crea un nuevo rol de equipo en el proyecto."""
    return project_service.create_role(db, project_id, current_user.id, payload)


@router.patch("/{project_id}/roles/{role_id}", response_model=ProjectRoleResponse)
def update_role(
    project_id: int,
    role_id: int,
    payload: ProjectRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualiza nombre o color de un rol."""
    return project_service.update_role(db, project_id, role_id, current_user.id, payload)


@router.delete("/{project_id}/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    project_id: int,
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Elimina un rol sin borrar a los miembros."""
    project_service.delete_role(db, project_id, role_id, current_user.id)
    return None


# --- COLUMNAS ---

@router.post("/{project_id}/columns", response_model=ProjectColumnResponse, status_code=status.HTTP_201_CREATED)
def create_column(
    project_id: int,
    payload: ProjectColumnCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Crea una columna en el tablero del proyecto."""
    col = project_service.create_column(db, project_id, current_user.id, payload)
    return {
        "id": col.id,
        "project_id": col.project_id,
        "name": col.name,
        "position": col.position,
        "is_done": col.is_done,
        "tasks": [],
    }


@router.patch("/{project_id}/columns/{column_id}", response_model=ProjectColumnResponse)
def update_column(
    project_id: int,
    column_id: int,
    payload: ProjectColumnUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Edita nombre, orden o marca is_done de la columna."""
    col = project_service.update_column(db, project_id, column_id, current_user.id, payload)
    return {
        "id": col.id,
        "project_id": col.project_id,
        "name": col.name,
        "position": col.position,
        "is_done": col.is_done,
        "tasks": [],
    }


@router.post("/{project_id}/columns/reorder", response_model=List[ProjectColumnResponse])
def reorder_columns(
    project_id: int,
    payload: ProjectColumnReorder,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reordena las columnas según la lista de IDs provista."""
    cols = project_service.reorder_columns(db, project_id, current_user.id, payload.column_ids)
    return [
        {
            "id": c.id,
            "project_id": c.project_id,
            "name": c.name,
            "position": c.position,
            "is_done": c.is_done,
            "tasks": [],
        }
        for c in cols
    ]


@router.delete("/{project_id}/columns/{column_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_column(
    project_id: int,
    column_id: int,
    target_column_id: Optional[int] = Query(None, description="Columna receptora de las tareas existentes"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Elimina una columna asegurando que quede al menos una."""
    project_service.delete_column(db, project_id, column_id, current_user.id, target_column_id=target_column_id)
    return None


# --- TAREAS ---

@router.post("/{project_id}/tasks", response_model=ProjectTaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    project_id: int,
    payload: ProjectTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Crea una tarea en el proyecto."""
    return project_task_service.create_task(db, project_id, current_user.id, payload)


@router.get("/{project_id}/tasks/{task_id}", response_model=ProjectTaskResponse)
def get_task(
    project_id: int,
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtiene el detalle completo de una tarea del proyecto."""
    return project_task_service.get_task(db, project_id, task_id, current_user.id)


@router.patch("/{project_id}/tasks/{task_id}", response_model=ProjectTaskResponse)
def update_task(
    project_id: int,
    task_id: int,
    payload: ProjectTaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualiza una tarea del proyecto."""
    return project_task_service.update_task(db, project_id, task_id, current_user.id, payload)


@router.post("/{project_id}/tasks/move", response_model=ProjectTaskResponse)
def move_task(
    project_id: int,
    payload: ProjectTaskMove,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mueve una tarea de columna y actualiza su posición."""
    return project_task_service.move_task(db, project_id, current_user.id, payload)


@router.delete("/{project_id}/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    project_id: int,
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Eliminación lógica de tarea."""
    project_task_service.delete_task(db, project_id, task_id, current_user.id)
    return None


# --- HORARIO Y CARGA HORARIA ---

@router.get("/{project_id}/schedule", response_model=ProjectScheduleResponse)
def get_schedule(
    project_id: int,
    start: date = Query(..., description="Fecha de inicio (YYYY-MM-DD)"),
    end: date = Query(..., description="Fecha de fin (YYYY-MM-DD)"),
    by: Optional[str] = Query(None, description="'person' para agrupar por miembro"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna las tareas programadas con hora en el rango dado."""
    return project_schedule_service.get_project_schedule(
        db, project_id, current_user.id, start, end, by_person=(by == "person")
    )


@router.get("/{project_id}/workload", response_model=ProjectWorkloadResponse)
def get_workload(
    project_id: int,
    week: Optional[date] = Query(None, description="Cualquier fecha de la semana a consultar (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna la carga horaria planificada de cada miembro para la semana."""
    return project_schedule_service.get_weekly_workload(
        db, project_id, current_user.id, week_start=week
    )
