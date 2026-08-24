"""Databricks connection and API settings loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

_API_DIR = Path(__file__).resolve().parent
load_dotenv(_API_DIR / ".env")
load_dotenv(_API_DIR.parent / ".env")


def _split_origins(raw: str) -> list[str]:
    origins = [item.strip() for item in raw.split(",") if item.strip()]
    return origins or ["*"]


@dataclass(frozen=True)
class Settings:
    server_hostname: str
    http_path: str
    access_token: str
    catalog: str = "fantasy_football"
    schema: str = "gold"
    cors_origins: list[str] = field(default_factory=lambda: ["*"])
    cache_ttl_seconds: int = 3600

    @property
    def player_weeks_table(self) -> str:
        return f"{self.catalog}.{self.schema}.player_weeks"

    @property
    def predictions_table(self) -> str:
        return f"{self.catalog}.{self.schema}.predictions"

    @property
    def is_configured(self) -> bool:
        return all(
            [
                self.server_hostname,
                self.http_path,
                self.access_token,
            ]
        )


@lru_cache
def get_settings() -> Settings:
    return Settings(
        server_hostname=os.getenv("DATABRICKS_SERVER_HOSTNAME", "").strip(),
        http_path=os.getenv("DATABRICKS_HTTP_PATH", "").strip(),
        access_token=os.getenv("DATABRICKS_ACCESS_TOKEN", "").strip(),
        catalog=os.getenv("DATABRICKS_CATALOG", "fantasy_football").strip(),
        schema=os.getenv("DATABRICKS_SCHEMA", "gold").strip(),
        cors_origins=_split_origins(os.getenv("CORS_ORIGINS", "*")),
        cache_ttl_seconds=int(os.getenv("CACHE_TTL_SECONDS", "3600")),
    )
