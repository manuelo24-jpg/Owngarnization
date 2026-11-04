from datetime import date, timedelta, datetime
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import (
    Project,
    ProjectMember,
    ProjectTask,
    ProjectTaskAssignee,
    User
)
from app.services.project_service import require_member
from app.services.project_task_service import _format_task_dict, check_schedule_overlaps


def get_project_schedule(
    db: Session,
    project_id: int,
    user_id: int,
    start_date: date,
    end_date: date,
    by_person: bool = False
) -> dict:
    """
    Retorna las tareas con horario dentro del rango de fechas especificado,
    evaluando y anotando posibles solapes de agenda por miembro.
    """
    require_member(db, project_id, user_id)

    tasks = (
        db.query(ProjectTask)
        .filter(
            ProjectTask.project_id == project_id,
            ProjectTask.is_active == True,
            ProjectTask.date >= start_date,
            ProjectTask.date <= end_date,
            ProjectTask.start_time != None
        )
        .order_by(ProjectTask.date.asc(), ProjectTask.start_time.asc())
        .all()
    )

    formatted_tasks = []
    by_person_map: Dict[int, List[dict]] = {}

    # Inicializar mapa para todos los miembros del proyecto
    members = db.query(ProjectMember).filter(ProjectMember.project_id == project_id).all()
    for m in members:
        by_person_map[m.user_id] = []

    for t in tasks:
        assignee_ids = [u.id for u in t.assignees]
        overlaps = check_schedule_overlaps(
            db=db,
            project_id=project_id,
            task_date=t.date,
            start_time=t.start_time,
            end_time=t.end_time,
            assignee_ids=assignee_ids,
            exclude_task_id=t.id
        )
        t_dict = _format_task_dict(db, t, overlaps)
        schedule_item = {
            "task": t_dict,
            "overlaps": overlaps
        }
        formatted_tasks.append(schedule_item)

        if assignee_ids:
            for uid in assignee_ids:
                if uid in by_person_map:
                    by_person_map[uid].append(schedule_item)
                else:
                    by_person_map[uid] = [schedule_item]
        else:
            # Tarea sin asignar (clave 0)
            if 0 not in by_person_map:
                by_person_map[0] = []
            by_person_map[0].append(schedule_item)

    return {
        "start": start_date,
        "end": end_date,
        "tasks": formatted_tasks,
        "by_person": by_person_map
    }


def get_weekly_workload(
    db: Session,
    project_id: int,
    user_id: int,
    week_start: Optional[date] = None
) -> dict:
    """
    Calcula la carga horaria planificada de cada miembro del proyecto
    para la semana especificada comparada con su capacidad semanal (weekly_hours).
    """
    require_member(db, project_id, user_id)

    if not week_start:
        today = date.today()
        week_start = today - timedelta(days=today.weekday())  # Lunes de esta semana
    else:
        # Asegurar que comience en lunes
        week_start = week_start - timedelta(days=week_start.weekday())

    week_end = week_start + timedelta(days=6)  # Domingo

    # Obtener todos los miembros
    members = (
        db.query(ProjectMember, User)
        .join(User, ProjectMember.user_id == User.id)
        .filter(ProjectMember.project_id == project_id)
        .all()
    )

    workload_members = []
    for member, user in members:
        # Buscar tareas asignadas a este miembro en la semana
        tasks = (
            db.query(ProjectTask)
            .join(ProjectTaskAssignee, ProjectTask.id == ProjectTaskAssignee.task_id)
            .filter(
                ProjectTask.project_id == project_id,
                ProjectTask.is_active == True,
                ProjectTaskAssignee.user_id == user.id,
                ProjectTask.date >= week_start,
                ProjectTask.date <= week_end
            )
            .all()
        )

        planned_minutes = 0
        for t in tasks:
            if t.estimated_minutes:
                planned_minutes += t.estimated_minutes
            elif t.start_time and t.end_time:
                # Calcular diferencia en minutos
                t1 = datetime.combine(date.min, t.start_time)
                t2 = datetime.combine(date.min, t.end_time)
                diff_min = int((t2 - t1).total_seconds() / 60)
                if diff_min > 0:
                    planned_minutes += diff_min

        workload_members.append({
            "user_id": user.id,
            "username": user.username,
            "weekly_hours": member.weekly_hours,
            "planned_hours": round(planned_minutes / 60.0, 1),
            "task_count": len(tasks),
        })

    return {
        "week_start": week_start,
        "week_end": week_end,
        "members": workload_members
    }

