from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

Kind = Literal[
    "alert", "observation", "hypothesis", "evidence", "experiment",
    "tool_call", "message", "state_transition", "approval",
    "verification", "report",
]

EpistemicStatus = Literal[
    "observed", "verified", "human_claim", "inferred", "rejected",
]


class EventCreate(BaseModel):
    actor: str = Field(pattern=r"^(system|zea|human:.+)$")
    kind: Kind
    epistemic_status: EpistemicStatus
    payload: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)


class EventOut(EventCreate):
    id: int
    incident_id: str
    ts: datetime