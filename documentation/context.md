# Fantasy Football ML Prediction Engine — Complete Project Documentation

Last updated: August 24, 2026. This document describes exactly how every file in the repository works, the data contracts between them, the rules that must never be broken, and the current state of the project.

---

## 1. Project Overview

An end-to-end machine learning system that predicts weekly NFL fantasy football points (full-PPR scoring) for QB/RB/WR/TE, explains those predictions with LLM-generated insights, stores everything in Databricks Delta tables, and serves it over FastAPI. A React dashboard is the remaining phase.

**Pipeline phases (from the project blueprint):**

1. **Data layer (Databricks medallion)** — ingest raw NFL data, engineer features, store as a Gold Delta table. ✅ Done
2. **ML + LLM insights** — XGBoost models trained on Gold, GPT-5.6 Terra insights via the OpenAI API, results in a `predictions` Delta table. ✅ Done
3. **FastAPI serving layer** — `api/` reads Gold Delta tables through the Databricks SQL Connector (no Lakebase sync). ✅ Done
4. **React TypeScript frontend** — dashboard displaying projections + insights. ⬜ Not started

**Runtime environment:** Databricks (Unity Catalog + Delta). The notebooks originated as local Jupyter notebooks working against parquet files and were migrated; all table I/O now goes through `spark.table(...)` / `saveAsTable(...)`.

**Scoring formula (full PPR), used everywhere:**

```
fantasy_points_ppr = 0.04*pass_yds + 4*pass_TD − 2*INT
                   + 0.1*rush_yds + 6*rush_TD
                   + 0.1*rec_yds  + 6*rec_TD + 1*reception
```

---

## 2. Data Flow

```
nfl_data_py (nflverse public data)
        │
        ▼
ingestion/feature_building.ipynb          ← builds everything from scratch each run
        │  writes
        ▼
fantasy_football.gold.player_weeks        ← Gold Delta table (~29k rows, 2020–2025)
        │  read by
        ├─ model-eval/baseline_model.ipynb          (static-split benchmark)
        ├─ model-eval/walk_forward_model.ipynb      (tuning + honest evaluation)
        ├─ model-eval/week1_prediction.ipynb        (2025 wk1 cold-start validation)
        ├─ model-eval/week1_2026_slate_builder.py   (future 2026 wk1 slate)
        └─ insights/insights_pipeline.ipynb         (production predictions + insights)
                │  writes (replaceWhere per season/week — history table)
                ▼
        fantasy_football.gold.predictions
                │  read by (Databricks SQL Connector, SELECT only)
                ▼
        api/  FastAPI on :8000                      ← seeds the future UI
```

---

## 3. Delta Tables (Unity Catalog)

### `fantasy_football.gold.player_weeks`

One row per player per game played, seasons 2020–2025, weeks 1–22 (model notebooks filter to 1–17). Written with `mode("overwrite")` + `overwriteSchema` — it is a full rebuild every run. Contains three kinds of columns:

1. **Identifiers:** `player_id` (GSIS id, string), `player_name`, `season`, `week`, `recent_team`, `position` (QB/RB/WR/TE), `opponent`, `starting_qb_id`, `gameday`.
2. **Same-week raw stats** (box score of that game — kept only as intermediates; every model drops them via the leakage guard): `pass_attempts`, `completions`, `passing_yards`, `passing_tds`, `interceptions`, `rush_attempts`, `rushing_yards`, `rushing_tds`, `targets`, `receptions`, `receiving_yards`, `receiving_tds`, `fantasy_points_ppr` (the **target**), plus usage intermediates `player_opportunities`, `team_total_opportunities`, `opportunity_share`, `hvt_carries`, `hvt_targets`, `total_hvts`, `team_pass_attempts`, `target_share`, `player_air_yards`, `team_air_yards`, `air_yards_share`, `wopr`, `snap_share`.
3. **Pre-game features** (all leakage-free — see section 5): listed per category in section 4.2.

### `fantasy_football.gold.predictions`

