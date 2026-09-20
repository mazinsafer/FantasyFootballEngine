# Fantasy Football Engine API

FastAPI serving layer for historical player-weeks and model predictions stored in Unity Catalog Delta tables.

## Tables

| Table | Rows | Purpose |
| --- | --- | --- |
| `fantasy_football.gold.player_weeks` | ~29,049 | Historical player data, 2020–2025, weeks 1–22 |
| `fantasy_football.gold.predictions` | grows weekly | History table of projections plus AI insights; the latest partition (2026 Week 2) has 665 rows |

The warehouse must be running, and the personal access token needs `SELECT` on both tables.

## Setup

Python 3.10–3.12 is required (the pinned packages predate Python 3.13). Do not use 3.14 — `pydantic==2.5.0` has no wheel and the source build fails.

```bash
cd api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` with your SQL warehouse hostname, HTTP path, and access token:

```
DATABRICKS_SERVER_HOSTNAME=your-workspace.cloud.databricks.com
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/your-warehouse-id
DATABRICKS_ACCESS_TOKEN=your-personal-access-token
```

In Databricks, the HTTP path is under **SQL Warehouses → your warehouse → Connection details**.

## Run

From the `api` directory:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health: http://localhost:8000/health

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| GET | `/health` | API status and Databricks connectivity |
| GET | `/api/players` | Distinct players (latest appearance), filter by `position` / `team`, paginated |
| GET | `/api/players/{player_id}` | Latest week plus career summary |
| GET | `/api/players/{player_id}/history` | Weekly history across seasons |
| GET | `/api/predictions` | Latest-week projections (`position`, `team`, `min_projected_ppr`) |
| GET | `/api/predictions/top/{n}` | Top N projected players |
| GET | `/api/predictions/{player_id}` | Projection and insight for one player |
| GET | `/api/weeks/latest` | Most recent week in `player_weeks` |
| GET | `/api/weeks/{season}/{week}` | All player stats for that week |
| GET | `/api/teams/{team_abbr}` | Team roster with latest projections |

Pagination query params (where listed): `limit` (default 50, max 700) and `offset`.

Collection endpoints return an empty `items` array when filters match nothing. Lookups by `player_id` return **404** when the player is missing. Databricks failures return **500**; missing credentials return **503**.

## Implementation notes

- Connections are opened per query and closed in a context manager — nothing is left open.
- Filters are applied in SQL for `player_weeks` (29k rows). The predictions slate is small (665 rows for the latest week), so it is loaded once and cached in memory for 1 hour (`CACHE_TTL_SECONDS`).
- All bind parameters use `?` placeholders.
- Databricks `Decimal` values are converted to `float` (or `int` for rank/week/season) before JSON serialization.
- Nullable stats columns are returned as `null`, not omitted or coerced to zero.
- CORS is enabled (`CORS_ORIGINS`, default `*`) so a local frontend can call the API.

## Deploy on AWS (ECS Fargate)

The API runs as a single Fargate task (0.25 vCPU / 512 MB, ARM64) behind an Application Load Balancer, fronted by CloudFront. Production resources (all in `us-east-1`, account `814251983407`):

| Resource | Value |
| --- | --- |
| Container image | ECR `gridiron-lab-api` (built from `api/Dockerfile`) |
| ECS | cluster `gridiron-lab`, service `gridiron-lab-api`, task definition `api/ecs-task-def.json` |
| Secrets | SSM Parameter Store SecureStrings under `/gridiron-lab/*` (the three Databricks vars), injected by the task execution role |
| Load balancer | `gridiron-lab-alb` (HTTP :80 → container :8000, health check `/health`); its security group only admits CloudFront origin-facing IPs |
| Public HTTPS | `https://gridironlab.live` (+ `www`) → CloudFront distribution `d1mkvupgst3eb9.cloudfront.net`, which routes `/api/*` to the ALB (caching disabled); everything else serves the frontend from S3 |
| DNS / TLS | Route 53 hosted zone `gridironlab.live` (registered at Namecheap, delegated to AWS); ACM certificate for apex + `www` attached to CloudFront |

Because the API and frontend share the CloudFront origin, CORS is not needed in production (the task still sets `CORS_ORIGINS` to the CloudFront URL as a belt-and-suspenders measure).

To deploy a new API version:

```bash
cd api
aws ecr get-login-password | docker login --username AWS --password-stdin 814251983407.dkr.ecr.us-east-1.amazonaws.com
docker build --platform linux/arm64 -t 814251983407.dkr.ecr.us-east-1.amazonaws.com/gridiron-lab-api:latest .
docker push 814251983407.dkr.ecr.us-east-1.amazonaws.com/gridiron-lab-api:latest
aws ecs update-service --cluster gridiron-lab --service gridiron-lab-api --force-new-deployment
```

The restart also clears the 1-hour in-memory cache, so a newly written predictions partition shows up immediately.
