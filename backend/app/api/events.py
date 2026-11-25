from fastapi import APIRouter

from app.db import get_connection
from app.event_store import insert_event
from app.models.event import EventCreate, EventOut

router = APIRouter(prefix="/incidents/{incident_id}/events", tags=["events"])


@router.post("", response_model=EventOut, status_code=201)
def append_event(incident_id: str, event: EventCreate):
    with get_connection() as conn:
        return insert_event(conn, incident_id, event)


@router.get("", response_model=list[EventOut])
def list_events(incident_id: str):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, incident_id, ts, actor, kind,
                   epistemic_status, payload, provenance
            FROM events
            WHERE incident_id = %s
            ORDER BY ts, id
            """,
            (incident_id,),
        ).fetchall()
    return rows 