**History table, never fully overwritten.** Keyed by `(season, week, player_id)`. Writers use `mode("overwrite")` with `option("replaceWhere", "season = X AND week = Y")` so each run replaces only its own week's partition. The 2025 Week 17 rows are the permanent seed data for the API/UI. Columns: identifiers + `projected_ppr`, `actual_ppr` (null/absent for future weeks), context features used for RAG (`implied_total`, `team_spread`, `team_win_prob`, `is_home`, `temp`, `wind`, `is_bad_weather`, `is_dome`, `fantasy_points_3wk_avg`, `depth_chart_rank`, `opp_def_ppg_allowed`, `prev_season_ppg`), and `insight` / `insight_source` (LLM text, top 15 players per week; `mergeSchema` enabled for the insight columns).

---

## 4. File-by-File Documentation

### 4.1 `ingestion/nfl_py_extraction.ipynb` (7 cells)

The original exploratory extraction notebook, **2025-season only**. Historically the first step of the pipeline; `feature_building.ipynb` now loads all data itself, so this notebook is reference/exploration, not a dependency.

- Cell 0: `%pip install --no-deps nfl_data_py` + `appdirs fastparquet pandas` (the `--no-deps` avoids a broken transitive pin in nfl_data_py).
- Cell 1: imports.
- Cell 2: `nfl.import_pbp_data([2025])` — play-by-play.
- Cell 3: `nfl.import_schedules([2025])` — includes Vegas lines and weather.
- Cell 4: `nfl.import_snap_counts([2025])`.
- Cell 5: aggregates play-by-play into weekly player stats (passer/rusher/receiver groupbys, identical logic to feature_building cell 5) and computes `fantasy_points_ppr` with the PPR formula.
- Cell 6: `nfl.import_injuries([2024, 2025])` and `nfl.import_seasonal_rosters([2025])`.

### 4.2 `ingestion/feature_building.ipynb` (30 cells) — THE FEATURE PIPELINE

Builds the Gold table from scratch. `SEASONS = [2020, 2021, 2022, 2023, 2024, 2025]`.

**Cell 5 — Load + weekly stats.** Loads six datasets: `import_pbp_data(SEASONS, downcast=True)`, `import_schedules`, `import_snap_counts`, `import_injuries`, `import_seasonal_rosters`, and depth charts **split by schema era** — `import_depth_charts([≤2024])` (weekly lists with a `depth_team` rank) and `import_depth_charts([≥2025])` (daily snapshots with `dt`/`pos_rank`). Then builds `weekly_stats`: three groupbys over play-by-play on `['season','week',{passer|rusher|receiver}_player_id, ..._player_name]` producing passing (attempts, completions, yards, TDs, INTs), rushing (attempts, yards, TDs) and receiving (targets = pass attempts to that receiver, receptions, yards, TDs) stats; outer-merged on `['season','week','player_id','player_name']`, numeric NaNs → 0, PPR points computed.

**Cell 7 — Positions and teams.** Position heuristic from play-by-play roles (passer→QB, rusher→RB, receiver→WR, most-common wins), then **overridden by official roster positions** where the roster says QB/RB/WR/TE/FB (FB mapped to RB) — this is how TEs are identified at all, and how pass-catching RBs avoid being tagged WR. Uses each player's **latest-season** roster position. Teams are resolved **per season** (`player_team`: last team seen in play-by-play that season) because players change teams between years.

**Cell 9 — Category 1: game context.** From schedules:
- `home_implied_total = total_line/2 + spread_line/2`, `away = total_line/2 − spread_line/2`. **Sign convention: nflverse `spread_line` is positive when the HOME team is favored.**
- `team_win_prob` from moneylines: `p = −ml/(−ml+100)` if ml<0 else `100/(ml+100)`; missing → 0.5. (Historical player-prop lines are not freely available anywhere; game-level spread/total/moneyline is the full obtainable Vegas signal.)
- `is_dome` = roof in {dome, closed}. `is_bad_weather` = (wind>15 or temp<32) **and not a dome** (schedules have no precipitation column).
- Home/away contexts stacked into one `game_context` frame with `team_spread` from each team's perspective (positive = that team favored) and `starting_qb_id` from `home_qb_id`/`away_qb_id`.
- `rest_advantage` = own days-since-last-game − opponent's, computed per `(team, season)` so the offseason gap never counts; NaN → 0.
- Merged into `weekly_stats_df` on `(season, week, recent_team)`.

