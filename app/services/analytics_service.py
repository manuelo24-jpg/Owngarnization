import datetime as dt
from typing import Optional, List, Dict
from sqlalchemy import or_, and_, func
from sqlalchemy.orm import Session

from app.models import User, Task, TaskOccurrence, Project, ProjectTask, ProjectColumn, ProjectMember
from app.schemas import (
    DailySummaryResponse,
    DailySummaryImportance,
    DailySummaryKind,
    DailyTaskBrief,
    DailyCarryOverResponse,
    WeeklySummaryResponse,
    WeeklyDaySummary,
    TaskHistoryItem,
    HistoryResponse,
)
from app.services.occurrence_service import get_user_today, ensure_occurrences

DAY_NAMES_ES = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
IMPORTANCE_LEVELS = ["urgent", "high", "medium", "low"]


def get_user_streak(db: Session, user_id: int, as_of_date: Optional[dt.date] = None) -> int:
    """
    Calcula la racha ininterrumpida de días consecutivos con al menos una tarea completada.
    Si hoy aún no tiene tareas completadas, la racha de ayer se mantiene activa como racha actual.
    """
    today = as_of_date or get_user_today(db, user_id)
    earliest = today - dt.timedelta(days=365)

    # 1. Fechas con ocurrencias personales finalizadas
    completed_occ_dates = (
        db.query(TaskOccurrence.date)
        .join(Task)
        .filter(
            Task.user_id == user_id,
            TaskOccurrence.status == "done",
            TaskOccurrence.date >= earliest,
            TaskOccurrence.date <= today,
        )
        .distinct()
        .all()
    )
    active_dates = {row[0] for row in completed_occ_dates}

    # 2. Fechas con tareas de proyecto completadas por el usuario
    completed_proj_tasks = (
        db.query(ProjectTask.date, ProjectTask.completed_at)
        .join(ProjectColumn, ProjectTask.column_id == ProjectColumn.id)
        .join(ProjectMember, ProjectMember.project_id == ProjectTask.project_id)
        .filter(
            ProjectMember.user_id == user_id,
            or_(ProjectColumn.is_done == True, ProjectTask.completed_at.isnot(None)),
            ProjectTask.is_active == True,
        )
        .all()
    )
    for p_date, p_completed_at in completed_proj_tasks:
        d = p_date
        if not d and p_completed_at:
            d = p_completed_at.date()
        if d and earliest <= d <= today:
            active_dates.add(d)

    if not active_dates:
        return 0

    # Si hoy tiene al menos una tarea completada, contar desde hoy hacia atrás
    if today in active_dates:
        streak = 0
        curr = today
        while curr in active_dates:
            streak += 1
            curr -= dt.timedelta(days=1)
        return streak

    # Si hoy aún no tiene tareas hechas, comprobar si ayer sí tuvo (la racha sigue viva hoy)
    yesterday = today - dt.timedelta(days=1)
    if yesterday in active_dates:
        streak = 0
        curr = yesterday
        while curr in active_dates:
            streak += 1
            curr -= dt.timedelta(days=1)
        return streak

    return 0


