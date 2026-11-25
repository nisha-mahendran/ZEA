from typing import Literal

from pydantic import BaseModel, Field


class Alert(BaseModel):
    status: Literal["firing", "resolved"]
    labels: dict[str, str] = Field(default_factory=dict)
    annotations: dict[str, str] = Field(default_factory=dict)
    startsAt: str
    endsAt: str | None = None
    generatorURL: str = ""
    fingerprint: str


class AlertmanagerWebhook(BaseModel):
    status: Literal["firing", "resolved"]
    receiver: str = ""
    groupKey: str = ""
    externalURL: str = ""
    alerts: list[Alert]