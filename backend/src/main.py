"""SubbiesStats API — FastAPI application entrypoint."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import get_settings
from src.competitions.router import router as competitions_router
from src.clubs.router import router as clubs_router
from src.games.router import router as games_router
from src.players.router import router as players_router
from src.standings.router import router as standings_router

settings = get_settings()
logger = logging.getLogger("uvicorn")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    # Startup — launch ingestion scheduler in background
    from src.ingestion.service import start_ingestion_scheduler, stop_ingestion_scheduler
    logger.info("Starting ingestion scheduler...")
    start_ingestion_scheduler()

    yield

    # Shutdown
    stop_ingestion_scheduler()
    from src.core.database import engine
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# CORS — allow frontend dev server in development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost", "http://localhost:8081"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(competitions_router, prefix="/api/competitions", tags=["Competitions"])
app.include_router(clubs_router, prefix="/api/clubs", tags=["Clubs"])
app.include_router(games_router, prefix="/api/games", tags=["Games"])
app.include_router(players_router, prefix="/api/players", tags=["Players"])
app.include_router(standings_router, prefix="/api/standings", tags=["Standings"])


@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint for container orchestration."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }
