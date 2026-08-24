from datetime import date, datetime
from decimal import Decimal

from database import TTLCache, convert_value


def test_ttl_cache_expires(monkeypatch) -> None:
    cache = TTLCache(ttl_seconds=10)
    now = 1_000.0
    monkeypatch.setattr("database.time.time", lambda: now)
    cache.set("latest_predictions", ["row"])
    assert cache.get("latest_predictions") == ["row"]

    monkeypatch.setattr("database.time.time", lambda: now + 11)
    assert cache.get("latest_predictions") is None


def test_ttl_cache_clear() -> None:
    cache = TTLCache(ttl_seconds=60)
    cache.set("k", 1)
    cache.clear()
    assert cache.get("k") is None


def test_convert_decimal_int_columns() -> None:
    assert convert_value("season", Decimal("2025")) == 2025
    assert convert_value("week", Decimal("17")) == 17
    assert convert_value("depth_chart_rank", Decimal("1")) == 1


def test_convert_decimal_float_columns() -> None:
    assert convert_value("projected_ppr", Decimal("18.5")) == 18.5


def test_convert_nan_to_none() -> None:
    assert convert_value("fantasy_points_ppr", float("nan")) is None
    assert convert_value("insight", None) is None


def test_convert_datetime_passthrough() -> None:
    stamp = datetime(2025, 9, 7, 13, 0, 0)
    assert convert_value("gameday", stamp) is stamp
    day = date(2025, 9, 7)
    assert convert_value("gameday", day) is day