**Cell 11 — Category 2: rolling form + season carryover.**
- `fantasy_points_3wk_avg` / `5wk_avg`: `groupby(['player_id','season'])[target].shift(1).rolling(3|5, min_periods=1).mean()` — **shifted one week and reset each season**.
- `prev_season_ppg` / `prev_season_games`: per-player mean PPR and games count aggregated per season, then the season key is **shifted forward one year** (2024 stats attach to 2025 rows). Rookies and the first loaded season get 0. These are the cold-start prior for week 1.

**Cell 13 — Category 3: QB features.** For QB rows only: shifted 3/5-week rolling means of `pass_attempts` and `rushing_yards` (rushing floor). Plus two team-level pressure rates from play-by-play dropbacks (`qb_dropback == 1`), both **shifted season-to-date cumulative rates** (cum sacks ÷ cum dropbacks through the previous week): `team_sack_rate_allowed` (own O-line proxy, keyed by `posteam`) and `opp_def_sack_rate` (matchup, keyed by `defteam`, merged on the opponent).

**Cell 15 — Category 4: RB features.** For RB rows only, all shifted 3/5-week rolling means reset per season:
- `rb_opportunity_share_*`: (rush attempts + targets) ÷ team total (team rush + pass attempts from play-by-play).
- `rb_hvts_*`: high-value touches = carries + targets with `yardline_100 <= 10`.
- `rb_snap_share_*`: from `snap_counts.offense_pct`. **Snap counts are keyed by PFR ids** — mapped to GSIS ids via the roster's `pfr_id` column.

**Cell 17 — Category 5: WR/TE features.** For WR/TE rows only, all shifted 3/5-week rolling means:
- `wr_te_target_share_*`: targets ÷ team pass attempts.
- `wr_te_air_yards_share_*`: player air yards ÷ team air yards (from play-by-play `air_yards`).
- `wr_te_wopr_*`: WOPR = `1.5*target_share + 0.7*air_yards_share`.
- `starting_qb_aya`: the scheduled starting QB's shifted season-to-date Adjusted Yards per Attempt = `(yards + 20*TD − 45*INT) / attempts`, joined via `starting_qb_id` from the schedule.

**Cell 19 — Category 6: matchup.** All shifted season-to-date, reset per season:
- `opp_def_ppg_allowed`: average PPR points the opponent's defense has allowed **to this position** (cumsum shifted ÷ weeks played).
- `opp_def_ypc_allowed` (rush plays) and `opp_def_ypp_allowed` (run+pass): yards-per-play rates keyed by `defteam`. These are the DVOA substitutes (DVOA is premium data).

**Cell 21 — Category 7: `wr1_wr2_healthy`.** Identifies each team's WR1/WR2 as the two WRs with the most **cumulative targets through the previous week** (a full player×week grid is built so injured WRs who miss weeks still rank), then flags 1 if neither is Out/Doubtful on that week's injury report (`nfl.import_injuries`, joined on `gsis_id`). Week 1 has no target history → ranking arbitrary, defaults healthy.

**Cell 23 — Category 8: `depth_chart_rank` + starter filter.** Two-era handling: 2023–24 weekly lists join directly on `(player_id, season, week)` (min `depth_team` across formations, offense only); 2025+ daily snapshots use `pd.merge_asof` backward on `gameday` (latest snapshot before the game; `player_id` cast to str on both sides — required to avoid a dtype MergeError). Ranks are forward-filled over gaps within a season; never-listed players get sentinel rank 9. Then the **QB/TE starter filter**: rows for QBs and TEs with `depth_chart_rank != 1` are dropped entirely (backups are not fantasy-relevant at one-man positions); RB/WR keep all ranks (committees and WR2/WR3 matter).

