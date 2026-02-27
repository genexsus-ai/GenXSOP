"""Static migration governance checks for Alembic revision files.

Usage:
    python scripts/check_migration_chain.py

Checks:
- every revision id is unique
- every down_revision exists (except root)
- there is exactly one head revision
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


REVISION_RE = re.compile(r'^revision\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)
DOWN_RE = re.compile(r'^down_revision\s*=\s*(.+)$', re.MULTILINE)


def _extract_scalar(raw: str) -> str | None:
    raw = raw.strip()
    if raw in {"None", ""}:
        return None
    if raw.startswith(("'", '"')) and raw.endswith(("'", '"')):
        return raw[1:-1]
    return None


def main() -> int:
    versions_dir = Path(__file__).resolve().parents[1] / "alembic" / "versions"
    files = sorted(versions_dir.glob("*.py"))

    revisions: dict[str, Path] = {}
    down_map: dict[str, str | None] = {}
    errors: list[str] = []

    for file in files:
        text = file.read_text(encoding="utf-8")
        rev_m = REVISION_RE.search(text)
        down_m = DOWN_RE.search(text)

        if not rev_m:
            errors.append(f"{file.name}: missing revision")
            continue

        rev = rev_m.group(1)
        if rev in revisions:
            errors.append(f"Duplicate revision id {rev} in {file.name} and {revisions[rev].name}")
        revisions[rev] = file

        down = _extract_scalar(down_m.group(1)) if down_m else None
        down_map[rev] = down

    for rev, down in down_map.items():
        if down is not None and down not in revisions:
            errors.append(f"Revision {rev} references missing down_revision {down}")

    referenced = {d for d in down_map.values() if d is not None}
    heads = [r for r in revisions if r not in referenced]
    if len(heads) != 1:
        errors.append(f"Expected exactly one head revision, found {len(heads)} ({heads})")

    print("Migration chain check")
    print(f"- files: {len(files)}")
    print(f"- revisions: {len(revisions)}")

    if errors:
        for err in errors:
            print(f"[FAIL] {err}")
        return 1

    print(f"[PASS] single head: {heads[0]}")
    print("[PASS] revision/down_revision integrity checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
