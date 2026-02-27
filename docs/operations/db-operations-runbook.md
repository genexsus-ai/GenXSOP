# DB Operations Runbook (P2)

This runbook defines baseline enterprise DB operations for GenXSOP.

## 1) Migration governance gate (CI)

Use:

```bash
cd backend
bash scripts/ci_migration_gate.sh
```

The gate verifies:

- Alembic revision/down-revision chain integrity
- Compilation of migration and preflight scripts
- DB preflight safety checks
- Lightweight unit safety tests

## 2) Backup + restore verification

Use:

```bash
cd backend
SOURCE_DATABASE_URL='postgresql://user:pass@host:5432/genxsop' \
RESTORE_DATABASE_URL='postgresql://user:pass@host:5432/genxsop_restore_check' \
bash scripts/backup_restore_runbook.sh
```

Note: scripts assume `python3` is available in PATH.

Expected outcome:

- Backup artifact generated in `./backups`
- Restore target is recreated
- Restore completes without errors
- Post-restore smoke query succeeds

## 3) Suggested cadence

- Migration governance gate: on every PR and deploy pipeline
- Backup + restore drill: weekly for non-prod, monthly for prod
- Capture evidence logs/artifacts in release records

## 4) Core DB SLO starter metrics

Track these metrics from PostgreSQL and app telemetry:

- Query latency p95 (read/write separately)
- DB error rate
- Connection pool utilization / saturation
- Lock wait time
- Deadlock count
- Backup success rate
- Restore drill success rate + time-to-restore

Target examples:

- Non-ML API DB query p95: < 150ms
- Backup success: 100%
- Restore drill success: 100% within defined RTO
