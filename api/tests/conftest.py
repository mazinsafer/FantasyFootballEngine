"""Ensure api/.env cannot leak real Databricks credentials into tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ["DATABRICKS_SERVER_HOSTNAME"] = ""
os.environ["DATABRICKS_HTTP_PATH"] = ""
os.environ["DATABRICKS_ACCESS_TOKEN"] = ""

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from config import get_settings  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
