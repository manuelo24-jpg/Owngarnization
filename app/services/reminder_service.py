import datetime as dt
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Dict, Optional
from sqlalchemy.orm import Session, joinedload

from app.models import User, Task, TaskOccurrence, PushSubscription
from app.services import occurrence_service, push_service

IMPORTANCE_LABELS = {
    "low": "Prioridad baja",
    "medium": "Prioridad media",
    "high": "Prioridad alta",
    "urgent": "Prioridad urgente",
}


def dispatch_due_reminders(db: Session, now_utc: Optional[dt.datetime] = None) -> Dict[str, int]:
    """
    Evalúa los recordatorios pendientes para todos los usuarios con avisos activos
    y suscripciones registradas.
    - Materializa las ocurrencias del día local del usuario (lazy generation).
    - Ventana de envío: [inicio - antelación, inicio + 15 min].
    - Marca reminder_sent_at en la misma transacción para evitar duplicados.
    """
    ref_utc = now_utc or dt.datetime.now(dt.timezone.utc)
    if ref_utc.tzinfo is None:
        ref_utc = ref_utc.replace(tzinfo=dt.timezone.utc)

    users = (
        db.query(User)
        .join(PushSubscription, PushSubscription.user_id == User.id)
        .filter(User.reminders_enabled == True)
        .distinct()
        .all()
    )

    occurrences_notified = 0
    messages_sent = 0

    for user in users:
        try:
            tz = ZoneInfo(user.timezone or "Europe/Madrid")
        except (ZoneInfoNotFoundError, KeyError, ValueError):
            tz = ZoneInfo("Europe/Madrid")

        now_local = ref_utc.astimezone(tz)
        today_local = now_local.date()

        occurrence_service.rollover_uncompleted_daily_tasks(db, user.id, ref_utc)
        occurrence_service.ensure_occurrences(db, user.id, today_local, today_local)

        candidates = (
            db.query(TaskOccurrence)
            .join(Task, TaskOccurrence.task_id == Task.id)
            .options(joinedload(TaskOccurrence.task))
            .filter(
                Task.user_id == user.id,
                Task.is_active == True,
                TaskOccurrence.date == today_local,
                TaskOccurrence.status != "done",
                TaskOccurrence.reminder_sent_at.is_(None),
            )
            .all()
        )

        offset_min = user.reminder_offset_min if user.reminder_offset_min is not None else 10

        for occ in candidates:
            effective_time = occ.start_time or occ.task.start_time
            if not effective_time:
                continue

            start_dt_local = dt.datetime.combine(today_local, effective_time, tzinfo=tz)
            window_open = start_dt_local - dt.timedelta(minutes=offset_min)
            window_close = start_dt_local + dt.timedelta(minutes=15)

            if window_open <= now_local <= window_close:
                time_str = effective_time.strftime("%H:%M")
                imp_label = IMPORTANCE_LABELS.get(occ.task.importance, "Prioridad media")
                if offset_min > 0:
                    body_text = f"Empieza a las {time_str} (aviso {offset_min} min antes) · {imp_label}"
                else:
                    body_text = f"Programada a las {time_str} · {imp_label}"

                payload = {
                    "title": f"⏱️ {time_str} · {occ.task.title}",
                    "body": body_text,
                    "tag": f"occ-{occ.id}",
                    "url": f"/m?date={today_local.isoformat()}&occ={occ.id}",
                    "occ_id": occ.id,
                }

                delivered = push_service.send_push_to_user(db, user, payload)
                if delivered > 0:
                    occ.reminder_sent_at = ref_utc
                    occurrences_notified += 1
                    messages_sent += delivered

        db.commit()

    return {
        "users_checked": len(users),
        "occurrences_notified": occurrences_notified,
        "messages_sent": messages_sent,
    }

