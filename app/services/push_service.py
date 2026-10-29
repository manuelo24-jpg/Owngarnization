import datetime as dt
import json
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.config import settings
from app.models import PushSubscription, User

logger = logging.getLogger(__name__)


def _deliver_webpush(subscription_info: Dict[str, Any], data: str, vapid_private_key: str, vapid_claims: Dict[str, Any]) -> None:
    """Wrapper sobre pywebpush.webpush para facilitar la inyección/simulación en tests."""
    from pywebpush import webpush
    webpush(
        subscription_info=subscription_info,
        data=data,
        vapid_private_key=vapid_private_key,
        vapid_claims=vapid_claims,
    )


def register_subscription(
    db: Session,
    user_id: int,
    endpoint: str,
    p256dh: str,
    auth: str,
    user_agent: Optional[str] = None,
) -> PushSubscription:
    """Crea o actualiza una suscripción Web Push garantizando unicidad por endpoint."""
    existing = db.query(PushSubscription).filter(PushSubscription.endpoint == endpoint).first()
    if existing:
        existing.user_id = user_id
        existing.p256dh = p256dh
        existing.auth = auth
        if user_agent:
            existing.user_agent = user_agent[:500]
        db.commit()
        db.refresh(existing)
        return existing

    sub = PushSubscription(
        user_id=user_id,
        endpoint=endpoint,
        p256dh=p256dh,
        auth=auth,
        user_agent=user_agent[:500] if user_agent else None,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


def delete_subscription(db: Session, user_id: int, endpoint: str) -> bool:
    """Elimina la suscripción del dispositivo sólo si pertenece al usuario actual."""
    sub = (
        db.query(PushSubscription)
        .filter(PushSubscription.endpoint == endpoint, PushSubscription.user_id == user_id)
        .first()
    )
    if not sub:
        return False
    db.delete(sub)
    db.commit()
    return True


def send_push_to_user(db: Session, user: User, payload: Dict[str, Any]) -> int:
    """
    Envía un payload JSON a todos los dispositivos suscritos del usuario.
    Limpia automáticamente suscripciones caducadas (HTTP 404 / 410).
    Retorna el número de envíos exitosos.
    """
    subs = db.query(PushSubscription).filter(PushSubscription.user_id == user.id).all()
    if not subs:
        return 0

    sent_count = 0
    payload_str = json.dumps(payload, ensure_ascii=False)
    now_utc = dt.datetime.now(dt.timezone.utc)

    for sub in list(subs):
        sub_info = {
            "endpoint": sub.endpoint,
            "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
        }
        try:
            _deliver_webpush(
                subscription_info=sub_info,
                data=payload_str,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": settings.VAPID_SUBJECT},
            )
            sub.last_success_at = now_utc
            sent_count += 1
        except Exception as exc:
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            if status_code in (404, 410):
                db.delete(sub)
            else:
                logger.warning("Fallo al enviar Web Push a sub %s: %s", sub.id, exc)

    return sent_count

