from fastapi import APIRouter

from app.db import get_connection
from app.event_store import insert_event
from app.models.alertmanager import Alert, AlertmanagerWebhook
from app.models.event import EventCreate

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def alert_to_event(alert: Alert, webhook: AlertmanagerWebhook) -> EventCreate:
    return EventCreate(
        actor="system",
        kind="alert",
        epistemic_status="observed",
        payload={
            "status": alert.status,
            "labels": alert.labels,
            "annotations": alert.annotations,
            "startsAt": alert.startsAt,
            "endsAt": alert.endsAt,
            "fingerprint": alert.fingerprint,
        },
        provenance={
            "source": "alertmanager",
            "receiver": webhook.receiver,
            "groupKey": webhook.groupKey,
            "generatorURL": alert.generatorURL,
            "externalURL": webhook.externalURL,
        },
    )


@router.post("/alertmanager")
def receive_alertmanager(webhook: AlertmanagerWebhook):
    with get_connection() as conn:
        saved = [
            insert_event(conn, f"alert-{alert.fingerprint}", alert_to_event(alert, webhook))
            for alert in webhook.alerts
        ]
    return {"received": len(saved), "event_ids": [e["id"] for e in saved]}