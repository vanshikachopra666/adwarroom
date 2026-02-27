# Competitor Ad War Room

Production-oriented competitive intelligence platform for monitoring Meta Ad Library activity across Mosaic brand categories (`bebodywise`, `manmatters`, `littlejoys`).

## What This Includes

- FastAPI backend with PostgreSQL + SQLAlchemy ORM.
- Meta Ad Library ingestion client (OAuth token, pagination, retries, status filters).
- Historical snapshot storage (no overwrites, timestamped snapshots).
- OpenAI-powered ad classification with strict JSON validation + retry.
- Weekly analytics engine for trend/shift/longevity/experimentation metrics.
- Opportunity gap detection (`Underutilized Messaging Opportunity`, `Untapped Creative Format`).
- Weekly executive brief generation endpoint with numeric validation.
- Next.js + TypeScript + Tailwind + Recharts infographic dashboard.
- PDF brief export.
- Weekly automation worker and Render cron config.
- Dockerfiles for backend and frontend.

## Repository Layout

- `/backend` FastAPI service
- `/frontend` Next.js dashboard
- `/render.yaml` Render deployment + cron blueprint
- `/vercel.json` Vercel config
- `/docker-compose.yml` local multi-service setup

## Backend Setup

```bash
cd /Users/vanshikachopra/Documents/New\ project/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Backend base URL: `http://localhost:8000/api/v1`

Key endpoints:

- `GET /health`
- `GET /competitors?mosaic_brand=bebodywise`
- `POST /ingest/run?mosaic_brand=bebodywise`
- `POST /analytics/recompute`
- `GET /dashboard?mosaic_brand=bebodywise&competitor=Minimalist&start_date=2026-01-01&end_date=2026-02-01&creative_format=UGC&message_theme=Authority&status=active`
- `GET /weekly-brief/{mosaic_brand}`
- `GET /weekly-brief/{mosaic_brand}/pdf`

## Frontend Setup

```bash
cd /Users/vanshikachopra/Documents/New\ project/frontend
npm install
cp .env.example .env.local
npm run dev
```

Frontend URL: `http://localhost:3000`

## Local Docker Run

```bash
cd /Users/vanshikachopra/Documents/New\ project
docker compose up --build
```

## Weekly Automation

Manual run:

```bash
cd /Users/vanshikachopra/Documents/New\ project/backend
python -m app.workers.weekly_job
```

Pipeline actions:

1. Ingest latest competitor snapshots.
2. Run AI classification for new ads.
3. Recompute weekly metrics.
4. Regenerate weekly briefs for all Mosaic brands.

## Render Deployment (Backend)

1. Push repository to GitHub.
2. In Render, create blueprint deploy from `render.yaml`.
3. Set secret env vars in Render:
   - `DATABASE_URL`
   - `OPENAI_API_KEY`
   - `META_ACCESS_TOKEN`
4. Ensure PostgreSQL instance is provisioned and its URL is attached.
5. Deploy web service and cron service.

## Vercel Deployment (Frontend)

1. Import repository in Vercel.
2. Set root directory to `frontend`.
3. Configure env var:
   - `NEXT_PUBLIC_API_BASE_URL=https://<your-render-api-domain>/api/v1`
4. Deploy.

## Data Model

Tables implemented:

- `competitors`
- `ads`
- `ai_classifications`
- `weekly_metrics`

All ads are stored with `scraped_at` snapshots to preserve history.

## Notes

- Seed data includes 15 competitors across three Mosaic categories.
- To ingest real data, provide a valid Meta Ad Library token in `META_ACCESS_TOKEN`.
- AI features require `OPENAI_API_KEY`.
