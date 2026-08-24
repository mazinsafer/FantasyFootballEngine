"""Databricks SQL connection manager, query helpers, and prediction cache."""

from __future__ import annotations

import logging
import math
import threading
import time
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterator, Optional, Sequence

from databricks import sql

from config import Settings, get_settings

logger = logging.getLogger("fantasy_api.db")

INT_COLUMNS = {
    "season",
    "week",
    "depth_chart_rank",
    "wr1_wr2_healthy",
    "games_played",
    "first_season",
    "last_season",
    "total",
}


class DatabricksNotConfiguredError(RuntimeError):
    """Raised when Databricks credentials are missing."""


class QueryError(RuntimeError):
    """Raised when a Databricks SQL query fails."""


class TTLCache:
    """Thread-safe in-memory cache with a uniform TTL."""

    def __init__(self, ttl_seconds: int = 3600) -> None:
        self.ttl_seconds = ttl_seconds
        self._store: dict[str, tuple[Any, float]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        now = time.time()
        with self._lock:
            item = self._store.get(key)
            if item is None:
                return None
            value, expires_at = item
            if now >= expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._store[key] = (value, time.time() + self.ttl_seconds)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


predictions_cache = TTLCache(ttl_seconds=get_settings().cache_ttl_seconds)


def convert_value(column: str, value: Any) -> Any:
    """Normalize Databricks values so they are JSON / Pydantic friendly."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, Decimal):
        if column in INT_COLUMNS:
            return int(value)
        return float(value)
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if column in INT_COLUMNS:
        try:
            return int(value)
        except (TypeError, ValueError):
            return value
    if isinstance(value, (int, float, str, bool)):
        return value
    # numpy / pandas scalars if the connector ever surfaces them
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return convert_value(column, item())
        except Exception:  # noqa: BLE001
            return str(value)
    return value


def convert_row(columns: Sequence[str], row: Sequence[Any]) -> dict[str, Any]:
    return {
        column: convert_value(column, value)
        for column, value in zip(columns, row)
    }


@contextmanager
def get_connection(settings: Optional[Settings] = None) -> Iterator[Any]:
    """Open a Databricks SQL connection and always close it."""
    settings = settings or get_settings()
    if not settings.is_configured:
        raise DatabricksNotConfiguredError(
            "Databricks credentials are not configured. "
            "Set DATABRICKS_SERVER_HOSTNAME, DATABRICKS_HTTP_PATH, "
            "and DATABRICKS_ACCESS_TOKEN."
        )

    connection = sql.connect(
        server_hostname=settings.server_hostname,
        http_path=settings.http_path,
        access_token=settings.access_token,
    )
    try:
        yield connection
    finally:
        connection.close()


@contextmanager
def get_cursor(settings: Optional[Settings] = None) -> Iterator[Any]:
    with get_connection(settings) as connection:
        cursor = connection.cursor()
        try:
            yield cursor
        finally:
            cursor.close()


def execute_query(
    query: str,
    params: Optional[Sequence[Any]] = None,
    settings: Optional[Settings] = None,
) -> list[dict[str, Any]]:
    """Run a parameterized query and return a list of dict rows."""
    params = tuple(params or ())
    compact_sql = " ".join(query.split())
    logger.info("SQL: %s | params=%s", compact_sql, params)

    try:
        with get_cursor(settings) as cursor:
            cursor.execute(query, params)
            if cursor.description is None:
                return []
            columns = [col[0] for col in cursor.description]
            # Connector 3.0.0's fetchall() converts Arrow → pandas → numpy and
            # crashes on modern pandas ("int() argument ... not 'NoneType'").
            if hasattr(cursor, "fetchall_arrow"):
                table = cursor.fetchall_arrow()
                return [
                    {
                        column: convert_value(column, value)
                        for column, value in record.items()
                    }
                    for record in table.to_pylist()
                ]
            return [convert_row(columns, row) for row in cursor.fetchall()]
    except DatabricksNotConfiguredError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Databricks query failed")
        raise QueryError(str(exc)) from exc


def execute_query_one(
    query: str,
    params: Optional[Sequence[Any]] = None,
    settings: Optional[Settings] = None,
) -> dict[str, Any] | None:
    rows = execute_query(query, params, settings)
    return rows[0] if rows else None


def ping() -> None:
    execute_query("SELECT 1 AS ok")
