# SubbiesStats

A community-focused website for the Sydney club rugby scene, providing club information, competition standings, player statistics, and referee management tools across all major local competitions.

---

## Features

- **Clubs** — Browse all clubs across Sydney competitions. View club details, follow clubs, and find contact information for new or existing players.
- **Competitions** — View ladder standings and navigate weekly draws for each competition. Live match scores are surfaced on the competition detail page.
- **Stats** — Player and team statistics across all competitions, with an expanding set of filters and metrics.
- **RefZone** — A dedicated portal for referees to view upcoming appointment schedules and match preparation details.
- **Notifications** — Push notification support for followed clubs and upcoming fixtures.

---

## Tech Stack

| Layer      | Technology                              |
|------------|-----------------------------------------|
| Frontend   | React (Vite), Vanilla CSS               |
| Backend    | FastAPI (Python 3.10)                   |
| Database   | PostgreSQL 16                           |
| Container  | Docker, Docker Compose                  |
| Web Server | Nginx (production frontend)             |
| CI         | GitHub Actions                          |

---

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- A `.env` file at the project root (see `.env.example`)

### Environment Configuration

Copy the example file and fill in the required values:

```bash
cp .env.example .env
```

Key variables:

| Variable               | Description                                              |
|------------------------|----------------------------------------------------------|
| `DB_USER`              | PostgreSQL username                                      |
| `DB_PASSWORD`          | PostgreSQL password                                      |
| `DB_NAME`              | PostgreSQL database name                                 |
| `INGESTION_PASSWORD`   | Password required to trigger a manual data refresh       |
| `FUSESPORT_DEVICE_ID`  | Device ID for the FuseSport data source                  |
| `VAPID_PUBLIC_KEY`     | 87-character VAPID key for web push notifications        |
| `VAPID_PRIVATE_KEY`    | 43-character VAPID private key                           |
| `VAPID_MAILTO`         | Contact email for the VAPID configuration                |

---

## Running the Application

### Development

Starts the backend and a Vite dev server with Hot Module Replacement (HMR):

```bash
docker compose up
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000/api
- API docs (dev only): http://localhost:8000/api/docs

### Production

Builds the frontend as static assets served via Nginx:

```bash
docker compose -f docker-compose.yml up
```

- Application: http://localhost:8081

---

## Project Structure

```
.
├── backend/
│   ├── src/
│   │   ├── main.py              # FastAPI entrypoint and router registration
│   │   ├── core/                # Config, database, and shared dependencies
│   │   ├── ingestion/           # FuseSport sync pipeline and scheduler
│   │   ├── clubs/               # Clubs API router
│   │   ├── competitions/        # Competitions API router
│   │   ├── games/               # Games API router
│   │   ├── players/             # Players API router
│   │   ├── standings/           # Standings API router
│   │   ├── stats/               # Stats API router
│   │   ├── refzone/             # RefZone API router
│   │   └── notifications/       # Push notification API router
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── pages/               # Page-level React components
│   │   ├── api/client.js        # API request wrapper
│   │   └── index.css            # Global design system (CSS variables, tokens)
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml           # Production compose configuration
├── docker-compose.override.yml  # Development overrides (applied automatically)
└── .env.example                 # Environment variable template
```

---

## Data Ingestion

Competition data is sourced from the FuseSport API and synced on a scheduled basis. The scheduler runs automatically on startup and is configured to refresh daily.

A manual refresh can be triggered from the home page via the floating action button. This requires the `INGESTION_PASSWORD` set in your `.env`.

---

## Running Tests

**Backend:**

```bash
cd backend
uv run pytest
```

**Frontend:**

```bash
cd frontend
npm test
```

CI runs both test suites and Black formatting checks on all pushes to `main` and `develop`.

---

## Deployment Notes

The application is designed for self-hosting on a home server or small VPS. The production Docker Compose setup is self-contained — no external cloud services are required beyond the FuseSport data source.

For HTTPS, place a reverse proxy (e.g., Nginx or Caddy) in front of port `8081`.

## TODO
- Fix competition home page to match the layout of the clubs page. Remove the # clubs, # of rounds details for each competition, update the ordering of the grades in each division

- Enable API access to DB for queries/extracting data for analytics
- Fix the remember me timing for the rugbyXplorer login
- Update "shute shield" to "premiership"
- Update the menu header to be more easily navigatable and clear
- Update the page icon
- Improve the notifications to be easier to read on mobile
- Handle duplicates of rugby ref appointments
- For upcoming fixtures on the home page, it should show the next match by date (rather than the last in the list)
- Update the rounds view to somehow include dates (in each competition deails page)
- Improve the video matching with nswRugbyTV
- Improve notifications page; allow for typing to choose club/division, manage easy access to specific games for notifications
- Remove the force refresh from the homepage and somehow make it admin only (IP address?)