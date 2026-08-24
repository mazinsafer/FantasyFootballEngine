"""Fantasy Football Engine FastAPI application.

Serves historical player weeks and model predictions from Unity Catalog
Delta tables via the Databricks SQL Connector.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Path, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import get_settings
from database import (
    DatabricksNotConfiguredError,
    QueryError,
    execute_query,
    execute_query_one,
    ping,
    predictions_cache,
)
from models import (
    ErrorResponse,
    HealthResponse,
    PlayerCareerSummary,
    PlayerDetail,
    PlayerHistoryResponse,
    PlayerListResponse,
    PlayerSummary,
    PlayerWeek,
    Prediction,
    PredictionListResponse,
    TeamPlayer,
    TeamResponse,
    WeekStatsResponse,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("fantasy_api")

MAX_LIMIT = 500
DEFAULT_LIMIT = 50
ERROR_RESPONSES = {
    404: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
    503: {"model": ErrorResponse},
}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    if settings.is_configured:
        logger.info(
            "Starting API (warehouse=%s catalog=%s.%s)",
            settings.server_hostname,
            settings.catalog,
            settings.schema,
        )
    else:
        logger.warning(
            "Starting API without Databricks credentials. "
            "Copy api/.env.example to api/.env and fill in your warehouse details."
        )
    yield
    predictions_cache.clear()
    logger.info("API shutdown complete")


settings = get_settings()

app = FastAPI(
    title="Fantasy Football Engine API",
    description=(
        "Read-only serving layer for the Fantasy Football ML Prediction Engine.\n\n"
        "Data is queried from Unity Catalog Delta tables:\n"
        f"- `{settings.player_weeks_table}` — historical player-weeks (2020–2025)\n"
        f"- `{settings.predictions_table}` — model projections and AI insights\n\n"
        "Interactive docs are available at `/docs` (Swagger UI) and `/redoc`."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DatabricksNotConfiguredError)
async def unconfigured_handler(_request, exc: DatabricksNotConfiguredError):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(QueryError)
async def query_error_handler(_request, _exc: QueryError):
    return JSONResponse(
        status_code=500,
        content={"detail": "Database query failed. Check API logs for details."},
    )


def _clamp_pagination(limit: int, offset: int) -> tuple[int, int]:
    return max(1, min(limit, MAX_LIMIT)), max(0, offset)


def _normalize_position(position: Optional[str]) -> Optional[str]:
    if position is None or not position.strip():
        return None
    return position.strip().upper()


def _normalize_team(team: Optional[str]) -> Optional[str]:
    if team is None or not team.strip():
        return None
    return team.strip().upper()


def _pop_total(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    if not rows:
        return [], 0
    total = int(rows[0].get("total") or 0)
    cleaned = [{k: v for k, v in row.items() if k != "total"} for row in rows]
    return cleaned, total


def _latest_slate(table: str) -> tuple[int, int] | None:
    row = execute_query_one(
        f"""
        SELECT season, week
        FROM {table}
        ORDER BY season DESC, week DESC
        LIMIT 1
        """
    )
    if not row or row.get("season") is None or row.get("week") is None:
        return None
    return int(row["season"]), int(row["week"])


def _load_latest_predictions() -> tuple[list[dict[str, Any]], Optional[int], Optional[int]]:
    cached = predictions_cache.get("latest_predictions")
    if cached is not None:
        logger.info("Predictions cache hit (ttl=%ss)", settings.cache_ttl_seconds)
        return cached

    table = settings.predictions_table
    slate = _latest_slate(table)
    if slate is None:
        payload: tuple[list[dict[str, Any]], Optional[int], Optional[int]] = ([], None, None)
        predictions_cache.set("latest_predictions", payload)
        return payload

    season, week = slate
    rows = execute_query(
        f"""
        SELECT
            player_id, player_name, position, recent_team, opponent,
            season, week, projected_ppr, actual_ppr,
            implied_total, team_spread, team_win_prob, is_home,
            temp, wind, is_bad_weather, is_dome,
            fantasy_points_3wk_avg, depth_chart_rank,
            opp_def_ppg_allowed, prev_season_ppg,
            insight, insight_source
        FROM {table}
        WHERE season = ? AND week = ?
        ORDER BY projected_ppr DESC
        """,
        (season, week),
    )
    payload = (rows, season, week)
    predictions_cache.set("latest_predictions", payload)
    logger.info("Cached %s predictions for season=%s week=%s", len(rows), season, week)
    return payload


def _filter_predictions(
    rows: list[dict[str, Any]],
    position: Optional[str],
    team: Optional[str],
    min_projected_ppr: Optional[float],
) -> list[dict[str, Any]]:
    filtered = rows
    if position:
        filtered = [row for row in filtered if row.get("position") == position]
    if team:
        filtered = [row for row in filtered if row.get("recent_team") == team]
    if min_projected_ppr is not None:
        filtered = [
            row
            for row in filtered
            if row.get("projected_ppr") is not None
            and float(row["projected_ppr"]) >= min_projected_ppr
        ]
    return filtered


def _paginate(rows: list[dict[str, Any]], limit: int, offset: int) -> tuple[list[dict[str, Any]], int]:
    return rows[offset : offset + limit], len(rows)


# ---------------------------------------------------------------------------
# Root / health
# ---------------------------------------------------------------------------


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {
        "name": "Fantasy Football Engine API",
        "docs": "/docs",
        "health": "/health",
    }


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="API and Databricks connection health",
)
def health() -> HealthResponse:
    base = {
        "api": "ok",
        "catalog": settings.catalog,
        "schema": settings.schema,
        "player_weeks_reachable": False,
        "predictions_reachable": False,
    }
    if not settings.is_configured:
        return HealthResponse.model_validate(
            {
                **base,
                "status": "unhealthy",
                "databricks": "unconfigured",
                "detail": "Missing DATABRICKS_SERVER_HOSTNAME, DATABRICKS_HTTP_PATH, or DATABRICKS_ACCESS_TOKEN",
            }
        )

    try:
        ping()
        player_ok = True
        pred_ok = True
        try:
            execute_query(f"SELECT 1 AS ok FROM {settings.player_weeks_table} LIMIT 1")
        except QueryError:
            player_ok = False
        try:
            execute_query(f"SELECT 1 AS ok FROM {settings.predictions_table} LIMIT 1")
        except QueryError:
            pred_ok = False
        return HealthResponse.model_validate(
            {
                **base,
                "status": "healthy" if player_ok and pred_ok else "degraded",
                "databricks": "connected",
                "player_weeks_reachable": player_ok,
                "predictions_reachable": pred_ok,
            }
        )
    except DatabricksNotConfiguredError as exc:
        return HealthResponse.model_validate(
            {
                **base,
                "status": "unhealthy",
                "databricks": "unconfigured",
                "detail": str(exc),
            }
        )
    except QueryError as exc:
        logger.exception("Health check failed")
        return HealthResponse.model_validate(
            {
                **base,
                "status": "unhealthy",
                "databricks": "disconnected",
                "detail": str(exc),
            }
        )


# ---------------------------------------------------------------------------
# Players
# ---------------------------------------------------------------------------


@app.get(
    "/api/players",
    response_model=PlayerListResponse,
    tags=["Players"],
    summary="List players",
    description="Returns the latest appearance for each player, with optional position/team filters.",
)
def list_players(
    position: Optional[str] = Query(None, description="Filter by position (QB, RB, WR, TE)"),
    team: Optional[str] = Query(None, description="Filter by NFL team abbreviation (e.g. KC, BUF)"),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
) -> PlayerListResponse:
    limit, offset = _clamp_pagination(limit, offset)
    position = _normalize_position(position)
    team = _normalize_team(team)

    clauses: list[str] = ["rn = 1"]
    params: list[Any] = []
    if position:
        clauses.append("position = ?")
        params.append(position)
    if team:
        clauses.append("recent_team = ?")
        params.append(team)
    params.extend([limit, offset])

    rows = execute_query(
        f"""
        SELECT
            player_id,
            player_name,
            position,
            recent_team,
            season AS latest_season,
            week AS latest_week,
            opponent AS latest_opponent,
            fantasy_points_ppr AS latest_ppr,
            COUNT(*) OVER() AS total
        FROM (
            SELECT
                player_id,
                player_name,
                position,
                recent_team,
                season,
                week,
                opponent,
                fantasy_points_ppr,
                ROW_NUMBER() OVER (
                    PARTITION BY player_id
                    ORDER BY season DESC, week DESC
                ) AS rn
            FROM {settings.player_weeks_table}
        ) latest
        WHERE {" AND ".join(clauses)}
        ORDER BY player_name
        LIMIT ? OFFSET ?
        """,
        params,
    )
    items, total = _pop_total(rows)
    return PlayerListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=[PlayerSummary.model_validate(item) for item in items],
    )


@app.get(
    "/api/players/{player_id}",
    response_model=PlayerDetail,
    responses=ERROR_RESPONSES,
    tags=["Players"],
    summary="Get a player's latest week and career summary",
)
def get_player(player_id: str = Path(..., min_length=1)) -> PlayerDetail:
    latest = execute_query_one(
        f"""
        SELECT *
        FROM {settings.player_weeks_table}
        WHERE player_id = ?
        ORDER BY season DESC, week DESC
        LIMIT 1
        """,
        (player_id,),
    )
    if latest is None:
        raise HTTPException(status_code=404, detail=f"Player '{player_id}' not found")

    career_row = execute_query_one(
        f"""
        SELECT
            COUNT(*) AS games_played,
            MIN(season) AS first_season,
            MAX(season) AS last_season,
            AVG(fantasy_points_ppr) AS career_ppg,
            MAX(fantasy_points_ppr) AS career_high
        FROM {settings.player_weeks_table}
        WHERE player_id = ?
        """,
        (player_id,),
    ) or {}

    return PlayerDetail(
        player_id=latest.get("player_id") or player_id,
        player_name=latest.get("player_name") or player_id,
        position=latest.get("position"),
        recent_team=latest.get("recent_team"),
        career=PlayerCareerSummary.model_validate(career_row),
        latest_week=PlayerWeek.model_validate(latest),
    )


@app.get(
    "/api/players/{player_id}/history",
    response_model=PlayerHistoryResponse,
    responses=ERROR_RESPONSES,
    tags=["Players"],
    summary="Player historical weekly stats",
)
def get_player_history(
    player_id: str = Path(..., min_length=1),
    season: Optional[int] = Query(None, description="Limit history to a single season"),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
) -> PlayerHistoryResponse:
    limit, offset = _clamp_pagination(limit, offset)

    exists = execute_query_one(
        f"""
        SELECT 1 AS ok
        FROM {settings.player_weeks_table}
        WHERE player_id = ?
        LIMIT 1
        """,
        (player_id,),
    )
    if exists is None:
        raise HTTPException(status_code=404, detail=f"Player '{player_id}' not found")

    clauses = ["player_id = ?"]
    params: list[Any] = [player_id]
    if season is not None:
        clauses.append("season = ?")
        params.append(season)
    params.extend([limit, offset])

    rows = execute_query(
        f"""
        SELECT *, COUNT(*) OVER() AS total
        FROM {settings.player_weeks_table}
        WHERE {" AND ".join(clauses)}
        ORDER BY season DESC, week DESC
        LIMIT ? OFFSET ?
        """,
        params,
    )
    items, total = _pop_total(rows)
    return PlayerHistoryResponse(
        player_id=player_id,
        total=total,
        limit=limit,
        offset=offset,
        items=[PlayerWeek.model_validate(item) for item in items],
    )


# ---------------------------------------------------------------------------
# Predictions
# ---------------------------------------------------------------------------


@app.get(
    "/api/predictions",
    response_model=PredictionListResponse,
    tags=["Predictions"],
    summary="Predictions for the latest week",
    description=(
        "Returns model projections and AI insights for the most recent week in "
        "`fantasy_football.gold.predictions`. Results are cached in memory for one hour."
    ),
)
def list_predictions(
    position: Optional[str] = Query(None, description="Filter by position (QB, RB, WR, TE)"),
    team: Optional[str] = Query(None, description="Filter by NFL team abbreviation"),
    min_projected_ppr: Optional[float] = Query(
        None, alias="min_projected_ppr", description="Minimum projected PPR points"
    ),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
) -> PredictionListResponse:
    limit, offset = _clamp_pagination(limit, offset)
    rows, season, week = _load_latest_predictions()
    filtered = _filter_predictions(
        rows,
        position=_normalize_position(position),
        team=_normalize_team(team),
        min_projected_ppr=min_projected_ppr,
    )
    page, total = _paginate(filtered, limit, offset)
    return PredictionListResponse(
        total=total,
        limit=limit,
        offset=offset,
        season=season,
        week=week,
        items=[Prediction.model_validate(item) for item in page],
    )


@app.get(
    "/api/predictions/top/{n}",
    response_model=PredictionListResponse,
    tags=["Predictions"],
    summary="Top N projected players for the latest week",
)
def top_predictions(
    n: int = Path(..., ge=1, le=100, description="Number of top projected players to return"),
    position: Optional[str] = Query(None, description="Filter by position before ranking"),
) -> PredictionListResponse:
    rows, season, week = _load_latest_predictions()
    filtered = _filter_predictions(
        rows,
        position=_normalize_position(position),
        team=None,
        min_projected_ppr=None,
    )
    top_rows = filtered[:n]
    return PredictionListResponse(
        total=len(filtered),
        limit=n,
        offset=0,
        season=season,
        week=week,
        items=[Prediction.model_validate(item) for item in top_rows],
    )


@app.get(
    "/api/predictions/{player_id}",
    response_model=Prediction,
    responses=ERROR_RESPONSES,
    tags=["Predictions"],
    summary="Prediction and insight for a specific player",
)
def get_prediction(player_id: str = Path(..., min_length=1)) -> Prediction:
    rows, _season, _week = _load_latest_predictions()
    match = next((row for row in rows if row.get("player_id") == player_id), None)
    if match is None:
        # Fall back to a targeted SQL lookup in case the cache is for a different week
        # or the player appears in an older predictions row.
        row = execute_query_one(
            f"""
            SELECT
                player_id, player_name, position, recent_team, opponent,
                season, week, projected_ppr, actual_ppr,
                implied_total, team_spread, team_win_prob, is_home,
                temp, wind, is_bad_weather, is_dome,
                fantasy_points_3wk_avg, depth_chart_rank,
                opp_def_ppg_allowed, prev_season_ppg,
                insight, insight_source
            FROM {settings.predictions_table}
            WHERE player_id = ?
            ORDER BY season DESC, week DESC
            LIMIT 1
            """,
            (player_id,),
        )
        if row is None:
            raise HTTPException(
                status_code=404,
                detail=f"No prediction found for player '{player_id}'",
            )
        match = row
    return Prediction.model_validate(match)


# ---------------------------------------------------------------------------
# Weekly stats
# ---------------------------------------------------------------------------


@app.get(
    "/api/weeks/latest",
    response_model=WeekStatsResponse,
    tags=["Weeks"],
    summary="Most recent week in player_weeks",
)
def latest_week(
    position: Optional[str] = Query(None),
    team: Optional[str] = Query(None),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
) -> WeekStatsResponse:
    slate = _latest_slate(settings.player_weeks_table)
    if slate is None:
        return WeekStatsResponse(
            season=None,
            week=None,
            total=0,
            limit=limit,
            offset=offset,
            items=[],
        )
    season, week = slate
    return week_stats(season=season, week=week, position=position, team=team, limit=limit, offset=offset)


@app.get(
    "/api/weeks/{season}/{week}",
    response_model=WeekStatsResponse,
    tags=["Weeks"],
    summary="All player stats for a specific season and week",
)
def week_stats(
    season: int = Path(..., ge=1999, le=2100),
    week: int = Path(..., ge=1, le=22),
    position: Optional[str] = Query(None, description="Filter by position"),
    team: Optional[str] = Query(None, description="Filter by team abbreviation"),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
) -> WeekStatsResponse:
    limit, offset = _clamp_pagination(limit, offset)
    position = _normalize_position(position)
    team = _normalize_team(team)

    clauses = ["season = ?", "week = ?"]
    params: list[Any] = [season, week]
    if position:
        clauses.append("position = ?")
        params.append(position)
    if team:
        clauses.append("recent_team = ?")
        params.append(team)
    params.extend([limit, offset])

    rows = execute_query(
        f"""
        SELECT *, COUNT(*) OVER() AS total
        FROM {settings.player_weeks_table}
        WHERE {" AND ".join(clauses)}
        ORDER BY fantasy_points_ppr DESC
        LIMIT ? OFFSET ?
        """,
        params,
    )
    items, total = _pop_total(rows)
    return WeekStatsResponse(
        season=season,
        week=week,
        total=total,
        limit=limit,
        offset=offset,
        items=[PlayerWeek.model_validate(item) for item in items],
    )


# ---------------------------------------------------------------------------
# Teams
# ---------------------------------------------------------------------------


@app.get(
    "/api/teams/{team_abbr}",
    response_model=TeamResponse,
    tags=["Teams"],
    summary="Roster with latest projections",
    description=(
        "Returns the latest player-week for each player currently on the team, "
        "left-joined to the latest-week model projections and AI insights."
    ),
)
def team_stats(
    team_abbr: str = Path(..., min_length=2, max_length=4, description="NFL team abbreviation"),
) -> TeamResponse:
    team = _normalize_team(team_abbr)
    if team is None:
        return TeamResponse(team=team_abbr, players=[])

    pred_slate = _latest_slate(settings.predictions_table)
    pred_season, pred_week = pred_slate if pred_slate else (None, None)

    rows = execute_query(
        f"""
        WITH roster AS (
            SELECT
                player_id,
                player_name,
                position,
                recent_team,
                opponent,
                season,
                week,
                fantasy_points_ppr,
                depth_chart_rank
            FROM (
                SELECT
                    player_id,
                    player_name,
                    position,
                    recent_team,
                    opponent,
                    season,
                    week,
                    fantasy_points_ppr,
                    depth_chart_rank,
                    ROW_NUMBER() OVER (
                        PARTITION BY player_id
                        ORDER BY season DESC, week DESC
                    ) AS rn
                FROM {settings.player_weeks_table}
                WHERE recent_team = ?
            ) ranked
            WHERE rn = 1
        )
        SELECT
            r.player_id,
            r.player_name,
            r.position,
            r.recent_team,
            COALESCE(p.opponent, r.opponent) AS opponent,
            COALESCE(p.season, r.season) AS season,
            COALESCE(p.week, r.week) AS week,
            p.projected_ppr,
            p.actual_ppr,
            p.insight,
            p.insight_source,
            r.fantasy_points_ppr AS latest_ppr,
            COALESCE(p.depth_chart_rank, r.depth_chart_rank) AS depth_chart_rank
        FROM roster r
        LEFT JOIN {settings.predictions_table} p
            ON p.player_id = r.player_id
            {"AND p.season = ? AND p.week = ?" if pred_slate else ""}
        ORDER BY p.projected_ppr DESC NULLS LAST, r.player_name
        """,
        (team, pred_season, pred_week) if pred_slate else (team,),
    )
    return TeamResponse(
        team=team,
        season=pred_season,
        week=pred_week,
        players=[TeamPlayer.model_validate(row) for row in rows],
    )
