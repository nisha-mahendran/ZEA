import psycopg
import pytest

from app.db import get_connection


def event_body(**overrides):
    body = {
        "actor": "zea",
        "kind": "observation",
        "epistemic_status": "observed",
    }
    body.update(overrides)
    return body


# ---------- adding events ----------

def test_append_returns_saved_event(client):
    response = client.post(
        "/incidents/inc-1/events",
        json=event_body(payload={"note": "checkout latency is high"}),
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 1
    assert data["incident_id"] == "inc-1"
    assert data["payload"] == {"note": "checkout latency is high"}
    assert data["ts"]


def test_payload_and_provenance_default_to_empty_objects(client):
    data = client.post("/incidents/inc-1/events", json=event_body()).json()

    assert data["payload"] == {}
    assert data["provenance"] == {}


def test_nested_json_survives_a_round_trip(client):
    payload = {"service": "checkout", "tags": ["slow", "db"], "stats": {"p99_ms": 2400}}
    client.post("/incidents/inc-1/events", json=event_body(payload=payload))

    saved = client.get("/incidents/inc-1/events").json()[0]

    assert saved["payload"] == payload


def test_server_assigns_id_ts_and_incident_id(client):
    response = client.post(
        "/incidents/inc-1/events",
        json=event_body(id=999, ts="2000-01-01T00:00:00Z", incident_id="evil"),
    )

    data = response.json()
    assert data["id"] == 1
    assert not data["ts"].startswith("2000")
    assert data["incident_id"] == "inc-1"


def test_human_actor_is_accepted(client):
    response = client.post(
        "/incidents/inc-1/events", json=event_body(actor="human:nisha")
    )

    assert response.status_code == 201


# ---------- listing events ----------

def test_list_returns_events_in_order(client):
    for kind in ["alert", "observation", "hypothesis"]:
        client.post("/incidents/inc-1/events", json=event_body(kind=kind))

    response = client.get("/incidents/inc-1/events")

    assert response.status_code == 200
    events = response.json()
    assert [e["kind"] for e in events] == ["alert", "observation", "hypothesis"]
    assert [e["id"] for e in events] == [1, 2, 3]


def test_list_only_returns_the_requested_incident(client):
    client.post("/incidents/inc-1/events", json=event_body(kind="alert"))
    client.post("/incidents/inc-2/events", json=event_body(kind="report"))

    events = client.get("/incidents/inc-1/events").json()

    assert len(events) == 1
    assert events[0]["kind"] == "alert"


def test_unknown_incident_returns_empty_list(client):
    response = client.get("/incidents/does-not-exist/events")

    assert response.status_code == 200
    assert response.json() == []


# ---------- the API rejects bad input ----------

@pytest.mark.parametrize(
    "field,value",
    [
        ("kind", "banana"),
        ("actor", "bob"),
        ("actor", "human:"),
        ("epistemic_status", "definitely-true"),
    ],
)
def test_api_rejects_invalid_values(client, field, value):
    response = client.post("/incidents/inc-1/events", json=event_body(**{field: value}))

    assert response.status_code == 422
    assert client.get("/incidents/inc-1/events").json() == []


def test_api_rejects_a_missing_required_field(client):
    body = event_body()
    del body["kind"]

    response = client.post("/incidents/inc-1/events", json=body)

    assert response.status_code == 422


# ---------- the database rejects bad input even without the API ----------

@pytest.mark.parametrize(
    "column,value",
    [("actor", "bob"), ("kind", "banana"), ("epistemic_status", "maybe")],
)
def test_database_rejects_bad_values(column, value):
    row = {
        "incident_id": "inc-1",
        "actor": "zea",
        "kind": "observation",
        "epistemic_status": "observed",
    }
    row[column] = value

    with pytest.raises(psycopg.errors.CheckViolation):
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO events (incident_id, actor, kind, epistemic_status)
                VALUES (%(incident_id)s, %(actor)s, %(kind)s, %(epistemic_status)s)
                """,
                row,
            )


# ---------- append-only: the API has no way to change events ----------

@pytest.mark.parametrize("method", ["put", "patch", "delete"])
def test_api_cannot_change_the_events_collection(client, method):
    response = getattr(client, method)("/incidents/inc-1/events")

    assert response.status_code == 405


@pytest.mark.parametrize("method", ["put", "patch", "delete"])
def test_api_cannot_change_a_single_event(client, method):
    client.post("/incidents/inc-1/events", json=event_body())

    response = getattr(client, method)("/incidents/inc-1/events/1")

    assert response.status_code in (404, 405)
    assert len(client.get("/incidents/inc-1/events").json()) == 1