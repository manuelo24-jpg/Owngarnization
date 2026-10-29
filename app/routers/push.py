import hmac
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.deps import get_db, get_current_user
from app.models import User
from app.schemas import (
    PushSubscriptionCreate,
    PushSubscriptionDelete,
    UserPreferencesResponse,
    UserPreferencesUpdate,
)
from app.services import push_service, reminder_service

router = APIRouter(tags=["Notificaciones Push"])


@router.get("/api/push/public-key")
def get_vapid_public_key(current_user: User = Depends(get_current_user)):
    """Devuelve la clave pública VAPID para suscribirse desde el navegador."""
    return {"public_key": settings.VAPID_PUBLIC_KEY}


@router.post("/api/push/subscriptions", status_code=status.HTTP_201_CREATED)
def subscribe_push(
    sub_in: PushSubscriptionCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Registra o actualiza la suscripción Web Push del dispositivo actual."""
    ua = request.headers.get("user-agent")
    sub = push_service.register_subscription(
        db=db,
        user_id=current_user.id,
        endpoint=sub_in.endpoint,
        p256dh=sub_in.keys.p256dh,
        auth=sub_in.keys.auth,
        user_agent=ua,
    )
    return {"id": sub.id, "message": "Suscripción registrada correctamente"}


@router.delete("/api/push/subscriptions")
def unsubscribe_push(
    sub_in: PushSubscriptionDelete,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Elimina la suscripción Web Push del dispositivo actual."""
    deleted = push_service.delete_subscription(
        db=db,
        user_id=current_user.id,
        endpoint=sub_in.endpoint,
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Suscripción no encontrada",
        )
    return {"message": "Suscripción eliminada"}


@router.get("/api/me/preferences", response_model=UserPreferencesResponse)
def get_preferences(current_user: User = Depends(get_current_user)):
    """Obtiene las preferencias de zona horaria y avisos del usuario actual."""
    return current_user


@router.patch("/api/me/preferences", response_model=UserPreferencesResponse)
def update_preferences(
    prefs_in: UserPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Actualiza la zona horaria, activación de recordatorios o antelación."""
    update_data = prefs_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/api/push/test")
def send_test_notification(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Envía una notificación de prueba inmediata a los dispositivos del usuario."""
    payload = {
        "title": "🔔 Owngarnization — Aviso de prueba",
        "body": "¡Tus notificaciones están configuradas y funcionando!",
        "tag": "owng-test",
        "url": "/m",
    }
    sent = push_service.send_push_to_user(db, current_user, payload)
    db.commit()
    if sent == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay dispositivos activos o no se pudo entregar el aviso",
        )
    return {"sent": sent, "message": "Notificación de prueba enviada"}


@router.post("/internal/reminders/dispatch")
def dispatch_reminders_cron(
    x_cron_secret: str | None = Header(default=None, alias="X-Cron-Secret"),
    db: Session = Depends(get_db),
):
    """
    Endpoint interno invocado cada minuto por el cron externo.
    Protegido con comparación en tiempo constante (hmac.compare_digest).
    Solo devuelve contadores agregados sin filtrar datos de usuarios.
    """
    expected = settings.CRON_SECRET
    if not expected or not x_cron_secret or not hmac.compare_digest(x_cron_secret, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autorizado",
        )

    stats = reminder_service.dispatch_due_reminders(db)
    return {"status": "ok", **stats}