**Cell 25 — Final cleanup.** Fills NaN → 0 for the explicit 35-feature list, copies to `gold_df`.

**Cell 27 — Quality report.** Prints record counts, position breakdown, feature category summary, missing-value check, leakage statement, top performers sample.

**Cell 29 — Persist.** `spark.createDataFrame(gold_df).write.format("delta").mode("overwrite").option("overwriteSchema","true").saveAsTable("fantasy_football.gold.player_weeks")`.

### 4.3 `model-eval/baseline_model.ipynb` (14 cells)

The original benchmark — one static split, default hyperparameters. Kept as a reference point; `walk_forward_model.ipynb` supersedes it.

- Loads `fantasy_football.gold.player_weeks` (falls back to an existing `gold_df` global if a prior notebook ran in the same kernel), filters `week <= 17`.
- Preprocessing (the **standard leakage guard**, identical in all four model files): saves `eval_meta` (identifiers, kept aside with aligned index), drops identifier columns (`player_id`, `player_name`, `recent_team`, `opponent`, `starting_qb_id`, `gameday`), drops **all 25 same-week outcome columns** (box score + usage intermediates — they would leak the answer since receptions directly determine PPR), one-hot encodes `position` into `pos_QB/RB/WR/TE`, fills NaN → 0, drops any residual non-numeric column.
- Split: train = all seasons before the latest + weeks 1–10 of the latest; test = weeks 11+ of the latest. Never shuffled.
- Model: `XGBRegressor(n_estimators=100, learning_rate=0.1, max_depth=4, random_state=42)`.
- Evaluation: overall MAE, MAE by position, naive baseline (predict `fantasy_points_3wk_avg`), sample predictions, top-10 feature importance chart.

### 4.4 `model-eval/walk_forward_model.ipynb` (14 cells) — THE EVALUATION HARNESS

The honest measure of model quality, and the source of the production hyperparameters.

- **Scope:** `FANTASY_MAX_WEEK = 17` — week 18 (starters rest) and playoffs 19–22 excluded from training *and* testing.
- **Preprocessing:** standard leakage guard (same as 4.3), but `position` kept as a plain column so per-position models can slice on it.
- **Engine (`walk_forward`)**: for each test week W of the latest season — train on all prior seasons plus current-season weeks ≤ W−2, early-stop (20 rounds patience, max 500 rounds) on week W−1, predict week W. Parameters: `params` (hyperparameters), `first_test_week` (default 11), `last_test_week`, `verbose`. Returns per-row actual/predicted indexed like the input, enabling exact-row comparisons between approaches.
- **Hyperparameter tuning (leakage-safe):** 12-config grid — `max_depth ∈ {3,4,6} × learning_rate ∈ {0.03,0.05} × min_child_weight ∈ {1,5}`, all with `subsample=0.8, colsample_bytree=0.8` — scored by walk-forward on **tuning weeks 5–10** only. Test weeks 11–17 never influence the choice. Winner stored in `BEST_PARAMS`. Last run selected `max_depth=4, learning_rate=0.05, min_child_weight=1, subsample=0.8, colsample_bytree=0.8`.
- **Model A (global):** one model, position one-hot encoded, `BEST_PARAMS`, weeks 11–17.
- **Model B (per-position):** four models (QB/RB/WR/TE), each on its own rows with `shared_features` (game context, form, carryover, generic matchup) plus its position's feature group. Same `BEST_PARAMS`.
- **Comparison:** naive (3-week average) vs global vs per-position on identical test rows, MAE by position + overall, plus a weekly-MAE line chart.

### 4.5 `model-eval/week1_prediction.ipynb` (10 cells) — COLD-START VALIDATION

Retrospectively predicts **2025 Week 1** using only preseason-knowable information, validating the approach the 2026 slate builder relies on.

