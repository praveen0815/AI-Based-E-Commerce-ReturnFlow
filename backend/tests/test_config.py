"""Configuration loading and validation."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import ENV_FILE, Settings

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _settings(monkeypatch: pytest.MonkeyPatch, **env: str) -> Settings:
    for name in (
        "APP_ENV",
        "DEBUG",
        "LOG_LEVEL",
        "API_V1_PREFIX",
        "CORS_ORIGINS",
        "DATABASE_URL",
        "REDIS_URL",
    ):
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    return Settings(_env_file=None)


def test_defaults_use_placeholder_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(monkeypatch)
    assert settings.app_name == "ReturnFlow"
    assert settings.api_v1_prefix == "/api/v1"
    assert settings.database_url.startswith("postgresql+asyncpg://")
    assert "change-me" in settings.database_url
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.cors_origin_list[0] == "http://localhost:5173"
    assert settings.is_production is False


def test_cors_origins_are_split_and_trimmed(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(
        monkeypatch,
        CORS_ORIGINS=" http://localhost:5173, http://localhost:4173 ",
    )
    assert settings.cors_origin_list == [
        "http://localhost:5173",
        "http://localhost:4173",
    ]


def test_api_prefix_strips_a_trailing_slash(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(monkeypatch, API_V1_PREFIX="/api/v1/")
    assert settings.api_v1_prefix == "/api/v1"


@pytest.mark.parametrize(
    ("env", "match"),
    [
        ({"LOG_LEVEL": "verbose"}, "log_level"),
        ({"API_V1_PREFIX": "api/v1"}, "api_v1_prefix"),
        ({"CORS_ORIGINS": "*"}, "CORS_ORIGINS"),
        ({"CORS_ORIGINS": " , "}, "CORS_ORIGINS"),
        ({"DATABASE_URL": "postgresql://returnflow:secret@localhost/returnflow"}, "DATABASE_URL"),
        ({"REDIS_URL": "http://localhost:6379/0"}, "REDIS_URL"),
        ({"APP_ENV": "production", "DEBUG": "true"}, "DEBUG"),
        ({"APP_ENV": "production", "JWT_SECRET": "short"}, "JWT_SECRET"),
        (
            {"APP_ENV": "production", "JWT_SECRET": "change-me-change-me-change-me-xxxx"},
            "JWT_SECRET",
        ),
    ],
)
def test_invalid_environment_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    env: dict[str, str],
    match: str,
) -> None:
    with pytest.raises(ValidationError, match=match):
        _settings(monkeypatch, **env)


def test_env_file_constant_points_at_the_repo_root() -> None:
    assert ENV_FILE.name == ".env"
    assert ENV_FILE.parent == BACKEND_DIR.parent


def test_alembic_offline_sql_compiles() -> None:
    alembic_bin = Path(sys.executable).with_name("alembic.exe")
    result = subprocess.run(
        [str(alembic_bin), "upgrade", "head", "--sql"],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "0001_baseline" in result.stdout
    assert "0002_auth" in result.stdout
    assert "0003_commerce" in result.stdout
    assert "CREATE TABLE users" in result.stdout
    assert "store_memberships" in result.stdout
    assert "audit_logs" in result.stdout
