import datetime as dt
from typing import List, Optional, Tuple
from sqlalchemy import or_, case
from sqlalchemy.orm import Session, joinedload

from app.models import Task, TaskOccurrence
from app.schemas import OccurrenceUpdate, OccurrenceReorder, TaskStatus, TaskImportance, TaskKind


def rollover_uncompleted_daily_tasks(db: Session, user_id: int) -> None:
    """
    Traspasa automáticamente al día de hoy las tareas del día puntuales
    que quedaron sin completar (status != 'done') en fechas pasadas.
    """
    today = dt.date.today()
    past_daily_tasks = (
        db.query(Task)
        .filter(
            Task.user_id == user_id,
            Task.kind == "daily",
            Task.is_active == True,
            Task.date < today,
        )
        .all()
    )

    if not past_daily_tasks:
        return

    for task in past_daily_tasks:
        past_occ = (
            db.query(TaskOccurrence)
            .filter(
                TaskOccurrence.task_id == task.id,
                TaskOccurrence.date == task.date
            )
            .first()
        )

        if past_occ and past_occ.status != "done":
            existing_today = (
                db.query(TaskOccurrence)
                .filter(
                    TaskOccurrence.task_id == task.id,
                    TaskOccurrence.date == today
                )
                .first()
            )
            if not existing_today:
                past_occ.date = today
                task.date = today
            else:
                task.date = today

    db.commit()


def ensure_occurrences(db: Session, user_id: int, start_date: dt.date, end_date: dt.date) -> None:
    """
    Generación perezosa (lazy) de TaskOccurrence:
    - Asegura que cada tarea 'common' activa tenga una ocurrencia para cada día permitido en [start_date, end_date].
    - Asegura que cada tarea 'daily' activa en dicho rango tenga su ocurrencia.
    """
    # 1. Tareas comunes activas del usuario
    common_tasks = (
        db.query(Task)
        .filter(Task.user_id == user_id, Task.kind == "common", Task.is_active == True)
        .all()
    )

    if common_tasks:
        task_ids = [t.id for t in common_tasks]
        existing_occs = (
            db.query(TaskOccurrence.task_id, TaskOccurrence.date)
            .filter(
                TaskOccurrence.task_id.in_(task_ids),
                TaskOccurrence.date >= start_date,
                TaskOccurrence.date <= end_date,
            )
            .all()
        )
        existing_set = set(existing_occs)

        curr = start_date
        while curr <= end_date:
            day_iso = curr.isoweekday()  # 1=Lunes, 2=Martes ... 7=Domingo
            for task in common_tasks:
                if task.days_of_week:
                    try:
                        allowed_days = [int(x.strip()) for x in task.days_of_week.split(",") if x.strip()]
                        if day_iso not in allowed_days:
                            continue
                    except ValueError:
                        pass

                if (task.id, curr) not in existing_set:
                    new_occ = TaskOccurrence(
                        task_id=task.id,
                        date=curr,
                        status="not_started",
                        position=task.id,
                        start_time=task.start_time,
                        end_time=task.end_time,
                    )
                    db.add(new_occ)
                    existing_set.add((task.id, curr))
            curr += dt.timedelta(days=1)

    # 2. Tareas del día activas del usuario en el rango
    daily_tasks = (
        db.query(Task)
        .filter(
            Task.user_id == user_id,
            Task.kind == "daily",
            Task.is_active == True,
            Task.date >= start_date,
            Task.date <= end_date,
        )
        .all()
    )

    if daily_tasks:
        daily_ids = [t.id for t in daily_tasks]
        existing_daily_occs = (
            db.query(TaskOccurrence.task_id, TaskOccurrence.date)
            .filter(
                TaskOccurrence.task_id.in_(daily_ids),
                TaskOccurrence.date >= start_date,
                TaskOccurrence.date <= end_date,
            )
            .all()
        )
        existing_daily_set = set(existing_daily_occs)

        for task in daily_tasks:
            if (task.id, task.date) not in existing_daily_set:
                new_occ = TaskOccurrence(
                    task_id=task.id,
                    date=task.date,
                    status="not_started",
                    position=0,
                    start_time=task.start_time,
                    end_time=task.end_time,
                )
                db.add(new_occ)
                existing_daily_set.add((task.id, task.date))

    db.commit()