def get_daily_summary(
    db: Session,
    user_id: int,
    target_date: Optional[dt.date] = None
) -> DailySummaryResponse:
    """
    Genera el resumen de productividad diario ("Cierre del Día"):
    - Ratio y porcentaje de completadas
    - Estimación de minutos totales vs completados
    - Desglose por importancia y tipo
    - Mensaje motivacional dinámico
    - Racha actual
    """
    ref_date = target_date or get_user_today(db, user_id)
    ensure_occurrences(db, user_id, ref_date, ref_date)

    occs = (
        db.query(TaskOccurrence)
        .join(Task)
        .filter(
            Task.user_id == user_id,
            Task.is_active == True,
            TaskOccurrence.date == ref_date,
        )
        .order_by(TaskOccurrence.position.asc(), TaskOccurrence.id.asc())
        .all()
    )

    total_tasks = len(occs)
    completed_tasks = sum(1 for o in occs if o.status == "done")
    in_progress_tasks = sum(1 for o in occs if o.status == "in_progress")
    not_started_tasks = sum(1 for o in occs if o.status == "not_started")
    completion_rate = int(round((completed_tasks / total_tasks * 100))) if total_tasks > 0 else 0

    est_minutes_total = 0
    est_minutes_completed = 0

    by_importance: Dict[str, DailySummaryImportance] = {
        lvl: DailySummaryImportance(total=0, completed=0) for lvl in IMPORTANCE_LEVELS
    }
    by_kind: Dict[str, DailySummaryKind] = {
        "common": DailySummaryKind(total=0, completed=0),
        "daily": DailySummaryKind(total=0, completed=0),
    }

    task_briefs: List[DailyTaskBrief] = []

    for o in occs:
        st = o.start_time or o.task.start_time
        et = o.end_time or o.task.end_time
        duration = 0
        if st and et:
            duration = (et.hour * 60 + et.minute) - (st.hour * 60 + st.minute)
            if duration < 0:
                duration = 0
        est_minutes_total += duration
        if o.status == "done":
            est_minutes_completed += duration

        imp = o.task.importance if o.task.importance in by_importance else "medium"
        by_importance[imp].total += 1
        if o.status == "done":
            by_importance[imp].completed += 1

        k = o.task.kind if o.task.kind in by_kind else "daily"
        by_kind[k].total += 1
        if o.status == "done":
            by_kind[k].completed += 1

        task_briefs.append(
            DailyTaskBrief(
                id=o.id,
                task_id=o.task_id,
                title=o.task.title,
                importance=imp,
                kind=k,
                status=o.status,
                start_time=st,
                end_time=et,
            )
        )

    # Mensaje motivacional
    if total_tasks == 0:
        motivational_message = "No hay tareas programadas para este día. ¡Disfruta de tu descanso o planifica nuevas metas! ✨"
    elif completion_rate == 100:
        motivational_message = "¡Día impecable! Has completado el 100% de tus objetivos. ¡Enhorabuena! 🎉"
    elif completion_rate >= 80:
        motivational_message = "¡Excelente rendimiento! Has resuelto casi la totalidad de tus tareas. 💪"
    elif completion_rate >= 50:
        motivational_message = "¡Buen progreso! Has superado la mitad de tus tareas de hoy. 👍"
    elif completed_tasks > 0:
        motivational_message = "Has dado los primeros pasos. ¡Ánimo para cerrar las tareas pendientes! ⏳"
    else:
        motivational_message = "Tienes tareas esperando por ti hoy. ¡Un paso a la vez y a por ellas! 🚀"

    current_streak = get_user_streak(db, user_id, ref_date)

    return DailySummaryResponse(
        date=ref_date,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        in_progress_tasks=in_progress_tasks,
        not_started_tasks=not_started_tasks,
        completion_rate=completion_rate,
        estimated_minutes_total=est_minutes_total,
        estimated_minutes_completed=est_minutes_completed,
        motivational_message=motivational_message,
        current_streak=current_streak,
        by_importance=by_importance,
        by_kind=by_kind,
        tasks=task_briefs,
    )


def carry_over_uncompleted_daily_tasks(
    db: Session,
    user_id: int,
    source_date: dt.date,
    target_date: Optional[dt.date] = None,
) -> DailyCarryOverResponse:
    """
    Pospone / traspasa las tareas puntuales del día que no fueron completadas en `source_date`
    directamente a `target_date` (por defecto el día siguiente).
    """
    dest_date = target_date or (source_date + dt.timedelta(days=1))
    if dest_date <= source_date:
        dest_date = source_date + dt.timedelta(days=1)

    uncompleted_occs = (
        db.query(TaskOccurrence)
        .join(Task)
        .filter(
            Task.user_id == user_id,
            Task.kind == "daily",
            Task.is_active == True,
            TaskOccurrence.date == source_date,
            TaskOccurrence.status != "done",
        )
        .all()
    )

    moved_count = 0
    for occ in uncompleted_occs:
        # Verificar si ya existe una ocurrencia de esta tarea en la fecha destino
        existing_dest = (
            db.query(TaskOccurrence)
            .filter(
                TaskOccurrence.task_id == occ.task_id,
                TaskOccurrence.date == dest_date,
            )
            .first()
        )
        if not existing_dest:
            occ.date = dest_date
            occ.task.date = dest_date
        else:
            occ.task.date = dest_date
            db.delete(occ)

        moved_count += 1

    db.commit()

    return DailyCarryOverResponse(
        source_date=source_date,
        target_date=dest_date,
        moved_count=moved_count,
        message=f"Se han pospuesto {moved_count} tarea(s) pendiente(s) al {dest_date.strftime('%d/%m/%Y')}."
    )


