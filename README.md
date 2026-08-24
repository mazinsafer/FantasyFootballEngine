# Gridiron Lab

Weekly full-PPR fantasy football projections for QB, RB, WR, and TE — trained on six seasons of NFL data, explained by a constrained LLM, served from Databricks, and shown in a React analytics dashboard.

The product is an end-to-end pipeline, not a notebook demo: leakage-safe features → walk-forward XGBoost → GPT-5.6 Terra insights → FastAPI → **Gridiron Lab** UI.

---

## Architecture

```
nflverse (nfl_data_py)
        │
        ▼
ingestion/feature_building.ipynb
        │  overwrite
        ▼
fantasy_football.gold.player_weeks          ~29k player-weeks, 2020–2025
        │
        ├─ model-eval/                      walk-forward eval + 2026 week-1 slate
        └─ insights/insights_pipeline.ipynb
                │  replaceWhere (season, week)
                ▼
        fantasy_football.gold.predictions   projections + model insights
                │  Databricks SQL Connector
                ▼
        api/  FastAPI  :8000
                │
                ▼
        gridironlab/  React + TypeScript    latest week only
```

Gold is rebuilt from scratch on every feature run. Predictions are a **history table**: each run replaces only its own `(season, week)` partition. The API always serves the newest `(season, week)` in that table. The UI has no hardcoded week — after you write a new partition, it picks it up on the next fetch (API cache TTL is one hour; refresh the browser tab).

---

## Current status

| Phase | Status |
| --- | --- |
| Feature pipeline (`ingestion/`) | Done — Gold table in Unity Catalog |
| XGBoost + walk-forward evaluation (`model-eval/`) | Done — overall MAE **4.88** PPR |
| LLM insights (`insights/`) | Done — top 15 players / week, GPT-5.6 Terra |
| FastAPI (`api/`) | Done — reads Delta tables directly |
| React dashboard (`gridironlab/`) | Done — live data with sample fallback |

Seed slate in production tables: **2025 Week 17**. 2026 Week 1 is produced by `model-eval/week1_2026_slate_builder.py` once rosters and Vegas lines firm up.

---

## Repository

| Path | Role |
| --- | --- |
| `ingestion/` | Feature engineering notebook. Writes `player_weeks`. |
| `model-eval/` | Baseline, walk-forward tuning, 2025 week-1 validation, 2026 slate builder. |
| `insights/` | Production predict + RAG insights notebook. Writes `predictions`. |
| `api/` | FastAPI serving layer (Databricks SQL Connector). |
| `gridironlab/` | React + TypeScript UI (Vite, Tailwind). |
| `documentation/context.md` | Full file-by-file documentation, data contracts, and rules. |
| `.agents/skills/` | Cursor agent skills for architecture, features, and RAG. |

---

## Quick start

### 1. API

Python 3.10–3.12. The SQL warehouse must be running, and the token needs `SELECT` on both Gold tables.

```bash
cd api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill warehouse hostname, HTTP path, PAT
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- Health: http://localhost:8000/health

### 2. Dashboard

```bash
cd gridironlab
npm install
npm run dev
```

Opens http://localhost:5173. Defaults to `http://localhost:8000` (`VITE_API_URL` to override). If the API is down, the sidebar shows **Sample data** and a bundled 10-player 2025 Week 17 slate; otherwise it shows **Live data**.

Full API setup: [`api/README.md`](api/README.md). Frontend notes: [`gridironlab/README.md`](gridironlab/README.md).

---

## Weekly operations

In-season (after Monday Night Football):

1. Run `ingestion/feature_building.ipynb` (rebuilds Gold).
2. Optionally run `model-eval/walk_forward_model.ipynb` for monitoring.
3. Run `insights/insights_pipeline.ipynb` (writes that week’s predictions + insights).

The UI does **not** need a code change. Restart the API (or wait out the 1-hour cache) and refresh the browser.

For **2026 Week 1**, run `model-eval/week1_2026_slate_builder.py` in early September after roster cuts — that partition becomes the dashboard slate automatically.

---

## Model accuracy

Walk-forward MAE on 2025 weeks 11–17 (PPR points), vs a naive 3-week average:

| | Naive | Global | Per-position |
| --- | --- | --- | --- |
| QB | 7.19 | 6.39 | **6.36** |
| RB | 5.09 | **4.72** | 4.74 |
| WR | 5.13 | 4.65 | **4.60** |
| TE | 5.45 | **4.92** | 5.01 |
| **Overall** | 5.38 | 4.89 | **4.88** |

Scoring is full PPR everywhere:

```
0.04·pass yds + 4·pass TD − 2·INT
+ 0.1·rush yds + 6·rush TD
+ 0.1·rec yds + 6·rec TD + 1·reception
```

Rules that never break: shift every historical feature one week, reset rolling stats per season, drop same-week box score before training, weeks 1–17 only, time-ordered splits only. Details in [`documentation/context.md`](documentation/context.md).

---

## Secrets

Never commit these. Root `.gitignore` covers `.env` and `.ruff_cache/`.

| Secret | Where |
| --- | --- |
| Databricks PAT + warehouse | `api/.env` |
| OpenAI API key | `insights/.env` or Databricks scope `openai-creds` / `api-key` |

Pin `gpt-5.6-terra`. The `gpt-5.6` alias routes to Sol.

---

## License

Private project. NFL data via [nflverse](https://github.com/nflverse) / `nfl_data_py`.
