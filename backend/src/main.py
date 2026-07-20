"""Subbies Live API — FastAPI application entrypoint."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import src.core.models  # noqa: F401
from src.core.config import get_settings
from src.competitions.router import router as competitions_router
from src.clubs.router import router as clubs_router
from src.games.router import router as games_router
from src.players.router import router as players_router
from src.standings.router import router as standings_router
from src.stats.router import router as stats_router
from src.refzone.router import router as refzone_router
from src.notifications.router import router as notifications_router
from src.teams.router import router as teams_router
from src.ratings.router import router as ratings_router

settings = get_settings()
logger = logging.getLogger("uvicorn")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    # Startup — launch ingestion scheduler in background
    from src.ingestion.scheduler import (
        start_ingestion_scheduler,
        stop_ingestion_scheduler,
    )

    logger.info("Starting ingestion scheduler...")
    start_ingestion_scheduler()

    yield

    # Shutdown
    stop_ingestion_scheduler()
    from src.core.database import engine

    await engine.dispose()


_is_dev = settings.environment == "development"

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/api/docs" if _is_dev else None,
    openapi_url="/api/openapi.json" if _is_dev else None,
    redoc_url="/api/redoc" if _is_dev else None,
    lifespan=lifespan,
)

# CORS — allow frontend dev server in development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost",
        "http://localhost:8081",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(
    competitions_router, prefix="/api/competitions", tags=["Competitions"]
)
app.include_router(clubs_router, prefix="/api/clubs", tags=["Clubs"])
app.include_router(games_router, prefix="/api/games", tags=["Games"])
app.include_router(players_router, prefix="/api/players", tags=["Players"])
app.include_router(standings_router, prefix="/api/standings", tags=["Standings"])
app.include_router(stats_router, prefix="/api/stats", tags=["Stats"])
app.include_router(refzone_router, prefix="/api/refzone", tags=["RefZone"])
app.include_router(
    notifications_router, prefix="/api/notifications", tags=["Notifications"]
)
app.include_router(teams_router, prefix="/api/teams", tags=["Teams"])
app.include_router(ratings_router, prefix="/api/ratings", tags=["Ratings"])


@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint for container orchestration."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }
