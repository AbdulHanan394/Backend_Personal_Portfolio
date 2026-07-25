# Abdul Core

Abdul Core is the FastAPI backend for Abdul Hanan's portfolio intelligence layer. It collects platform activity, normalizes it, enriches it with AI, embeds summaries for retrieval, stores structured records in PostgreSQL, and exposes a versioned REST API for the portfolio and future assistant clients.

## Local Development

1. Copy `backend/.env.example` to `backend/.env` and fill secrets.
2. Start dependencies and the API:

```bash
cd docker
docker compose up --build
```

3. Run migrations:

```bash
cd ../backend
alembic upgrade head
```

The API mounts v1 routes under `/api/v1`. Public portfolio reads require `X-API-Key`; this is a lightweight abuse filter, not strong security. Rate limiting and restricted CORS are still required.

## Portfolio Contracts

`GET /api/v1/activities` returns the exact activity shape expected by the existing Next.js portfolio slider. `POST /api/v1/assistant/query` returns `{ "data": { "answer": "..." } }`, matching the planned replacement for the mock `askAgent()`.

## Current Scope

The repository includes the full v1 structure, initial database schema, collectors, service seams, API contracts, scheduler wiring, Docker, and CI/CD skeletons. LinkedIn collection is intentionally manual-only in v1 because personal activity read access is not generally available through LinkedIn's API.

