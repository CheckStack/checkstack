from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401 — register mappers
from app.database import Base, engine
from app.db_migrate import run_migrations
from app.routers import (
    alerts,
    health,
    incidents,
    monitors,
    public_status,
    tags,
    uptime,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    run_migrations(engine)
    yield


app = FastAPI(title="CheckStack API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(public_status.router)
app.include_router(monitors.router)
app.include_router(incidents.router)
app.include_router(uptime.router)
app.include_router(alerts.router)
app.include_router(tags.router)
