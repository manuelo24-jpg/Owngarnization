from datetime import datetime, timezone, date, time
from typing import List, Optional, Tuple, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models import (
    Project,
    ProjectMember,
    ProjectColumn,
    ProjectTask,
    ProjectTaskAssignee,
    ProjectRole,
    User
)
from app.schemas import (
    ProjectTaskCreate,
    ProjectTaskUpdate,
    ProjectTaskMove,
    ScheduleOverlapWarning
)
from app.services.project_service import require_member, require_permission, get_member


def check_schedule_overlaps(
    db: Session,
    project_id: int,
    task_date: Optional[date],
    start_time: Optional[time],
    end_time: Optional[time],
    assignee_ids: List[int],
    exclude_task_id: Optional[int] = None
) -> List[dict]:
    """
    Detecta si alguno de los miembros asignados tiene otra tarea del proyecto
    en conflicto horario en la misma fecha (solape: start1 < end2 and start2 < end1).
    Devuelve lista de advertencias informativas (no bloqueantes).
    """
    if not task_date or not start_time or not end_time or not assignee_ids:
        return []

    warnings = []
    # Buscar tareas asignadas a estos usuarios en esa fecha con horario
    query = (
        db.query(ProjectTask, ProjectTaskAssignee, User)
        .join(ProjectTaskAssignee, ProjectTask.id == ProjectTaskAssignee.task_id)
        .join(User, ProjectTaskAssignee.user_id == User.id)
        .filter(
            ProjectTask.project_id == project_id,
            ProjectTask.is_active == True,
            ProjectTask.date == task_date,
            ProjectTask.start_time != None,
            ProjectTask.end_time != None,
            ProjectTaskAssignee.user_id.in_(assignee_ids)
        )
    )
    if exclude_task_id:
        query = query.filter(ProjectTask.id != exclude_task_id)

    other_tasks = query.all()
    for other_task, assignee_rel, user in other_tasks:
        # Condición de solape
        if start_time < other_task.end_time and other_task.start_time < end_time:
            warnings.append({
                "task_id": exclude_task_id or 0,
                "user_id": user.id,
                "username": user.username,
                "conflicting_task_id": other_task.id,
                "conflicting_title": other_task.title,
                "date": task_date,
                "start_time": other_task.start_time,
                "end_time": other_task.end_time,
            })
    return warnings


def _format_task_dict(db: Session, task: ProjectTask, warnings: Optional[List[dict]] = None) -> dict:
    """Serializa la tarea con sus relaciones completas para la API."""
    assignees_data = []
    assignee_ids = []
    for u in task.assignees:
        assignee_ids.append(u.id)
        mem = get_member(db, task.project_id, u.id)
        assignees_data.append({
            "id": mem.id if mem else 0,
            "user_id": u.id,
            "username": u.username,
            "email": u.email,
            "permission": mem.permission if mem else "member",
            "role_name": mem.role.name if (mem and mem.role) else None,
            "role_color": mem.role.color if (mem and mem.role) else None,
        })

    return {
        "id": task.id,
        "project_id": task.project_id,
        "column_id": task.column_id,
        "title": task.title,
        "description": task.description,
        "priority": task.priority,
        "position": task.position,
        "date": task.date,
        "start_time": task.start_time,
        "end_time": task.end_time,
        "due_date": task.due_date,
        "estimated_minutes": task.estimated_minutes,
        "role_id": task.role_id,
        "role_name": task.role.name if task.role else None,
        "role_color": task.role.color if task.role else None,
        "completed_at": task.completed_at,
        "created_by": task.created_by,
        "assignee_ids": assignee_ids,
        "assignees": assignees_data,
        "overlap_warnings": warnings or [],
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }


def create_task(db: Session, project_id: int, user_id: int, data: ProjectTaskCreate) -> dict:
    """Crea una tarea en el proyecto (requiere al menos permiso member)."""
    require_permission(db, project_id, user_id, "member")

    col = db.query(ProjectColumn).filter(
        ProjectColumn.id == data.column_id,
        ProjectColumn.project_id == project_id
    ).first()
    if not col:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Columna no encontrada en el proyecto")

    if data.role_id:
        role = db.query(ProjectRole).filter(
            ProjectRole.id == data.role_id,
            ProjectRole.project_id == project_id
        ).first()
        if not role:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El rol no pertenece a este proyecto")

    # Validar que todos los asignados sean miembros
    if data.assignee_ids:
        members_count = db.query(func.count(ProjectMember.id)).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id.in_(data.assignee_ids)
        ).scalar()
        if members_count != len(set(data.assignee_ids)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solo se puede asignar tareas a miembros registrados en el proyecto"
            )

    max_pos = db.query(func.max(ProjectTask.position)).filter(
        ProjectTask.column_id == col.id,
        ProjectTask.is_active == True
    ).scalar() or 0

    now_utc = datetime.now(timezone.utc)
    completed_at = now_utc if col.is_done else None

    task = ProjectTask(
        project_id=project_id,
        column_id=col.id,
        title=data.title.strip(),
        description=data.description,
        priority=data.priority,
        position=max_pos + 1,
        is_active=True,
        created_by=user_id,
        date=data.date,
        start_time=data.start_time,
        end_time=data.end_time,
        due_date=data.due_date,
        estimated_minutes=data.estimated_minutes,
        role_id=data.role_id,
        completed_at=completed_at
    )
    db.add(task)
    db.flush()

    # Añadir asignados
    if data.assignee_ids:
        for a_uid in set(data.assignee_ids):
            db.add(ProjectTaskAssignee(task_id=task.id, user_id=a_uid))

    db.commit()
    db.refresh(task)

    warnings = check_schedule_overlaps(
        db=db,
        project_id=project_id,
        task_date=data.date,
        start_time=data.start_time,
        end_time=data.end_time,
        assignee_ids=data.assignee_ids or [],
        exclude_task_id=task.id
    )
    return _format_task_dict(db, task, warnings)


