"""Sanity checks against Unity Catalog Gold tables via the Databricks SQL Connector.

Used by `.github/workflows/gold-validate.yml`. Run locally from the repo root:

    cd api && python ../.github/scripts/validate_gold.py

Requires DATABRICKS_SERVER_HOSTNAME, DATABRICKS_HTTP_PATH, and
DATABRICKS_ACCESS_TOKEN (api/.env is loaded automatically).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[2] / "api"
sys.path.insert(0, str(API_DIR))

from config import get_settings  # noqa: E402
from database import execute_query, execute_query_one  # noqa: E402

PLAYER_WEEK_COLUMNS = [
    "player_id",
    "player_name",
    "season",
    "week",
    "position",
    "recent_team",
    "opponent",
    "fantasy_points_ppr",
    "implied_total",
    "team_spread",
    "fantasy_points_3wk_avg",
    "fantasy_points_5wk_avg",
    "prev_season_ppg",
    "depth_chart_rank",
    "opp_def_ppg_allowed",
    "wr1_wr2_healthy",
]

PREDICTION_COLUMNS = [
    "player_id",
    "player_name",
    "season",
    "week",
    "position",
    "projected_ppr",
    "insight",
    "insight_source",
]


class Check:
    def __init__(self, name: str, ok: bool, detail: str) -> None:
        self.name = name
        self.ok = ok
        self.detail = detail


def _scalar(row: dict | None, key: str, default=0):
    if not row:
        return default
    value = row.get(key)
    return default if value is None else value


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Gold Delta tables")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail when Databricks credentials are missing (scheduled runs)",
    )
    args = parser.parse_args()

    settings = get_settings()
    if not settings.is_configured:
        print(
            "SKIP: Databricks credentials are not configured. "
            "Set DATABRICKS_SERVER_HOSTNAME, DATABRICKS_HTTP_PATH, "
            "and DATABRICKS_ACCESS_TOKEN."
        )
        return 1 if args.strict else 0

    players = settings.player_weeks_table
    preds = settings.predictions_table
    checks: list[Check] = []

    count_row = execute_query_one(f"SELECT COUNT(*) AS n FROM {players}")
    n_players = int(_scalar(count_row, "n"))
    checks.append(
        Check(
            "player_weeks nonempty",
            n_players > 0,
            f"{n_players} rows in {players}",
        )
    )

    dup_row = execute_query_one(
        f"""
        SELECT COUNT(*) AS n FROM (
            SELECT player_id, season, week
            FROM {players}
            GROUP BY player_id, season, week
            HAVING COUNT(*) > 1
        ) dups
        """
    )
    n_dups = int(_scalar(dup_row, "n"))
    checks.append(
        Check(
            "player_weeks unique (player_id, season, week)",
            n_dups == 0,
            f"{n_dups} duplicate keys",
        )
    )

    pos_row = execute_query_one(
        f"""
        SELECT COUNT(*) AS n
        FROM {players}
        WHERE position NOT IN ('QB', 'RB', 'WR', 'TE') OR position IS NULL
        """
    )
    n_bad_pos = int(_scalar(pos_row, "n"))
    checks.append(
        Check(
            "positions are QB/RB/WR/TE",
            n_bad_pos == 0,
            f"{n_bad_pos} rows with invalid position",
        )
    )

    backup_row = execute_query_one(
        f"""
        SELECT COUNT(*) AS n
        FROM {players}
        WHERE position IN ('QB', 'TE') AND depth_chart_rank != 1
        """
    )
    n_backups = int(_scalar(backup_row, "n"))
    checks.append(
        Check(
            "QB/TE starter filter (depth_chart_rank = 1)",
            n_backups == 0,
            f"{n_backups} backup QB/TE rows",
        )
    )

    try:
        cols = ", ".join(PLAYER_WEEK_COLUMNS)
        execute_query(f"SELECT {cols} FROM {players} LIMIT 1")
        checks.append(Check("player_weeks required columns", True, "ok"))
    except Exception as exc:  # noqa: BLE001
        checks.append(Check("player_weeks required columns", False, str(exc)))

    pred_count = execute_query_one(f"SELECT COUNT(*) AS n FROM {preds}")
    n_preds = int(_scalar(pred_count, "n"))
    checks.append(
        Check(
            "predictions nonempty",
            n_preds > 0,
            f"{n_preds} rows in {preds}",
        )
    )

    pred_dups = execute_query_one(
        f"""
        SELECT COUNT(*) AS n FROM (
            SELECT player_id, season, week
            FROM {preds}
            GROUP BY player_id, season, week
            HAVING COUNT(*) > 1
        ) dups
        """
    )
    n_pred_dups = int(_scalar(pred_dups, "n"))
    checks.append(
        Check(
            "predictions unique (player_id, season, week)",
            n_pred_dups == 0,
            f"{n_pred_dups} duplicate keys",
        )
    )

    try:
        cols = ", ".join(PREDICTION_COLUMNS)
        execute_query(f"SELECT {cols} FROM {preds} LIMIT 1")
        checks.append(Check("predictions required columns", True, "ok"))
    except Exception as exc:  # noqa: BLE001
        checks.append(Check("predictions required columns", False, str(exc)))

    latest = execute_query_one(
        f"""
        SELECT season, week, COUNT(*) AS n
        FROM {preds}
        GROUP BY season, week
        ORDER BY season DESC, week DESC
        LIMIT 1
        """
    )
    if latest:
        checks.append(
            Check(
                "latest predictions partition",
                True,
                f"season={latest.get('season')} week={latest.get('week')} "
                f"rows={latest.get('n')}",
            )
        )
    else:
        checks.append(Check("latest predictions partition", False, "no partitions"))

    failed = 0
    for check in checks:
        status = "PASS" if check.ok else "FAIL"
        if not check.ok:
            failed += 1
        print(f"{status:4}  {check.name} — {check.detail}")

    print(f"\n{len(checks) - failed}/{len(checks)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
