"""
collect_dataset.py — CLI for adding new benchmark entries.

Usage
-----
  python datasets/collect_dataset.py add \\
      --app juice_shop \\
      --vuln-name "Order BOLA via DELETE /api/Orders/:id" \\
      --route-id  "DELETE_/api/Orders/1_88" \\
      --method    DELETE \\
      --route     "/api/Orders/:id" \\
      --vulnerable-version "14.3.1" \\
      --expected-verdict   true \\
      --source     cve \\
      --cve-id    "CVE-2024-12345" \\
      --patched-version "14.4.0" \\
      --notes     "No ownership check; any authenticated user can delete any order"

⚠️  --route-id MUST be copied from actual analyzer output
    (results/static_analysis_results.json → "route_id" field).
    Run `bola-sentinel analyze <source_path>` first, find the matching
    route in the output, and copy its exact route_id here.
    Wrong values cause Phase 4's ground-truth join to silently miss entries.

How new CVEs get added going forward
-------------------------------------
  1. Clone the CVE-affected repository into datasets/real_cves/<name>/.
  2. Add an entry to datasets/app_registry.json.
  3. Run `bola-sentinel analyze datasets/real_cves/<name>/` and find route_id.
  4. Run this script with that route_id.
  5. Run `python datasets/validate_dataset.py` to confirm no errors.
  6. Run `python run_benchmark.py` to execute the full pipeline.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure project root is importable.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from datasets.dataset_schema import DatasetEntry, to_ground_truth_entry  # noqa: E402

_GROUND_TRUTH_DIR = _PROJECT_ROOT / "datasets" / "ground_truth"
_REGISTRY_FILE = _PROJECT_ROOT / "datasets" / "app_registry.json"


# ── Core logic ─────────────────────────────────────────────────────────────

def _load_registry() -> list[dict]:
    if not _REGISTRY_FILE.exists():
        raise FileNotFoundError(f"app_registry.json not found at {_REGISTRY_FILE}")
    return json.loads(_REGISTRY_FILE.read_text(encoding="utf-8"))


def _registry_app_names() -> set[str]:
    return {e["application_name"] for e in _load_registry() if "application_name" in e}


def add_dataset_entry(entry: DatasetEntry, route_id: str) -> Path:
    """
    Append a new ground-truth entry to
    datasets/ground_truth/{application_name}.json.

    Validation
    ----------
    • Raises ValueError if application_name is not in app_registry.json.
    • Raises ValueError if route_id already exists in the file (dedup guard).
    • Creates the file if it does not yet exist.

    Parameters
    ----------
    entry:
        A populated DatasetEntry.
    route_id:
        Exact route_id from Phase 1 analyzer output.  See module docstring.

    Returns
    -------
    Path
        Path of the updated ground-truth file.
    """
    # Validate application is registered.
    known = _registry_app_names()
    if entry.application_name not in known:
        raise ValueError(
            f"Unknown application_name '{entry.application_name}'.\n"
            f"Known applications: {sorted(known)}\n"
            f"Add it to datasets/app_registry.json first."
        )

    gt_file = _GROUND_TRUTH_DIR / f"{entry.application_name}.json"
    _GROUND_TRUTH_DIR.mkdir(parents=True, exist_ok=True)

    existing: list[dict] = []
    if gt_file.exists():
        try:
            existing = json.loads(gt_file.read_text(encoding="utf-8"))
            if not isinstance(existing, list):
                raise ValueError(f"{gt_file.name} must be a JSON array.")
        except json.JSONDecodeError as exc:
            raise ValueError(f"{gt_file.name} is not valid JSON: {exc}") from exc

    # Dedup guard.
    existing_ids = {e.get("route_id") for e in existing}
    if route_id in existing_ids:
        raise ValueError(
            f"route_id '{route_id}' already exists in {gt_file.name}.\n"
            "Use a different route_id or update the existing entry manually."
        )

    new_entry = to_ground_truth_entry(entry, route_id)
    existing.append(new_entry)

    gt_file.write_text(
        json.dumps(existing, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"✓ Added route_id '{route_id}' to {gt_file.relative_to(_PROJECT_ROOT)}")
    print(f"  actually_vulnerable: {new_entry['actually_vulnerable']}")
    print(f"  source:              {new_entry['source']}")
    return gt_file


# ── CLI ────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="collect_dataset.py",
        description="Add a new benchmark entry to datasets/ground_truth/.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)
    add_cmd = sub.add_parser("add", help="Add a new entry.")
    add_cmd.add_argument("--app", required=True, dest="application_name",
                         help="Application name matching app_registry.json.")
    add_cmd.add_argument("--vuln-name", required=True, dest="vulnerability_name",
                         help="Human-readable vulnerability description.")
    add_cmd.add_argument("--route-id", required=True, dest="route_id",
                         help="⚠ EXACT route_id from analyzer output. "
                              "Run `bola-sentinel analyze` first and copy from results.")
    add_cmd.add_argument("--route", required=True,
                         help="Route path as it appears in source code.")
    add_cmd.add_argument("--method", required=True,
                         choices=["POST", "PUT", "PATCH", "DELETE"])
    add_cmd.add_argument("--vulnerable-version", required=True,
                         dest="vulnerable_version")
    add_cmd.add_argument("--patched-version", default=None, dest="patched_version")
    add_cmd.add_argument("--expected-verdict", required=True, dest="expected_verdict",
                         choices=["true", "false"],
                         help="true = actually vulnerable, false = safe (true-negative).")
    add_cmd.add_argument("--source", required=True,
                         choices=["juice_shop", "cve", "advisory", "manual"])
    add_cmd.add_argument("--cve-id", default=None, dest="cve_id")
    add_cmd.add_argument("--notes", default="")
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "add":
        entry = DatasetEntry(
            application_name=args.application_name,
            vulnerability_name=args.vulnerability_name,
            cve_id=args.cve_id,
            route=args.route,
            method=args.method,  # type: ignore[arg-type]
            vulnerable_version=args.vulnerable_version,
            patched_version=args.patched_version,
            expected_verdict=(args.expected_verdict == "true"),
            source=args.source,  # type: ignore[arg-type]
            notes=args.notes,
        )
        try:
            add_dataset_entry(entry, args.route_id)
        except (ValueError, FileNotFoundError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