def get_weekly_summary(
    db: Session,
    user_id: int,
    ref_date: Optional[dt.date] = None
) -> WeeklySummaryResponse:
    """
    Genera el resumen semanal de lunes a domingo:
    - Desglose por día
    - Cumplimiento global acumulado
    - Mejor día de la semana
    - Racha actual
    """
    base_date = ref_date or get_user_today(db, user_id)
    # Lunes de la semana
    week_start = base_date - dt.timedelta(days=base_date.weekday())
    # Domingo de la semana
    week_end = week_start + dt.timedelta(days=6)

    ensure_occurrences(db, user_id, week_start, week_end)

    occs = (
        db.query(TaskOccurrence)
        .join(Task)
        .filter(
            Task.user_id == user_id,
            Task.is_active == True,
            TaskOccurrence.date >= week_start,
            TaskOccurrence.date <= week_end,
        )
        .all()
    )

    # Agrupar por fecha
    occs_by_date: Dict[dt.date, List[TaskOccurrence]] = {}
    for o in occs:
        occs_by_date.setdefault(o.date, []).append(o)

    days_summary: List[WeeklyDaySummary] = []
    total_week_tasks = 0
    total_week_completed = 0
    best_day_name = None
    max_completed = -1

    today = get_user_today(db, user_id)

    curr = week_start
    idx = 0
    while curr <= week_end:
        day_occs = occs_by_date.get(curr, [])
        d_total = len(day_occs)
        d_completed = sum(1 for o in day_occs if o.status == "done")
        d_rate = int(round((d_completed / d_total * 100))) if d_total > 0 else 0

        total_week_tasks += d_total
        total_week_completed += d_completed

        day_name = DAY_NAMES_ES[idx]
        if d_completed > max_completed and d_completed > 0:
            max_completed = d_completed
            best_day_name = f"{day_name} ({d_completed} tareas)"

        days_summary.append(
            WeeklyDaySummary(
                date=curr,
                day_name=day_name,
                total_tasks=d_total,
                completed_tasks=d_completed,
                completion_rate=d_rate,
                is_today=(curr == today),
            )
        )
        curr += dt.timedelta(days=1)
        idx += 1

    weekly_rate = int(round((total_week_completed / total_week_tasks * 100))) if total_week_tasks > 0 else 0
    current_streak = get_user_streak(db, user_id, base_date)

    return WeeklySummaryResponse(
        week_start=week_start,
        week_end=week_end,
        total_tasks=total_week_tasks,
        completed_tasks=total_week_completed,
        completion_rate=weekly_rate,
        current_streak=current_streak,
        best_day=best_day_name,
        days=days_summary,
    )


def get_completed_history(
    db: Session,
    user_id: int,
    start_date: Optional[dt.date] = None,
    end_date: Optional[dt.date] = None,
    q: Optional[str] = None,
    project_id: Optional[int] = None,
    limit: int = 20,
    offset: int = 0,
) -> HistoryResponse:
    """
    Obtiene el historial paginado de tareas completadas (personales y/o de proyecto):
    - Filtrable por rango de fechas
    - Búsqueda en texto libre
    - Aislamiento por usuario
    """
    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    items: List[TaskHistoryItem] = []

    # 1. Si no se pide un proyecto específico (o si project_id es None), buscar tareas personales
    if project_id is None:
        occ_query = (
            db.query(TaskOccurrence)
            .join(Task)
            .filter(
                Task.user_id == user_id,
                TaskOccurrence.status == "done",
            )
        )

        if start_date:
            occ_query = occ_query.filter(TaskOccurrence.date >= start_date)
        if end_date:
            occ_query = occ_query.filter(TaskOccurrence.date <= end_date)
        if q and q.strip():
            search_pat = f"%{q.strip()}%"
            occ_query = occ_query.filter(
                or_(Task.title.ilike(search_pat), Task.description.ilike(search_pat))
            )

        personal_occs = (
            occ_query
            .order_by(TaskOccurrence.date.desc(), TaskOccurrence.id.desc())
            .all()
        )

        for o in personal_occs:
            items.append(
                TaskHistoryItem(
                    occurrence_id=o.id,
                    task_id=o.task_id,
                    title=o.task.title,
                    description=o.task.description,
                    kind=o.task.kind,
                    importance=o.task.importance,
                    date=o.date,
                    completed_at=None,
                    project_id=None,
                    project_name=None,
                )
            )

    # 2. Tareas de proyecto donde el usuario participa
    proj_query = (
        db.query(ProjectTask, Project.name.label("project_name"))
        .join(Project, ProjectTask.project_id == Project.id)
        .join(ProjectColumn, ProjectTask.column_id == ProjectColumn.id)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .filter(
            ProjectMember.user_id == user_id,
            or_(ProjectColumn.is_done == True, ProjectTask.completed_at.isnot(None)),
            ProjectTask.is_active == True,
        )
    )

    if project_id:
        proj_query = proj_query.filter(ProjectTask.project_id == project_id)
    if start_date:
        proj_query = proj_query.filter(
            or_(ProjectTask.date >= start_date, func.date(ProjectTask.completed_at) >= start_date)
        )
    if end_date:
        proj_query = proj_query.filter(
            or_(ProjectTask.date <= end_date, func.date(ProjectTask.completed_at) <= end_date)
        )
    if q and q.strip():
        search_pat = f"%{q.strip()}%"
        proj_query = proj_query.filter(
            or_(ProjectTask.title.ilike(search_pat), ProjectTask.description.ilike(search_pat))
        )

    proj_tasks = proj_query.all()
    for pt, p_name in proj_tasks:
        task_date = pt.date or (pt.completed_at.date() if pt.completed_at else dt.date.today())
        items.append(
            TaskHistoryItem(
                occurrence_id=None,
                task_id=pt.id,
                title=pt.title,
                description=pt.description,
                kind="project",
                importance=pt.priority,
                date=task_date,
                completed_at=pt.completed_at,
                project_id=pt.project_id,
                project_name=p_name,
            )
        )

    # Ordenar por fecha descendente
    items.sort(key=lambda x: (x.date, x.completed_at or dt.datetime.min), reverse=True)

    total_count = len(items)
    paged_items = items[offset : offset + limit]

    return HistoryResponse(
        total=total_count,
        limit=limit,
        offset=offset,
        items=paged_items,
    )

