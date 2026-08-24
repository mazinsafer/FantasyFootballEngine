"""Pydantic request/response models for the Fantasy Football API."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class HealthResponse(ORMModel):
    status: str = Field(..., description="healthy or unhealthy")
    api: str = Field(default="ok", description="Process liveness")
    databricks: str = Field(..., description="connected, disconnected, or unconfigured")
    catalog: str
    schema_name: str = Field(..., alias="schema")
    player_weeks_reachable: bool = False
    predictions_reachable: bool = False
    detail: Optional[str] = None

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class PlayerSummary(ORMModel):
    player_id: str
    player_name: str
    position: Optional[str] = None
    recent_team: Optional[str] = None
    latest_season: Optional[int] = None
    latest_week: Optional[int] = None
    latest_opponent: Optional[str] = None
    latest_ppr: Optional[float] = None


class PlayerCareerSummary(ORMModel):
    games_played: int = 0
    first_season: Optional[int] = None
    last_season: Optional[int] = None
    career_ppg: Optional[float] = None
    career_high: Optional[float] = None


class PlayerWeek(ORMModel):
    """One row from fantasy_football.gold.player_weeks (72 columns)."""

    player_id: Optional[str] = None
    player_name: Optional[str] = None
    position: Optional[str] = None
    recent_team: Optional[str] = None
    season: Optional[int] = None
    week: Optional[int] = None
    opponent: Optional[str] = None
    gameday: Optional[datetime] = None
    starting_qb_id: Optional[str] = None

    pass_attempts: Optional[float] = None
    completions: Optional[float] = None
    passing_yards: Optional[float] = None
    passing_tds: Optional[float] = None
    interceptions: Optional[float] = None
    rush_attempts: Optional[float] = None
    rushing_yards: Optional[float] = None
    rushing_tds: Optional[float] = None
    targets: Optional[float] = None
    receptions: Optional[float] = None
    receiving_yards: Optional[float] = None
    receiving_tds: Optional[float] = None
    fantasy_points_ppr: Optional[float] = None

    implied_total: Optional[float] = None
    team_spread: Optional[float] = None
    team_win_prob: Optional[float] = None
    is_home: Optional[float] = None
    temp: Optional[float] = None
    wind: Optional[float] = None
    is_bad_weather: Optional[float] = None
    is_dome: Optional[float] = None
    rest_advantage: Optional[float] = None

    opportunity_share: Optional[float] = None
    target_share: Optional[float] = None
    air_yards_share: Optional[float] = None
    wopr: Optional[float] = None
    snap_share: Optional[float] = None
    player_opportunities: Optional[float] = None
    team_total_opportunities: Optional[float] = None
    team_pass_attempts: Optional[float] = None
    player_air_yards: Optional[float] = None
    team_air_yards: Optional[float] = None

    fantasy_points_3wk_avg: Optional[float] = None
    fantasy_points_5wk_avg: Optional[float] = None
    prev_season_ppg: Optional[float] = None
    prev_season_games: Optional[float] = None

    qb_pass_attempts_3wk_avg: Optional[float] = None
    qb_pass_attempts_5wk_avg: Optional[float] = None
    qb_rushing_yards_3wk_avg: Optional[float] = None
    qb_rushing_yards_5wk_avg: Optional[float] = None
    team_sack_rate_allowed: Optional[float] = None
    opp_def_sack_rate: Optional[float] = None
    starting_qb_aya: Optional[float] = None

    rb_opportunity_share_3wk_avg: Optional[float] = None
    rb_opportunity_share_5wk_avg: Optional[float] = None
    hvt_carries: Optional[float] = None
    hvt_targets: Optional[float] = None
    total_hvts: Optional[float] = None
    rb_hvts_3wk_avg: Optional[float] = None
    rb_hvts_5wk_avg: Optional[float] = None
    rb_snap_share_3wk_avg: Optional[float] = None
    rb_snap_share_5wk_avg: Optional[float] = None

    wr_te_target_share_3wk_avg: Optional[float] = None
    wr_te_target_share_5wk_avg: Optional[float] = None
    wr_te_air_yards_share_3wk_avg: Optional[float] = None
    wr_te_air_yards_share_5wk_avg: Optional[float] = None
    wr_te_wopr_3wk_avg: Optional[float] = None
    wr_te_wopr_5wk_avg: Optional[float] = None
    wr1_wr2_healthy: Optional[int] = None

    opp_def_ppg_allowed: Optional[float] = None
    opp_def_ypc_allowed: Optional[float] = None
    opp_def_ypp_allowed: Optional[float] = None
    depth_chart_rank: Optional[int] = None


class PlayerDetail(ORMModel):
    player_id: str
    player_name: str
    position: Optional[str] = None
    recent_team: Optional[str] = None
    career: PlayerCareerSummary
    latest_week: Optional[PlayerWeek] = None


class Prediction(ORMModel):
    """One row from fantasy_football.gold.predictions."""

    player_id: str
    player_name: str
    position: Optional[str] = None
    recent_team: Optional[str] = None
    opponent: Optional[str] = None
    season: Optional[int] = None
    week: Optional[int] = None
    projected_ppr: Optional[float] = None
    actual_ppr: Optional[float] = None
    implied_total: Optional[float] = None
    team_spread: Optional[float] = None
    team_win_prob: Optional[float] = None
    is_home: Optional[float] = None
    temp: Optional[float] = None
    wind: Optional[float] = None
    is_bad_weather: Optional[float] = None
    is_dome: Optional[float] = None
    fantasy_points_3wk_avg: Optional[float] = None
    depth_chart_rank: Optional[int] = None
    opp_def_ppg_allowed: Optional[float] = None
    prev_season_ppg: Optional[float] = None
    insight: Optional[str] = None
    insight_source: Optional[str] = None


class TeamPlayer(ORMModel):
    player_id: str
    player_name: str
    position: Optional[str] = None
    recent_team: Optional[str] = None
    opponent: Optional[str] = None
    season: Optional[int] = None
    week: Optional[int] = None
    projected_ppr: Optional[float] = None
    actual_ppr: Optional[float] = None
    insight: Optional[str] = None
    insight_source: Optional[str] = None
    latest_ppr: Optional[float] = None
    depth_chart_rank: Optional[int] = None


class TeamResponse(ORMModel):
    team: str
    season: Optional[int] = None
    week: Optional[int] = None
    players: list[TeamPlayer] = Field(default_factory=list)


class PlayerListResponse(ORMModel):
    total: int
    limit: int
    offset: int
    items: list[PlayerSummary]


class PlayerHistoryResponse(ORMModel):
    player_id: str
    total: int
    limit: int
    offset: int
    items: list[PlayerWeek]


class PredictionListResponse(ORMModel):
    total: int
    limit: int
    offset: int
    season: Optional[int] = None
    week: Optional[int] = None
    items: list[Prediction]


class WeekStatsResponse(ORMModel):
    season: Optional[int] = None
    week: Optional[int] = None
    total: int
    limit: int
    offset: int
    items: list[PlayerWeek]


class ErrorResponse(ORMModel):
    detail: str
