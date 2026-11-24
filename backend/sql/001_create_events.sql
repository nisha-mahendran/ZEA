-- The events table: an append-only log of everything ZEA sees and does.
-- Rule: rows are only ever added, never edited or deleted.
-- For now the API enforces this by having no update or delete routes.

CREATE TABLE events (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    incident_id       TEXT        NOT NULL,
    ts                TIMESTAMPTZ NOT NULL DEFAULT now(),
    actor             TEXT        NOT NULL,
    kind              TEXT        NOT NULL,
    payload           JSONB       NOT NULL DEFAULT '{}',
    provenance        JSONB       NOT NULL DEFAULT '{}',
    epistemic_status  TEXT        NOT NULL,

    CONSTRAINT events_actor_check
        CHECK (actor IN ('system', 'zea') OR actor LIKE 'human:%'),

    CONSTRAINT events_kind_check
        CHECK (kind IN (
            'alert', 'observation', 'hypothesis', 'evidence', 'experiment',
            'tool_call', 'message', 'state_transition', 'approval',
            'verification', 'report'
        )),

    CONSTRAINT events_epistemic_status_check
        CHECK (epistemic_status IN (
            'observed', 'verified', 'human_claim', 'inferred', 'rejected'
        ))
);

-- The timeline asks: all events for one incident, in time order.
CREATE INDEX events_incident_ts_idx ON events (incident_id, ts, id);