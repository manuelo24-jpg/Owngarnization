from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.deps import get_db, get_current_user
from app.models import User, Project, ProjectMember, ProjectTask, ProjectColumn, TaskOccurrence
from app.schemas import UserSpaceUpdate, SpacesSummaryResponse, SpaceSummaryPersonal, SpaceSummaryProjects
from app.services.occurrence_service import get_user_today, ensure_occurrences

router = APIRouter(prefix="/api", tags=["Espacios"])


@router.patch("/me/space", status_code=status.HTTP_200_OK)
def update_user_space(
    payload: UserSpaceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualiza el último espacio o proyecto seleccionado por el usuario."""
    if payload.last_space is not None:
        current_user.last_space = payload.last_space
    if payload.last_project_id is not None:
        # Validar que sea miembro de dicho proyecto
        is_member = (
            db.query(ProjectMember)
            .filter(
                ProjectMember.project_id == payload.last_project_id,
                ProjectMember.user_id == current_user.id
            )
            .first()
        )
        if is_member:
            current_user.last_project_id = payload.last_project_id

    db.commit()
    return {
        "status": "ok",
        "last_space": current_user.last_space,
        "last_project_id": current_user.last_project_id
    }


@router.get("/spaces/summary", response_model=SpacesSummaryResponse)
def get_spaces_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retorna métricas resumen para alimentar las tarjetas del selector de espacios:
    - Organización personal: tareas hoy y hechas hoy
    - Proyectos: proyectos activos y tareas abiertas asignadas
    """
    # 1. Personal
    today = get_user_today(db, current_user.id)
    ensure_occurrences(db, current_user.id, today, today)

    personal_occs = (
        db.query(TaskOccurrence)
        .join(TaskOccurrence.task)
        .filter(
            TaskOccurrence.date == today,
            TaskOccurrence.task.has(user_id=current_user.id, is_active=True)
        )
        .all()
    )
    today_total = len(personal_occs)
    today_done = sum(1 for occ in personal_occs if occ.status == "done")

    # 2. Proyectos
    active_projects_count = (
        db.query(func.count(Project.id))
        .join(ProjectMember, Project.id == ProjectMember.project_id)
        .filter(
            ProjectMember.user_id == current_user.id,
            Project.is_active == True,
            Project.is_archived == False
        )
        .scalar() or 0
    )

    # Tareas de proyecto asignadas al usuario y no finalizadas
    assigned_open_tasks = (
        db.query(func.count(ProjectTask.id))
        .join(ProjectTask.assignees)
        .join(ProjectColumn, ProjectTask.column_id == ProjectColumn.id)
        .filter(
            User.id == current_user.id,
            ProjectTask.is_active == True,
            ProjectColumn.is_done == False
        )
        .scalar() or 0
    )

    return SpacesSummaryResponse(
        personal=SpaceSummaryPersonal(
            today_total=today_total,
            today_done=today_done
        ),
        projects=SpaceSummaryProjects(
            active_projects=active_projects_count,
            assigned_tasks=assigned_open_tasks
        )
    )
