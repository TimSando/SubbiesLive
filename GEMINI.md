This project is all about creating an easily accessible website for fans of the local rugby scene in Sydney. There is a focus on 3 main areas currently:
- Clubs: The goal of this is to provide a view of all the clubs across the competitions in Sydney to make it easy for both new players looking for a club or existing players/spectators to find information about their club of choice.
- Competitions: The goal of this is to provide a view of the club ladders for each competition and make it easy to navigate to the draw for a given week.
- Stats: This is the primary goal of the website, to provide statistics for players and teams across all competitions. The goal would be to extend this over time for interesting stats

You're an experienced webapp developer and you have a deep understanding of React, TypeScript, and Python. You have backend experience with FastAPI and PostgreSQL. You are comfortable working within a docker environment.

All recommendations should be centered around how to host this as simply as possible as a small-scale website which will likely be from a home server.

---

## Project Architecture & Reference Summary

This section details the layout, configuration, and components of the repository to fast-track onboarding in new agent sessions.

### 1. Project Directory Structure
* **`backend/`**: FastAPI web application running on Python.
  - `src/main.py`: Main entry point containing application lifespan handlers and router declarations.
  - `src/core/`: Application settings (`config.py`), database setup (`database.py`), dependencies (`dependencies.py`), and models.
    - Supports both async sessions (`AsyncSession` using `asyncpg` via `DATABASE_URL`) and sync engines (`DATABASE_URL_SYNC` for background tasks).
  - `src/ingestion/`: Ingestion orchestration (FuseSport APIs, parser/engine, scheduler).
  - Feature Routers: Isolated under respective directories (e.g. `src/competitions/`, `src/clubs/`, `src/games/`, `src/players/`, `src/standings/`, `src/stats/`, `src/refzone/`).
* **`frontend/`**: Single-Page React application built using Vite.
  - `src/main.jsx` & `src/App.jsx`: Base router & styling setup.
  - `src/pages/`: Page components (e.g., `Home.jsx`, `Clubs.jsx`, `Stats.jsx`).
  - `src/api/client.js`: HTTP request wrapper for communicate with the backend via `/api/` prefix.
  - `src/index.css`: The central CSS design system using variables (HSL palette, spacing, glass card UI, animations).

### 2. Configuration & Environments
* Configuration is managed via Pydantic `BaseSettings` (`src/core/config.py`) loading values from the root `.env` file.
* **Environment Variables**:
  - `DATABASE_URL`: Asynchronous DB URL (e.g., `postgresql+asyncpg://...`).
  - `DATABASE_URL_SYNC`: Synchronous DB URL (e.g., `postgresql://...`).
  - `INGESTION_PASSWORD`: Token/Password (default: `dbRefresh_`) used to authorize manual database ingestion.
* **Docker Multi-Stage Setup**:
  - **Development Mode**: `docker compose up` automatically includes the dev override. The frontend uses a Vite dev server on port `5173` with a live volume mount (`./frontend/src:/app/src`) to support Hot Module Replacement (HMR).
  - **Production Mode**: `docker compose -f docker-compose.yml up` builds and runs the production stage. The frontend builds static HTML/JS assets into a `dist/` directory and serves them via an Nginx container listening on port `8081`, proxying `/api/` requests to the `backend` container.

### 3. Ingestion & Sync Pipeline
* **Background Scheduler**: Set up inside `src/ingestion/scheduler.py` via `APScheduler`. Launches a background thread on startup for initial mapping sync and registers daily and Saturday sync cycles.
* **Concurrency Locking**: The main sync function `run_ingestion` in `src/ingestion/service.py` is protected by a thread-safe `_ingestion_lock` and tracking variable `_is_ingestion_running`. Any concurrent manual or scheduled triggers will be rejected cleanly if a sync is already active.
* **Manual Refresh**: Initiated via a floating action button on the bottom left of the `Home` page, which opens a custom glass card password modal. The trigger route is `/api/ingestion/trigger` and the status check is `/api/ingestion/status`.