- Standard leakage guard, weeks ≤ 17.
- Split: train = all 2020–2024 rows **except** 2024 Week 1; validation (early stopping) = 2024 Week 1 (the most recent week-1-like distribution); test = 2025 Week 1. The model sees `week` as a feature and learns from five historical week 1s how to behave when all rolling features are 0.
- Model: `XGBRegressor(n_estimators=500, learning_rate=0.05, max_depth=4, min_child_weight=5, subsample=0.8, colsample_bytree=0.8, early_stopping_rounds=20)`. Predictions clipped at 0.
- Evaluation: MAE vs two naive baselines (predict `prev_season_ppg`; predict training mean), MAE by position, top-25 projected players vs actual, biggest over/under-projections, top-15 feature importance.
- Caveat stated in the notebook: rows are players who actually recorded a stat (Gold is play-by-play-derived); a live system builds the slate from schedule + roster + depth chart — which is exactly what 4.6 does.

### 4.6 `model-eval/week1_2026_slate_builder.py` (Databricks notebook source) — FUTURE PREDICTION

Builds a **forward-looking slate** for 2026 Week 1 (rows that don't exist in Gold because the games haven't been played) and predicts it.

- **Game context:** `nfl.import_schedules([2026])` week-1 games → home/away rows; away spread flipped; `team_win_prob` from moneylines (missing → 0.5); `is_dome` from roof; weather set to neutral (temp 72, wind 0) because it's unknowable pre-game-week; `missing_vegas_lines` flag for preliminary lines.
- **Players:** `nfl.import_seasonal_rosters([2026])` filtered to QB/RB/WR/TE, joined to the latest 2026 depth chart snapshot per player (`depth_chart_rank`, 99 = not listed).
- **Carryover:** `prev_season_ppg`/`prev_season_games` computed from the Gold table's 2025 rows; rookies → 0 (known limitation: the model underrates rookies).
- **Feature alignment:** all in-season rolling features set to 0 (matching what the trained model saw for historical week-1 rows); columns aligned to the exact training feature set + position dummies, in order.
- **Model:** same architecture/hyperparameters as 4.5, trained on all 2020–2025 Gold data (weeks 1–17), early-stopped on 2025 Week 1.
- **Output:** `replaceWhere season=2026 AND week=1` into `fantasy_football.gold.predictions`.
- **QB/TE starter filter:** backup QBs and TEs (depth_chart_rank ≠ 1) are dropped from the slate, matching the Gold table's business rule — the model was trained exclusively on starter QB/TE rows.
- **Production schedule:** run in the **first week of September 2026** — before final roster cuts (~Sept 1) depth charts show camp bodies and Vegas lines are preliminary.

### 4.7 `insights/insights_pipeline.ipynb` (6 cells) — PRODUCTION PREDICTIONS + LLM INSIGHTS

(Formerly `bedrock/insights_pipeline.ipynb`. LLM calls go to the **OpenAI API directly** — the original Bedrock route required an account-level marketplace subscription for GPT-5.6 that never finished provisioning, so it was abandoned. The API key lives in `insights/.env`, which is git-ignored.)

**Cell 3 — Predictions table.** Standard leakage guard, weeks ≤ 17. Targets the most recent completed fantasy week W of the latest season: train on everything strictly before W−1 (all prior seasons + current season ≤ W−2), early-stop on W−1, predict W — the exact fold layout validated in 4.4, with its tuned hyperparameters. Builds `predictions_df` = identifiers + `projected_ppr` (clipped ≥ 0, rounded 1dp) + `actual_ppr` (retrospective) + 12 context columns for RAG. Writes to `fantasy_football.gold.predictions` with `replaceWhere` on `(season, week)` — history-table semantics.

