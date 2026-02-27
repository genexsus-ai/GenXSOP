#!/usr/bin/env bash
set -euo pipefail

# CI migration governance gate.
# Intended usage in CI pipelines before deploy.

echo "[1/4] Checking Alembic revision chain integrity"
python3 scripts/check_migration_chain.py

echo "[2/4] Verifying migration/preflight scripts compile"
python3 -m compileall alembic/versions scripts/check_migration_chain.py scripts/db_preflight.py

echo "[3/4] Running DB preflight in CI mode (non-production defaults)"
python3 scripts/db_preflight.py

echo "[4/4] Running lightweight unit safety tests"
python3 -m pytest tests/unit/test_exceptions.py tests/unit/test_ml_strategies.py -q

echo "CI migration governance gate passed"
