from unittest.mock import patch

from fastapi.testclient import TestClient

from main import (
    _clamp_pagination,
    _filter_predictions,
    _normalize_position,
    _normalize_team,
    app,
)

client = TestClient(app)


def test_clamp_pagination() -> None:
    assert _clamp_pagination(50, 0) == (50, 0)
    assert _clamp_pagination(9999, -3) == (500, 0)
    assert _clamp_pagination(0, 10) == (1, 10)


def test_normalize_filters() -> None:
    assert _normalize_position(" qb ") == "QB"
    assert _normalize_position("  ") is None
    assert _normalize_team("kc") == "KC"


def test_filter_predictions() -> None:
    rows = [
        {"player_id": "a", "position": "QB", "recent_team": "KC", "projected_ppr": 22.0},
        {"player_id": "b", "position": "RB", "recent_team": "KC", "projected_ppr": 14.0},
        {"player_id": "c", "position": "WR", "recent_team": "BUF", "projected_ppr": 18.0},
    ]
    kc_only = _filter_predictions(rows, position=None, team="KC", min_projected_ppr=None)
    assert [row["player_id"] for row in kc_only] == ["a", "b"]

    high_floor = _filter_predictions(rows, position=None, team=None, min_projected_ppr=18)
    assert [row["player_id"] for row in high_floor] == ["a", "c"]


def test_root_and_unconfigured_health() -> None:
    root = client.get("/")
    assert root.status_code == 200
    assert root.json()["health"] == "/health"

    health = client.get("/health")
    assert health.status_code == 200
    body = health.json()
    assert body["api"] == "ok"
    assert body["status"] == "unhealthy"
    assert body["databricks"] == "unconfigured"


def test_list_players_uses_query_results() -> None:
    fake_rows = [
        {
            "player_id": "00-0033873",
            "player_name": "Patrick Mahomes",
            "position": "QB",
            "recent_team": "KC",
            "latest_season": 2025,
            "latest_week": 17,
            "latest_opponent": "LV",
            "latest_ppr": 21.4,
            "total": 1,
        }
    ]
    with patch("main.execute_query", return_value=fake_rows):
        response = client.get("/api/players?position=qb&limit=10")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["player_name"] == "Patrick Mahomes"


def test_list_predictions_from_cache_payload() -> None:
    fake_pred = {
        "player_id": "00-0033873",
        "player_name": "Patrick Mahomes",
        "position": "QB",
        "recent_team": "KC",
        "opponent": "LV",
        "season": 2025,
        "week": 17,
        "projected_ppr": 18.5,
        "actual_ppr": 21.4,
        "implied_total": 24.5,
        "team_spread": -3.5,
        "team_win_prob": 0.64,
        "is_home": 1.0,
        "temp": 72.0,
        "wind": 5.0,
        "is_bad_weather": 0.0,
        "is_dome": 0.0,
        "fantasy_points_3wk_avg": 19.2,
        "depth_chart_rank": 1,
        "opp_def_ppg_allowed": 18.1,
        "prev_season_ppg": 20.0,
        "insight": "Mahomes has a solid floor.",
        "insight_source": "template",
    }
    with patch("main._load_latest_predictions", return_value=([fake_pred], 2025, 17)):
        response = client.get("/api/predictions/top/5")
    assert response.status_code == 200
    payload = response.json()
    assert payload["season"] == 2025
    assert payload["week"] == 17
    assert payload["items"][0]["projected_ppr"] == 18.5


def test_list_predictions_accepts_blank_swagger_query_params() -> None:
    fake_pred = {
        "player_id": "00-0033873",
        "player_name": "Patrick Mahomes",
        "position": "QB",
        "recent_team": "KC",
        "projected_ppr": 18.5,
    }
    with patch("main._load_latest_predictions", return_value=([fake_pred], 2025, 17)):
        response = client.get(
            "/api/predictions?position=&team=&min_projected_ppr=&limit=50&offset=0"
        )
    assert response.status_code == 200
    assert response.json()["items"][0]["player_name"] == "Patrick Mahomes"


def test_unknown_player_returns_404() -> None:
    with patch("main.execute_query_one", return_value=None):
        response = client.get("/api/players/00-missing")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
