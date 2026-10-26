import datetime as dt
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import Task, TaskOccurrence
from app.schemas import TaskCreate, TaskUpdate


def create_task(db: Session, user_id: int, task_in: TaskCreate) -> Task:
    """
    Crea una nueva tarea (común o del día) para el usuario y genera su ocurrencia inicial.
    """
    if task_in.kind == "daily" and not task_in.date:
        task_in.date = dt.date.today()

    task = Task(
        user_id=user_id,
        title=task_in.title,
        description=task_in.description,
        kind=task_in.kind,
        importance=task_in.importance,
        date=task_in.date,
        start_time=task_in.start_time,
        end_time=task_in.end_time,
        days_of_week=task_in.days_of_week if task_in.kind == "common" else None,
        is_active=True,
    )
    db.add(task)
    db.flush()

    # Determinar fecha para la primera ocurrencia
    target_date = task_in.date if task_in.kind == "daily" else dt.date.today()
    should_create_occ = True

    # Para tareas comunes, comprobar si hoy es un día permitido
    if task.kind == "common" and task.days_of_week:
        try:
            allowed_days = [int(x.strip()) for x in task.days_of_week.split(",") if x.strip()]
            if target_date.isoweekday() not in allowed_days:
                should_create_occ = False
        except ValueError:
            pass

    if should_create_occ:
        max_position = (
            db.query(func.max(TaskOccurrence.position))
            .join(Task)
            .filter(Task.user_id == user_id, TaskOccurrence.date == target_date)
            .scalar()
        ) or 0

        initial_occ = TaskOccurrence(
            task_id=task.id,
            date=target_date,
            status=task_in.initial_status,
            position=max_position + 1,
            start_time=task.start_time,
            end_time=task.end_time,
        )
        db.add(initial_occ)

    db.commit()
    db.refresh(task)
    return task


def get_task_by_id(db: Session, user_id: int, task_id: int) -> Optional[Task]:
    """Obtiene una tarea por su ID garantizando el aislamiento por usuario."""
    return (
        db.query(Task)
        .filter(Task.id == task_id, Task.user_id == user_id)
        .first()
    )


def update_task(db: Session, user_id: int, task_id: int, task_in: TaskUpdate) -> Optional[Task]:
    """Actualiza una tarea existente y gestiona reglas de periodicidad."""
    task = get_task_by_id(db, user_id, task_id)
    if not task:
        return None

    update_data = task_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    # Si se cambió a común, la fecha de definición pasa a ser None
    if task.kind == "common":
        task.date = None
    elif task.kind == "daily":
        task.days_of_week = None

    # Si cambiaron los días permitidos de una común, limpiar ocurrencias no iniciadas en días no permitidos
    if "days_of_week" in update_data and task.kind == "common" and task.days_of_week:
        try:
            allowed = [int(x.strip()) for x in task.days_of_week.split(",") if x.strip()]
            existing_unstarted = (
                db.query(TaskOccurrence)
                .filter(
                    TaskOccurrence.task_id == task.id,
                    TaskOccurrence.status == "not_started"
                )
                .all()
            )
            for occ in existing_unstarted:
                if occ.date.isoweekday() not in allowed:
                    db.delete(occ)
        except ValueError:
            pass

    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, user_id: int, task_id: int) -> bool:
    """Realiza un borrado lógico de la tarea para preservar el histórico."""
    task = get_task_by_id(db, user_id, task_id)
    if not task:
        return False

    task.is_active = False
    db.commit()
    return True
