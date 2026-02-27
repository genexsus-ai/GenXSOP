"""Database production preflight checks.

Usage:
    python scripts/db_preflight.py

Checks key enterprise safety requirements before deployment.
Exits non-zero when any required control fails.
"""

from __future__ import annotations

import os
import sys


DEFAULT_SECRET = "genxsop-super-secret-key-change-in-production"


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def run() -> int:
    environment = os.getenv("ENVIRONMENT", "development").strip().lower()
    database_url = os.getenv("DATABASE_URL", "sqlite:///./genxsop.db")
    secret_key = os.getenv("SECRET_KEY", DEFAULT_SECRET)
    auto_create_tables = _bool_env("AUTO_CREATE_TABLES", True)

    checks: list[tuple[str, bool, str]] = []

    checks.append((
        "ENVIRONMENT is explicitly set",
        bool(environment),
        f"ENVIRONMENT={environment or '<empty>'}",
    ))

    if environment in {"production", "prod"}:
        checks.extend(
            [
                (
                    "DATABASE_URL is not SQLite",
                    "sqlite" not in database_url.lower(),
                    f"DATABASE_URL={database_url}",
                ),
                (
                    "SECRET_KEY is not the default value",
                    secret_key != DEFAULT_SECRET,
                    "SECRET_KEY is custom" if secret_key != DEFAULT_SECRET else "SECRET_KEY is default",
                ),
                (
                    "AUTO_CREATE_TABLES is disabled",
                    not auto_create_tables,
                    f"AUTO_CREATE_TABLES={auto_create_tables}",
                ),
            ]
        )

    has_failures = False
    print("GenXSOP DB Preflight")
    print(f"- environment: {environment}")
    for title, ok, detail in checks:
        marker = "PASS" if ok else "FAIL"
        print(f"[{marker}] {title} ({detail})")
        if not ok:
            has_failures = True

    if has_failures:
        print("\nPreflight failed. Resolve failed checks before deployment.")
        return 1

    print("\nPreflight passed.")
    return 0


if __name__ == "__main__":
    sys.exit(run())