**Cell 5 — RAG insights.**
- `OPENAI_MODEL = 'gpt-5.6-terra'` — the explicit Terra id. **Do not use the `gpt-5.6` alias — it routes to Sol** (the flagship, ~6x the price). Terra: ~$2/M input, $12/M output tokens.
- API key resolution (in order): a `.env` file loaded via `python-dotenv` (`OPENAI_API_KEY`, optional `OPENAI_API_BASE` for a custom endpoint), Databricks secret scope `openai-creds` / key `api-key`, then the plain environment variable. `.env` files are git-ignored at the repo root.
- Calls use the **Responses API** — GPT-5.6 models are reasoning models and reject Chat Completions parameters like `temperature`/`max_tokens`.
- `build_prompt(row)` — the AUGMENT step: injects projection, 3-week form, prev-season average, Vegas (implied total / spread / win prob), opponent defense PPG allowed to the position, depth chart rank, venue and weather. Instructs the LLM to write 2–3 sentences using ONLY the provided data (one supporting factor, one risk factor, no invented news).
- `make_llm()` — smoke-tests the OpenAI Responses API (`client.responses.create` with `reasoning={'effort':'low'}`, `max_output_tokens=500`, `store=False`); on any failure returns the offline path.
- `template_insight(row)` — deterministic fallback so the pipeline always completes end-to-end without a key.
- Insights generated for the **top 15** projected players (cost bound), merged back, written to the predictions table with `mergeSchema` (adds `insight`, `insight_source` columns).

### 4.8 `.agents/skills/` — Cursor agent skills (project knowledge base)

- `fantasy-engine-architecture/SKILL.md` — the four pipeline phases, where code lives, the walk-forward fold layout, and the MAE accuracy targets by position.
- `feature-engineering-rules/SKILL.md` — the business rules for every feature, the nfl_data_py source mapping, empirically-verified data gotchas (spread sign convention, no precipitation column, PFR↔GSIS id mapping, scheduled-starter QB ids), premium-data workarounds (DVOA → PPG/YPP allowed; O-line rank → sack rate allowed), the weeks-1–17 scope, and the QB/TE starter-only evaluation rule.
- `clustering-and-rag/SKILL.md` — design for player archetype clustering (not yet implemented) and the retrieve→augment→generate insight flow (implemented in 4.7).

### 4.9 `.gitignore`

`/CONTEXT.md` (the original private blueprint, root only — scoped so this documentation file stays tracked), `.DS_Store`, `data/` (local parquet artifacts from the pre-Databricks era), `.env` (OpenAI key and Databricks PAT). `api/.gitignore` additionally ignores `api/.venv`.

### 4.10 `api/` — FASTAPI SERVING LAYER

Read-only HTTP API over the two Gold Delta tables. Lives on the `backend` branch. The original blueprint called for syncing predictions into Lakebase (managed Postgres) and querying via SQLAlchemy; the implemented design skips that extra copy and queries Unity Catalog directly with the **Databricks SQL Connector**. The SQL warehouse must be running, and the PAT needs `SELECT` on both Gold tables.

Run from `api/` (Python 3.10–3.12; pinned deps predate 3.13):

