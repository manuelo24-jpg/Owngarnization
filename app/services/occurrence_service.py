import datetime as dt
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import List, Optional, Tuple
from sqlalchemy import or_, case
from sqlalchemy.orm import Session, joinedload

from app.models import User, Task, TaskOccurrence
from app.schemas import OccurrenceUpdate, OccurrenceReorder, TaskStatus, TaskImportance, TaskKind


def get_user_today(
    db: Session,
    user_id: int,
    now_utc: Optional[dt.datetime] = None,
    user_timezone: Optional[str] = None,
) -> dt.date:
    """Calcula la fecha de 'hoy' en la zona horaria IANA del usuario."""
    tz_name = user_timezone
    if not tz_name:
        user_tz = db.query(User.timezone).filter(User.id == user_id).first()
        tz_name = user_tz[0] if user_tz and user_tz[0] else "Europe/Madrid"
    try:
        tz = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, KeyError, ValueError):
        tz = ZoneInfo("Europe/Madrid")
    ref_utc = now_utc or dt.datetime.now(dt.timezone.utc)
    if ref_utc.tzinfo is None:
        ref_utc = ref_utc.replace(tzinfo=dt.timezone.utc)
    return ref_utc.astimezone(tz).date()


def rollover_uncompleted_daily_tasks(
    db: Session,
    user_id: int,
    now_utc: Optional[dt.datetime] = None,
    user_timezone: Optional[str] = None,
) -> None:
    """
    Traspasa automáticamente al día de hoy (en la zona horaria del usuario)
    las tareas del día puntuales que quedaron sin completar en fechas pasadas.
    Optimizado en consultas por lotes O(1) para máxima escalabilidad (evita N+1 queries).
    """
    today = get_user_today(db, user_id, now_utc, user_timezone=user_timezone)

    # 1. Obtener de un solo golpe las ocurrencias pasadas incompletas junto con su tarea
    pending_past_pairs = (
        db.query(TaskOccurrence, Task)
        .join(Task, TaskOccurrence.task_id == Task.id)
        .filter(
            Task.user_id == user_id,
            Task.kind == "daily",
            Task.is_active == True,
            Task.date < today,
            TaskOccurrence.date == Task.date,
            TaskOccurrence.status != "done",
        )
        .all()
    )

    if not pending_past_pairs:
        return

    # 2. Consultar en una sola consulta IN si ya existe ocurrencia para hoy en esas tareas
    task_ids = [task.id for _, task in pending_past_pairs]
    existing_today_task_ids = set(
        r[0]
        for r in db.query(TaskOccurrence.task_id)
        .filter(
            TaskOccurrence.task_id.in_(task_ids),
            TaskOccurrence.date == today
        )
        .all()
    )

    modified = False
    for past_occ, task in pending_past_pairs:
        if task.id not in existing_today_task_ids:
            past_occ.date = today
            task.date = today
            existing_today_task_ids.add(task.id)
        else:
            task.date = today
        modified = True

    if modified:
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

    # Commit solo si hubo nuevas inserciones, evitando bloqueos innecesarios
    if db.new:
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
    user_timezone: Optional[str] = None,
) -> List[TaskOccurrence]:
    """
    Obtiene las ocurrencias filtradas y ordenadas para el rango solicitado.
    """
    # 1. Traspasar pendientes y asegurar generación lazy
    rollover_uncompleted_daily_tasks(db, user_id, user_timezone=user_timezone)
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
            case((TaskOccurrence.manual_order == True, 0), else_=1).asc(),
            case((TaskOccurrence.manual_order == True, TaskOccurrence.position), else_=0).asc(),
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
        if occ_in.start_time != occ.start_time:
            occ.reminder_sent_at = None
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
        occ.reminder_sent_at = None
        if occ.task.kind == "daily":
            occ.task.date = new_date

    db.commit()
    db.refresh(occ)
    return occ, None


def reorder_occurrences(db: Session, user_id: int, reorder_in: OccurrenceReorder) -> None:
    """Actualiza la posición ordinal de los post-its para una fecha en una sola consulta por lotes."""
    if not reorder_in.ordered_ids:
        return

    occs = (
        db.query(TaskOccurrence)
        .join(Task)
        .filter(
            TaskOccurrence.id.in_(reorder_in.ordered_ids),
            TaskOccurrence.date == reorder_in.date,
            Task.user_id == user_id
        )
        .all()
    )

    occ_map = {o.id: o for o in occs}
    modified = False
    for position, occ_id in enumerate(reorder_in.ordered_ids):
        occ = occ_map.get(occ_id)
        if occ:
            occ.position = position
            occ.manual_order = True
            modified = True

    if modified:
        db.commit()
