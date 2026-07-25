"""
validate_dataset.py — Pre-benchmark ground-truth validation.

Run this BEFORE every benchmark execution to catch bad ground-truth data
early rather than producing silently wrong metrics.

Usage
-----
  python datasets/validate_dataset.py

Exit code 0 = all validations passed.
Exit code 1 = one or more errors found (do not run benchmark).

Checks performed
----------------
(a) Every entry in every ground-truth file parses against the required schema.
(b) No duplicate route_ids within a single file.
(c) Every ground-truth file's stem (e.g. "juice_shop" from juice_shop.json)
    has a matching "application_name" entry in app_registry.json.
(d) Every route_id is non-empty and contains at least two underscores
    (consistent with the f"{method}_{path}_{line}" pattern that Phase 1
    currently produces — this is a lint warning, not a hard error, so future
    format changes don't break validation).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_GROUND_TRUTH_DIR = _PROJECT_ROOT / "datasets" / "ground_truth"
_REGISTRY_FILE = _PROJECT_ROOT / "datasets" / "app_registry.json"

# Minimum fields required in each ground-truth entry (Phase 4 schema).
_REQUIRED_FIELDS: frozenset[str] = frozenset(
    {"route_id", "actually_vulnerable", "source"}
)

# Soft pattern for route_id — warns but does not fail.
# Matches strings like "POST_/api/orders/1_88" or "DELETE_/users/{id}_42"
_ROUTE_ID_PATTERN = re.compile(r"^[A-Z]+_.+_\d+$")


# ── Validation logic ───────────────────────────────────────────────────────

def validate_all_ground_truth(
    ground_truth_dir: str | Path | None = None,
    registry_file: str | Path | None = None,
) -> dict[str, Any]:
    """
    Validate every ground-truth file in *ground_truth_dir*.

    Returns
    -------
    dict with keys:
        "total_entries"  – total route entries checked
        "errors"         – list of error dicts (file, entry_index, message)
        "warnings"       – list of warning dicts
        "passed"         – bool (True if no errors)
    """
    gt_dir = Path(ground_truth_dir or _GROUND_TRUTH_DIR)
    reg_file = Path(registry_file or _REGISTRY_FILE)

    errors: list[dict] = []
    warnings: list[dict] = []
    total_entries = 0

    # Load registry.
    registered_apps: set[str] = set()
    if reg_file.exists():
        try:
            reg_data = json.loads(reg_file.read_text(encoding="utf-8"))
            registered_apps = {
                e["application_name"]
                for e in reg_data
                if isinstance(e, dict) and "application_name" in e
                and not e.get("_comment")
                and e["application_name"] not in ("SCHEMA_PLACEHOLDER",)
            }
        except Exception as exc:
            errors.append({
                "file": str(reg_file.name),
                "entry_index": None,
                "message": f"Could not load app_registry.json: {exc}",
            })
    else:
        errors.append({
            "file": "app_registry.json",
            "entry_index": None,
            "message": "app_registry.json not found — run from project root.",
        })

    if not gt_dir.exists():
        errors.append({
            "file": str(gt_dir),
            "entry_index": None,
            "message": "datasets/ground_truth/ directory not found.",
        })
        return {
            "total_entries": 0,
            "errors": errors,
            "warnings": warnings,
            "passed": False,
        }

    gt_files = sorted(gt_dir.glob("*.json"))
    skipped_filenames = {"EXAMPLE.json"}

    for gt_file in gt_files:
        if gt_file.name in skipped_filenames:
            continue

        # (c) Check registry membership.
        app_name = gt_file.stem
        if app_name not in registered_apps:
            errors.append({
                "file": gt_file.name,
                "entry_index": None,
                "message": (
                    f"Application '{app_name}' (from filename) is not in "
                    f"app_registry.json.  Add it before running the benchmark."
                ),
            })

        # Parse file.
        try:
            raw = json.loads(gt_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append({
                "file": gt_file.name,
                "entry_index": None,
                "message": f"JSON parse error: {exc}",
            })
            continue

        if not isinstance(raw, list):
            errors.append({
                "file": gt_file.name,
                "entry_index": None,
                "message": f"Expected a JSON array, got {type(raw).__name__}.",
            })
            continue

        seen_ids: dict[str, int] = {}

        for i, entry in enumerate(raw):
            total_entries += 1

            # (a) Schema check.
            if not isinstance(entry, dict):
                errors.append({
                    "file": gt_file.name,
                    "entry_index": i,
                    "message": f"Entry must be a dict, got {type(entry).__name__}.",
                })
                continue

            missing = _REQUIRED_FIELDS - entry.keys()
            if missing:
                errors.append({
                    "file": gt_file.name,
                    "entry_index": i,
                    "message": f"Missing required fields: {sorted(missing)}.",
                })
                continue

            if not isinstance(entry["actually_vulnerable"], bool):
                errors.append({
                    "file": gt_file.name,
                    "entry_index": i,
                    "message": (
                        f"'actually_vulnerable' must be a bool, "
                        f"got {type(entry['actually_vulnerable']).__name__} "
                        f"(route_id={entry.get('route_id', '?')!r})."
                    ),
                })

            route_id = str(entry.get("route_id", ""))

            if not route_id:
                errors.append({
                    "file": gt_file.name,
                    "entry_index": i,
                    "message": "route_id is empty.",
                })
                continue

            # (b) Duplicate check.
            if route_id in seen_ids:
                errors.append({
                    "file": gt_file.name,
                    "entry_index": i,
                    "message": (
                        f"Duplicate route_id '{route_id}' "
                        f"(first seen at index {seen_ids[route_id]})."
                    ),
                })
            else:
                seen_ids[route_id] = i

            # (d) Soft format check.
            if not _ROUTE_ID_PATTERN.match(route_id):
                warnings.append({
                    "file": gt_file.name,
                    "entry_index": i,
                    "message": (
                        f"route_id '{route_id}' does not match the expected "
                        f"'METHOD_/path_linenum' pattern.  Confirm it was "
                        f"copied from actual analyzer output."
                    ),
                })

    return {
        "total_entries": total_entries,
        "errors": errors,
        "warnings": warnings,
        "passed": len(errors) == 0,
    }


# ── CLI ────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 64)
    print("  bola-sentinel — Ground-Truth Validation")
    print("=" * 64)

    result = validate_all_ground_truth()

    total = result["total_entries"]
    errors = result["errors"]
    warnings = result["warnings"]

    print(f"\n  Total entries checked : {total}")
    print(f"  Errors                : {len(errors)}")
    print(f"  Warnings              : {len(warnings)}")

    if warnings:
        print("\n  ⚠ Warnings:")
        for w in warnings:
            idx = f"[{w['entry_index']}]" if w["entry_index"] is not None else ""
            print(f"    {w['file']}{idx}: {w['message']}")

    if errors:
        print("\n  ✗ Errors (must fix before running benchmark):")
        for e in errors:
            idx = f"[{e['entry_index']}]" if e["entry_index"] is not None else ""
            print(f"    {e['file']}{idx}: {e['message']}")
        print("\n  RESULT: FAILED — fix errors above, then re-run.")
        sys.exit(1)
    else:
        print("\n  RESULT: PASSED — ground truth is valid.")


if __name__ == "__main__":
    main()
