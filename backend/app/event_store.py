from psycopg import Connection
from psycopg.types.json import Jsonb

from app.models.event import EventCreate


def insert_event(conn: Connection, incident_id: str, event: EventCreate) -> dict:
    return conn.execute(
        """
        INSERT INTO events
            (incident_id, actor, kind, epistemic_status, payload, provenance)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id, incident_id, ts, actor, kind,
                  epistemic_status, payload, provenance
        """,
        (
            incident_id,
            event.actor,
            event.kind,
            event.epistemic_status,
            Jsonb(event.payload),
            Jsonb(event.provenance),
        ),
    ).fetchone()