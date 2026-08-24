from config import Settings, get_settings


def test_is_configured_requires_all_three_fields() -> None:
    missing_token = Settings(
        server_hostname="example.cloud.databricks.com",
        http_path="/sql/1.0/warehouses/abc",
        access_token="",
    )
    assert missing_token.is_configured is False

    complete = Settings(
        server_hostname="example.cloud.databricks.com",
        http_path="/sql/1.0/warehouses/abc",
        access_token="dapi123",
    )
    assert complete.is_configured is True


def test_table_names_use_catalog_and_schema() -> None:
    settings = Settings(
        server_hostname="h",
        http_path="p",
        access_token="t",
        catalog="fantasy_football",
        schema="gold",
    )
    assert settings.player_weeks_table == "fantasy_football.gold.player_weeks"
    assert settings.predictions_table == "fantasy_football.gold.predictions"


def test_empty_catalog_env_falls_back_to_default(monkeypatch) -> None:
    monkeypatch.setenv("DATABRICKS_CATALOG", "")
    monkeypatch.setenv("DATABRICKS_SCHEMA", "")
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.catalog == "fantasy_football"
    assert settings.schema == "gold"


def test_get_settings_reads_env(monkeypatch) -> None:
    monkeypatch.setenv("DATABRICKS_SERVER_HOSTNAME", "host.databricks.com")
    monkeypatch.setenv("DATABRICKS_HTTP_PATH", "/sql/1.0/warehouses/xyz")
    monkeypatch.setenv("DATABRICKS_ACCESS_TOKEN", "dapi-test")
    monkeypatch.setenv("DATABRICKS_CATALOG", "other_catalog")
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.server_hostname == "host.databricks.com"
    assert settings.catalog == "other_catalog"
    assert settings.is_configured is True