def get_occurrences_in_range(
    db: Session,
    user_id: int,
    start: dt.date,
    end: dt.date,
    q: Optional[str] = None,
    status: Optional[TaskStatus] = None,
    importance: Optional[TaskImportance] = None,
    kind: Optional[TaskKind] = None,
) -> List[TaskOccurrence]:
    """
    Obtiene las ocurrencias filtradas y ordenadas para el rango solicitado.
    """
    # 1. Traspasar pendientes y asegurar generación lazy
    rollover_uncompleted_daily_tasks(db, user_id)
    ensure_occurrences(db, user_id, start, end)

    # 2. Consulta con JOIN
    query = (
        db.query(TaskOccurrence)
        .join(Task, TaskOccurrence.task_id == Task.id)
        .options(joinedload(TaskOccurrence.task))
        .filter(
            Task.user_id == user_id,
            Task.is_active == True,
            TaskOccurrence.date >= start,
            TaskOccurrence.date <= end,
        )
    )

    if status:
        query = query.filter(TaskOccurrence.status == status)

    if importance:
        query = query.filter(Task.importance == importance)

    if kind:
        query = query.filter(Task.kind == kind)

    if q and q.strip():
        search_term = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Task.title.ilike(search_term),
                Task.description.ilike(search_term)
            )
        )

    return (
        query
        .order_by(
            TaskOccurrence.date.asc(),
            TaskOccurrence.position.asc(),
            TaskOccurrence.start_time.is_(None),  # False (0) para tareas con hora, True (1) para NULL
            TaskOccurrence.start_time.asc(),
            case(
                (Task.importance == 'urgent', 1),
                (Task.importance == 'high', 2),
                (Task.importance == 'medium', 3),
                (Task.importance == 'low', 4),
                else_=5
            ).asc(),
            TaskOccurrence.id.asc()
        )
        .all()
    )


def update_occurrence(
    db: Session,
    user_id: int,
    occurrence_id: int,
    occ_in: OccurrenceUpdate,
) -> Tuple[Optional[TaskOccurrence], Optional[str]]:
    """
    Actualiza una ocurrencia. Retorna (ocurrencia, error_message).
    Si ocurre un error de validación o conflicto, retorna (None, "mensaje").
    """
    occ = (
        db.query(TaskOccurrence)
        .join(Task)
        .options(joinedload(TaskOccurrence.task))
        .filter(TaskOccurrence.id == occurrence_id, Task.user_id == user_id)
        .first()
    )
    if not occ:
        return None, "Ocurrencia no encontrada"

    fields_set = occ_in.model_fields_set

    if "status" in fields_set and occ_in.status is not None:
        occ.status = occ_in.status

    if "start_time" in fields_set:
        occ.start_time = occ_in.start_time

    if "end_time" in fields_set:
        occ.end_time = occ_in.end_time

    if "date" in fields_set and occ_in.date is not None and occ_in.date != occ.date:
        new_date = occ_in.date
        existing = (
            db.query(TaskOccurrence)
            .filter(
                TaskOccurrence.task_id == occ.task_id,
                TaskOccurrence.date == new_date,
                TaskOccurrence.id != occ.id
            )
            .first()
        )
        if existing:
            return None, "Ya existe una ocurrencia para esta tarea en la fecha indicada"

        occ.date = new_date
        if occ.task.kind == "daily":
            occ.task.date = new_date

    db.commit()
    db.refresh(occ)
    return occ, None


def reorder_occurrences(db: Session, user_id: int, reorder_in: OccurrenceReorder) -> None:
    """Actualiza la posición ordinal de los post-its para una fecha."""
    for position, occ_id in enumerate(reorder_in.ordered_ids):
        occ = (
            db.query(TaskOccurrence)
            .join(Task)
            .filter(
                TaskOccurrence.id == occ_id,
                TaskOccurrence.date == reorder_in.date,
                Task.user_id == user_id
            )
            .first()
        )
        if occ:
            occ.position = position

    db.commit()
