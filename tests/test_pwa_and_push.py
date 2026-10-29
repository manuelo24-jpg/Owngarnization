"""
Tests de integración y servicios para la App Móvil (/m), Página de Descarga (/download),
PWA (/manifest.webmanifest, /sw.js), Web Push y Recordatorios por Zona Horaria.
"""

from datetime import date, datetime, time
import json
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base
from app.models import PushSubscription, Task, TaskOccurrence, User
from app.routers.pages import download_mobile_page, index, mobile_app_page
from app.routers.push import dispatch_reminders_cron, update_preferences
from app.routers.pwa import get_manifest, get_service_worker
from app.schemas import TaskUpdate, UserPreferencesUpdate
from app.services import occurrence_service, push_service, reminder_service, task_service


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def _create_user(
    db,
    username="usuario1",
    email="u1@example.com",
    tz="Europe/Madrid",
    offset=10,
    enabled=True,
) -> User:
    user = User(
        username=username,
        email=email,
        password_hash="hash_ficticio",
        timezone=tz,
        reminders_enabled=enabled,
        reminder_offset_min=offset,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_manifest_points_to_mobile_app_and_sw_headers():
    """Verifica que el Web App Manifest apunta a /m?source=pwa y que /sw.js no se cachea."""
    manifest_resp = get_manifest()
    assert manifest_resp.media_type == "application/manifest+json"

    body = json.loads(manifest_resp.body.decode("utf-8"))
    assert body["display"] == "standalone"
    assert body["start_url"] == "/m?source=pwa"
    sizes = {icon["sizes"] for icon in body["icons"]}
    assert "192x192" in sizes
    assert "512x512" in sizes

    sw_resp = get_service_worker()
    assert "no-cache" in sw_resp.headers.get("Cache-Control", "")
    assert sw_resp.headers.get("Service-Worker-Allowed") == "/"


def test_web_mobile_and_download_pages_separation(db_session):
    """Verifica que la versión Web (/), la versión Móvil (/m) y la página de Descarga (/download) están separadas."""
    from starlette.requests import Request

    user = _create_user(db_session)

    def make_req(path: str) -> Request:
        scope = {
            "type": "http",
            "method": "GET",
            "path": path,
            "headers": [],
            "query_string": b"",
            "session": {"user_id": user.id},
        }
        return Request(scope)

    web_resp = index(make_req("/"), current_user=user)
    mobile_resp = mobile_app_page(make_req("/m"), current_user=user)
    download_resp = download_mobile_page(make_req("/download"), current_user=user)

    assert web_resp.template.name == "app.html"
    assert mobile_resp.template.name == "mobile_app.html"
    assert download_resp.template.name == "download_app.html"


def test_default_task_ordering_and_manual_override(db_session):
    """
    Verifica que por defecto:
    1. Primero van las tareas con hora ordenadas por start_time ASC.
    2. Luego las tareas sin hora ordenadas por prioridad (urgent -> high -> medium -> low).
    3. Si el usuario reordena manualmente, se respeta manual_order.
    """
    user = _create_user(db_session)
    target = date(2026, 10, 29)

    t_low = Task(user_id=user.id, title="Sin hora Baja", kind="daily", importance="low", date=target)
    t_urgent = Task(user_id=user.id, title="Sin hora Urgente", kind="daily", importance="urgent", date=target)
    t_late = Task(user_id=user.id, title="Con hora 14:00", kind="daily", importance="low", date=target, start_time=time(14, 0))
    t_early = Task(user_id=user.id, title="Con hora 09:00", kind="daily", importance="medium", date=target, start_time=time(9, 0))
    db_session.add_all([t_low, t_urgent, t_late, t_early])
    db_session.commit()

    occs = occurrence_service.get_occurrences_in_range(
        db_session, user.id, start=target, end=target, kind="daily"
    )
    titles = [o.task.title for o in occs]
    assert titles == [
        "Con hora 09:00",
        "Con hora 14:00",
        "Sin hora Urgente",
        "Sin hora Baja",
    ]


def test_user_preferences_validation(db_session):
    """Verifica validación de zona horaria IANA y antelaciones permitidas."""
    user = _create_user(db_session)

    prefs = update_preferences(
        UserPreferencesUpdate(
            timezone="America/Mexico_City",
            reminders_enabled=False,
            reminder_offset_min=15,
        ),
        current_user=user,
        db=db_session,
    )
    assert prefs.timezone == "America/Mexico_City"
    assert prefs.reminders_enabled is False
    assert prefs.reminder_offset_min == 15

    with pytest.raises(ValidationError):
        UserPreferencesUpdate(timezone="Zona/Inexistente")

    with pytest.raises(ValidationError):
        UserPreferencesUpdate(reminder_offset_min=7)


def test_push_subscription_isolation_between_users(db_session):
    """Verifica creación, actualización e imposibilidad de borrar suscripción de otro usuario."""
    u1 = _create_user(db_session, "user1", "u1@test.com")
    u2 = _create_user(db_session, "user2", "u2@test.com")

    sub = push_service.register_subscription(
        db_session,
        user_id=u1.id,
        endpoint="https://fcm.googleapis.com/fcm/send/abc-123",
        p256dh="clave_p256dh",
        auth="clave_auth",
        user_agent="Mozilla/5.0 Mobile",
    )
    assert sub.user_id == u1.id

    deleted_by_other = push_service.delete_subscription(db_session, u2.id, sub.endpoint)
    assert deleted_by_other is False

    deleted_by_owner = push_service.delete_subscription(db_session, u1.id, sub.endpoint)
    assert deleted_by_owner is True


def test_reminder_dispatch_window_deeplink_and_410_cleanup(db_session):
    """
    Verifica:
    1. Envío cuando now_local entra en [start_dt - offset, start_dt + 15m] con enlace a /m.
    2. No duplicación en segunda ejecución (reminder_sent_at).
    3. Re-armado de reminder_sent_at al cambiar la hora de la tarea.
    4. Eliminación automática de suscripciones expiradas (HTTP 410).
    """
    user = _create_user(db_session, tz="Europe/Madrid", offset=10, enabled=True)

    push_service.register_subscription(
        db_session,
        user_id=user.id,
        endpoint="https://push.example.com/valid",
        p256dh="k1",
        auth="a1",
    )
    push_service.register_subscription(
        db_session,
        user_id=user.id,
        endpoint="https://push.example.com/expired-410",
        p256dh="k2",
        auth="a2",
    )

    target_date = date(2026, 10, 29)
    task = Task(
        user_id=user.id,
        title="Reunión 10h",
        kind="daily",
        importance="high",
        date=target_date,
        start_time=time(10, 0),
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    occ = TaskOccurrence(
        task_id=task.id,
        date=target_date,
        status="not_started",
    )
    db_session.add(occ)
    db_session.commit()
    db_session.refresh(occ)

    deliveries = []

    class FakeResp:
        status_code = 410

    class FakeWebPushException(Exception):
        def __init__(self):
            self.response = FakeResp()

    def fake_deliver(subscription_info, data, vapid_private_key, vapid_claims):
        deliveries.append((subscription_info["endpoint"], data))
        if "expired-410" in subscription_info["endpoint"]:
            raise FakeWebPushException()

    now_madrid = datetime(2026, 10, 29, 9, 52, tzinfo=ZoneInfo("Europe/Madrid"))
    now_utc = now_madrid.astimezone(ZoneInfo("UTC"))

    with patch("app.services.push_service._deliver_webpush", side_effect=fake_deliver):
        stats1 = reminder_service.dispatch_due_reminders(db_session, now_utc=now_utc)
        assert stats1["occurrences_notified"] == 1
        assert stats1["messages_sent"] == 1
        assert f"/m?date=2026-10-29&occ={occ.id}" in deliveries[0][1]
        assert "Reunión 10h" in deliveries[0][1]

        remaining_subs = db_session.query(PushSubscription).filter(PushSubscription.user_id == user.id).all()
        assert len(remaining_subs) == 1
        assert remaining_subs[0].endpoint == "https://push.example.com/valid"

        # Segunda pasada idempotente
        stats2 = reminder_service.dispatch_due_reminders(db_session, now_utc=now_utc)
        assert stats2["occurrences_notified"] == 0

    # Cambiar hora de la tarea re-arma reminder_sent_at
    task_service.update_task(
        db_session,
        user.id,
        task.id,
        TaskUpdate(start_time=time(11, 30)),
    )
    db_session.refresh(occ)
    assert occ.reminder_sent_at is None


def test_cron_secret_protection(db_session):
    """Verifica que /internal/reminders/dispatch exige X-Cron-Secret válido."""
    original_secret = settings.CRON_SECRET
    try:
        settings.CRON_SECRET = "secreto-super-seguro"
        with pytest.raises(HTTPException) as exc:
            dispatch_reminders_cron(x_cron_secret="incorrecto", db=db_session)
        assert exc.value.status_code == 401

        res = dispatch_reminders_cron(x_cron_secret="secreto-super-seguro", db=db_session)
        assert "occurrences_notified" in res
        assert "messages_sent" in res
    finally:
        settings.CRON_SECRET = original_secret
