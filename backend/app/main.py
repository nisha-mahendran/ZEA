from fastapi import FastAPI

from app.api.events import router as events_router
from app.api.webhooks import router as webhooks_router

app = FastAPI(title="ZEA")

app.include_router(events_router)
app.include_router(webhooks_router)