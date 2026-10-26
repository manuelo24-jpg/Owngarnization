import datetime as dt
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, func
from sqlalchemy.orm import Session, joinedload

from app.deps import get_db, get_current_user
from app.models import User, Task, TaskOccurrence
from app.schemas import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    OccurrenceResponse,
    OccurrenceUpdate,
    OccurrenceReorder,
    TaskStatus,
    TaskImportance,
    TaskKind
)

router = APIRouter(prefix="/api", tags=["Tareas"])


def _rollover_uncompleted_daily_tasks(db: Session, user_id: int) -> None:
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
        # Buscar la ocurrencia original
        past_occ = (
            db.query(TaskOccurrence)
            .filter(
                TaskOccurrence.task_id == task.id,
                TaskOccurrence.date == task.date
            )
            .first()
        )

        # Si no está completada (not_started o in_progress), mover a hoy
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


def _ensure_occurrences(db: Session, user_id: int, start_date: dt.date, end_date: dt.date) -> None:
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
        # Consultar ocurrencias existentes para las tareas comunes en el rango
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

        # Crear las que falten
        curr = start_date
        while curr <= end_date:
            day_iso = curr.isoweekday()  # 1=Lunes, 2=Martes ... 7=Domingo
            for task in common_tasks:
                # Si la tarea especifica días de la semana, comprobar si hoy aplica
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


# --- ENDPOINTS ---

@router.get("/occurrences", response_model=List[OccurrenceResponse])
def get_occurrences(
    start: dt.date = Query(..., description="Fecha inicial del rango (YYYY-MM-DD)"),
    end: dt.date = Query(..., description="Fecha final del rango (YYYY-MM-DD)"),
    q: Optional[str] = Query(None, description="Búsqueda por texto en título o descripción"),
    status: Optional[TaskStatus] = Query(None, description="Filtrar por estado"),
    importance: Optional[TaskImportance] = Query(None, description="Filtrar por importancia"),
    kind: Optional[TaskKind] = Query(None, description="Filtrar por tipo (common o daily)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Obtiene las ocurrencias de tareas en un rango de fechas con búsqueda y filtros.
    Traspasa al día de hoy tareas del día incompletas de fechas pasadas.
    Genera automáticamente las ocurrencias para tareas comunes (según días permitidos) y del día.
    """
    if end < start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La fecha de fin debe ser posterior o igual a la fecha de inicio"
        )

    # Limitar rango máximo a 370 días para proteger rendimiento
    if (end - start).days > 370:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El rango de fechas no puede superar un año"
        )

    # 1. Traspasar tareas pendientes del pasado a hoy
    _rollover_uncompleted_daily_tasks(db, current_user.id)

    # 2. Generación lazy
    _ensure_occurrences(db, current_user.id, start, end)


    # Consulta con JOIN y filtros
    query = (
        db.query(TaskOccurrence)
        .join(Task, TaskOccurrence.task_id == Task.id)
        .options(joinedload(TaskOccurrence.task))
        .filter(
            Task.user_id == current_user.id,
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

    occurrences = (
        query
        .order_by(
            TaskOccurrence.date.asc(),
            TaskOccurrence.position.asc(),
            TaskOccurrence.id.asc()
        )
        .all()
    )

    return occurrences


@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    task_in: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Crea una nueva tarea (común o del día) y genera su ocurrencia inicial.
    """
    if task_in.kind == "daily" and not task_in.date:
        task_in.date = dt.date.today()

    task = Task(
        user_id=current_user.id,
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
            .filter(Task.user_id == current_user.id, TaskOccurrence.date == target_date)
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


@router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Obtiene el detalle completo de una tarea del usuario."""
    task = (
        db.query(Task)
        .filter(Task.id == task_id, Task.user_id == current_user.id)
        .first()
    )
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tarea no encontrada"
        )
    return task


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    task_in: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Actualiza los campos de una tarea existente."""
    task = (
        db.query(Task)
        .filter(Task.id == task_id, Task.user_id == current_user.id)
        .first()
    )
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tarea no encontrada"
        )

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



@router.delete("/tasks/{task_id}")
def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Elimina/desactiva una tarea para el usuario (borrado lógico para preservar histórico).
    """
    task = (
        db.query(Task)
        .filter(Task.id == task_id, Task.user_id == current_user.id)
        .first()
    )
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tarea no encontrada"
        )

    task.is_active = False
    db.commit()
    return {"message": "Tarea eliminada correctamente"}


@router.patch("/api/occurrences/{occurrence_id}", response_model=OccurrenceResponse)
@router.patch("/occurrences/{occurrence_id}", response_model=OccurrenceResponse)
def update_occurrence(
    occurrence_id: int,
    occ_in: OccurrenceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Actualiza el estado, horario o fecha de una ocurrencia específica.
    Permite mover tareas entre días en la vista de calendario.
    """
    occ = (
        db.query(TaskOccurrence)
        .join(Task)
        .options(joinedload(TaskOccurrence.task))
        .filter(TaskOccurrence.id == occurrence_id, Task.user_id == current_user.id)
        .first()
    )
    if not occ:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ocurrencia no encontrada"
        )

    fields_set = occ_in.model_fields_set

    if "status" in fields_set and occ_in.status is not None:
        occ.status = occ_in.status

    if "start_time" in fields_set:
        occ.start_time = occ_in.start_time

    if "end_time" in fields_set:
        occ.end_time = occ_in.end_time

    if "date" in fields_set and occ_in.date is not None and occ_in.date != occ.date:
        new_date = occ_in.date
        # Verificar si ya existe ocurrencia para esa tarea en la fecha destino
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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe una ocurrencia para esta tarea en la fecha indicada"
            )

        occ.date = new_date
        # Si es una tarea puntual (daily), actualizar también la fecha de la tarea
        if occ.task.kind == "daily":
            occ.task.date = new_date

    db.commit()
    db.refresh(occ)
    return occ


@router.post("/occurrences/reorder")
def reorder_occurrences(
    reorder_in: OccurrenceReorder,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Guarda el orden manual de los post-its tras drag & drop para una fecha concreta.
    """
    for position, occ_id in enumerate(reorder_in.ordered_ids):
        occ = (
            db.query(TaskOccurrence)
            .join(Task)
            .filter(
                TaskOccurrence.id == occ_id,
                TaskOccurrence.date == reorder_in.date,
                Task.user_id == current_user.id
            )
            .first()
        )
        if occ:
            occ.position = position

    db.commit()
    return {"message": "Orden actualizado correctamente"}