def get_task(db: Session, project_id: int, task_id: int, user_id: int) -> dict:
    """Obtiene el detalle completo de una tarea."""
    require_member(db, project_id, user_id)
    task = db.query(ProjectTask).filter(
        ProjectTask.id == task_id,
        ProjectTask.project_id == project_id,
        ProjectTask.is_active == True
    ).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada")

    warnings = check_schedule_overlaps(
        db=db,
        project_id=project_id,
        task_date=task.date,
        start_time=task.start_time,
        end_time=task.end_time,
        assignee_ids=[u.id for u in task.assignees],
        exclude_task_id=task.id
    )
    return _format_task_dict(db, task, warnings)


def update_task(db: Session, project_id: int, task_id: int, user_id: int, data: ProjectTaskUpdate) -> dict:
    """Actualiza campos de la tarea (requiere al menos member)."""
    require_permission(db, project_id, user_id, "member")
    task = db.query(ProjectTask).filter(
        ProjectTask.id == task_id,
        ProjectTask.project_id == project_id,
        ProjectTask.is_active == True
    ).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada")

    if data.title is not None:
        task.title = data.title.strip()
    if data.description is not None:
        task.description = data.description
    if data.priority is not None:
        task.priority = data.priority

    # Cambio de columna
    if data.column_id is not None and data.column_id != task.column_id:
        target_col = db.query(ProjectColumn).filter(
            ProjectColumn.id == data.column_id,
            ProjectColumn.project_id == project_id
        ).first()
        if not target_col:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Columna destino no válida")
        task.column_id = target_col.id
        if target_col.is_done:
            task.completed_at = datetime.now(timezone.utc)
        else:
            task.completed_at = None

    if data.position is not None:
        task.position = data.position

    # Horario
    if data.date is not None:
        task.date = data.date
    if data.start_time is not None:
        task.start_time = data.start_time
    if data.end_time is not None:
        task.end_time = data.end_time

    if data.due_date is not None:
        task.due_date = data.due_date
    if data.estimated_minutes is not None:
        task.estimated_minutes = data.estimated_minutes

    if data.role_id is not None:
        if data.role_id > 0:
            role = db.query(ProjectRole).filter(
                ProjectRole.id == data.role_id,
                ProjectRole.project_id == project_id
            ).first()
            if not role:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rol inválido")
            task.role_id = data.role_id
        else:
            task.role_id = None

    # Asignados
    if data.assignee_ids is not None:
        if data.assignee_ids:
            members_count = db.query(func.count(ProjectMember.id)).filter(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id.in_(data.assignee_ids)
            ).scalar()
            if members_count != len(set(data.assignee_ids)):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Todos los asignados deben ser miembros")

        # Reemplazar asignados
        db.query(ProjectTaskAssignee).filter(ProjectTaskAssignee.task_id == task.id).delete()
        for a_uid in set(data.assignee_ids):
            db.add(ProjectTaskAssignee(task_id=task.id, user_id=a_uid))

    db.commit()
    db.refresh(task)

    current_assignee_ids = [u.id for u in task.assignees]
    warnings = check_schedule_overlaps(
        db=db,
        project_id=project_id,
        task_date=task.date,
        start_time=task.start_time,
        end_time=task.end_time,
        assignee_ids=current_assignee_ids,
        exclude_task_id=task.id
    )
    return _format_task_dict(db, task, warnings)


def move_task(db: Session, project_id: int, user_id: int, data: ProjectTaskMove) -> dict:
    """Mueve una tarea de columna o de posición dentro del tablero."""
    require_permission(db, project_id, user_id, "member")

    task = db.query(ProjectTask).filter(
        ProjectTask.id == data.task_id,
        ProjectTask.project_id == project_id,
        ProjectTask.is_active == True
    ).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada")

    target_col = db.query(ProjectColumn).filter(
        ProjectColumn.id == data.column_id,
        ProjectColumn.project_id == project_id
    ).first()
    if not target_col:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Columna destino no válida")

    is_same_column = (task.column_id == target_col.id)
    task.column_id = target_col.id
    task.position = data.position

    if target_col.is_done:
        if not task.completed_at:
            task.completed_at = datetime.now(timezone.utc)
    else:
        task.completed_at = None

    db.commit()
    db.refresh(task)
    return _format_task_dict(db, task, [])


def delete_task(db: Session, project_id: int, task_id: int, user_id: int) -> None:
    """Eliminación lógica de tarea (requiere member o superior)."""
    require_permission(db, project_id, user_id, "member")
    task = db.query(ProjectTask).filter(
        ProjectTask.id == task_id,
        ProjectTask.project_id == project_id,
        ProjectTask.is_active == True
    ).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada")

    task.is_active = False
    db.commit()