```
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Swagger UI at `/docs`, ReDoc at `/redoc`, liveness/readiness at `/health`.

**`config.py`.** Loads `api/.env` (then repo-root `.env`) via `python-dotenv`. Required: `DATABRICKS_SERVER_HOSTNAME`, `DATABRICKS_HTTP_PATH`, `DATABRICKS_ACCESS_TOKEN`. Optional: `DATABRICKS_CATALOG` (default `fantasy_football`), `DATABRICKS_SCHEMA` (default `gold`), `CORS_ORIGINS` (default `*`), `CACHE_TTL_SECONDS` (default 3600). Table names are interpolated only from these config values, never from request input.

**`database.py`.** Connection manager — `sql.connect(...)` inside a context manager so every request opens and closes the warehouse connection; nothing is left open. `execute_query` / `execute_query_one` log the compacted SQL + bind params, use `?` placeholders, and convert Databricks `Decimal` → `float` (or `int` for `season`/`week`/`depth_chart_rank`/`wr1_wr2_healthy`) and NaN → `None` so JSON serialization is valid. `TTLCache` holds the latest-week predictions payload in process memory.

**`models.py`.** Pydantic v2 response models. `PlayerWeek` maps all 72 Gold columns (nullable stats stay `null`, never coerced to 0). `Prediction` maps all 23 predictions columns including `insight` / `insight_source`. List endpoints wrap `total` / `limit` / `offset` / `items`.

**`main.py`.** CORS enabled for the future React app. Endpoints:

| Method | Path | Behavior |
|---|---|---|
| GET | `/health` | Warehouse `SELECT 1` plus a probe of both Gold tables. Missing creds → `unconfigured`; query failure → `disconnected`. Always HTTP 200 with a status payload (the API process is up). |
| GET | `/api/players` | Latest appearance per `player_id` (`ROW_NUMBER` on season/week desc). Filters: `position`, `team`. Paginated (`limit` default 50, max 500, `offset`). |
| GET | `/api/players/{player_id}` | Latest week + career summary (`games_played`, `career_ppg`, `career_high`). **404** if unknown. |
| GET | `/api/players/{player_id}/history` | All player-weeks, optional `season` filter, paginated. **404** if unknown. |
| GET | `/api/predictions` | Latest `(season, week)` in the predictions table. Filters: `position`, `team`, `min_projected_ppr`. Served from the 1-hour in-memory cache after the first warehouse hit (~269 rows). |
| GET | `/api/predictions/top/{n}` | Same cache, ranked by `projected_ppr` (`n` 1–100). Registered before `/{player_id}` so `top` is not parsed as an id. |
| GET | `/api/predictions/{player_id}` | Cache lookup, then a targeted SQL fallback. **404** if none. |
| GET | `/api/weeks/latest` | Max `(season, week)` in `player_weeks`, then the week endpoint. |
| GET | `/api/weeks/{season}/{week}` | All Gold rows for that week, filters `position`/`team`, paginated, ordered by `fantasy_points_ppr` desc. Empty `items` (not 404) when the week has no rows. |
| GET | `/api/teams/{team_abbr}` | Latest player-week per player currently on that team, left-joined to the latest prediction week. |

`player_weeks` filters are applied in SQL (29k rows). Predictions are filtered in memory after one cached full-week fetch. Collection misses return empty arrays; resource-by-id misses return 404; Databricks errors return 500; missing credentials return 503.

**`requirements.txt`.** Pinned: `fastapi==0.104.1`, `uvicorn[standard]==0.24.0`, `databricks-sql-connector==3.0.0`, `python-dotenv==1.0.0`, `pydantic==2.5.0`.

---

## 5. The Rules That Must Never Be Broken

1. **Shift everything.** Every historical feature uses `.shift(1)` (rolling means) or a shifted cumulative sum (season-to-date rates). Week N rows may only contain information available before week N kicks off.
2. **Reset per season.** All rolling/expanding calculations group by `(entity, season)`. December form never leaks into September.
3. **Drop the same-week box score before training.** The 25 `same_week_outcome_cols` exist in Gold only as intermediates. Any model that keeps them is cheating (receptions literally determine PPR points).
4. **Weeks 1–17 only.** Week 18 starters rest; weeks 19–22 are playoffs. Excluded from training and evaluation everywhere.
5. **Time-ordered splits only.** Walk-forward fold: train ≤ W−2, early-stop on W−1, predict W. Never shuffle, never tune on test weeks (tuning uses weeks 5–10; testing uses 11–17).
6. **QB/TE starters only** (depth_chart_rank == 1) in the Gold table; RB/WR keep all depth ranks.
7. **Secrets never in code.** OpenAI key via env var or Databricks secret scope; Databricks PAT in `api/.env`; AWS creds (if ever needed again) likewise.

---

## 6. Latest Validated Results

From the last full run (6 seasons, tuned, weeks 11–17 of 2025 as test):

| MAE (PPR points) | Naive 3wk avg | Global walk-forward | Per-position |
|---|---|---|---|
| QB | 7.19 | 6.39 | **6.36** |
| RB | 5.09 | **4.72** | 4.74 |
| WR | 5.13 | 4.65 | **4.60** |
| TE | 5.45 | **4.92** | 5.01 |
| **Overall** | 5.38 | 4.89 | **4.88** |

2025 Week 1 cold start: model **4.58** vs 5.08 (naive prev-season PPG) vs 6.21 (training mean). QB is the hardest position cold (6.99); RB (3.82) and TE (3.76) are very predictable. Biggest misses are genuinely unknowable pre-game: outlier eruptions (Josh Allen 39.1 vs 18.4 projected) and rookie breakouts (prev_season_ppg = 0).

Top predictive features (walk-forward): `fantasy_points_5wk_avg`, `fantasy_points_3wk_avg`, `depth_chart_rank`, `prev_season_ppg`, position dummies, `implied_total`.

---

## 7. Known Issues and Gotchas

### `week1_2026_slate_builder.py` — fixed bugs (Aug 23, 2026) and accepted limitations

1. **Inverted implied total — FIXED.** The original code computed `implied_total = total/2 − spread/2` on a team-perspective spread (positive = favored), giving favorites a *lower* implied total. Now `total/2 + spread/2` (matching the feature pipeline's convention), with missing totals filled to a league-average 44.0 and missing spreads to 0.
2. **Wrong depth chart schema for 2026 — FIXED.** The original code read the pre-2025 weekly schema (`week`/`depth_team`/`full_name` name-based join), which doesn't exist in 2025+ data. Now uses the snapshot schema (`dt`/`pos_abb`/`pos_rank`) with min rank per player per snapshot day, latest snapshot kept, joined on `gsis_id` — mirroring feature_building cell 23.
3. **Backup QB/TEs in the slate — FIXED.** The slate now drops QB/TE rows with `depth_chart_rank != 1`, matching the Gold table's starter-only rule (the model never saw backup QB/TE rows in training).
4. **Cosmetic (left as-is):** the `rolling_features` zero-fill list contains a few names that don't exist in Gold (`hvt_3wk_avg`, `pass_rate_diff`, `blitz_rate_diff`, `opp_def_pressure_rate`, `injury_severity`). Harmless — the alignment step selects only real training columns.
5. **By design (accepted):** `opp_def_ppg_allowed` and all in-season features are 0 for a future week 1 (matches training-time week-1 rows); rookies are underrated (no prior-season data); weather is neutral-filled.

### General gotchas

- **nflverse `spread_line` is positive when the home team is favored.** Every Vegas derivation depends on this convention.
- **Snap counts use PFR player ids**, not GSIS — always map through the roster's `pfr_id`.
- **Depth charts changed schema in 2025** — any new season's code must use the snapshot era logic.
- The `gpt-5.6` OpenAI alias routes to **Sol**, not Terra — always pin `gpt-5.6-terra`.
- `import_pbp_data` downloads ~50MB/season; the feature notebook takes a few minutes on first run per environment.
- Gold is fully rebuilt on every feature-notebook run (overwrite). The predictions table is **not** — only the targeted `(season, week)` partition is replaced.

---

## 8. Operations

- **Weekly in-season cadence (recommended job):** Tuesday mornings after Monday Night Football — `feature_building` → `walk_forward_model` (optional monitoring) → `insights_pipeline`. The API cache TTL is 1 hour, so a warehouse write is visible to clients within that window (or after a process restart).
- **2026 Week 1:** run the slate builder in the first week of September 2026 (after final roster cuts and firm Vegas lines).
- **Cluster packages:** `nfl_data_py` (install with `--no-deps`, then `appdirs fastparquet`), `xgboost`, `scikit-learn`, `matplotlib`, `openai`.
- **API packages:** see `api/requirements.txt`. Local run: `cd api && python3.12 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && cp .env.example .env` then fill warehouse hostname / HTTP path / PAT.
- **Secrets:** OpenAI key in `insights/.env` (git-ignored) or Databricks secret scope `openai-creds`, key name `api-key`. Databricks PAT in `api/.env` (`DATABRICKS_ACCESS_TOKEN`).
- **Accuracy targets** (from the blueprint, per-week MAE achieved ✅): the engine's 4.88 overall / per-position results in section 6 are competitive with industry projection systems.
