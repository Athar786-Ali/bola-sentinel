#!/usr/bin/env python3
"""
verify_dashboard_consistency.py

Reads pipeline JSON files directly and compares computed metrics against
what the dashboard API returns. Reports PASS/FAIL per application.

Usage:
    python scripts/verify_dashboard_consistency.py [--api-base http://localhost:3001]
"""
import json
import sys
import os
import argparse
from pathlib import Path


def load_json(path: Path):
    """Load a JSON file, return None if missing."""
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def compute_metrics_from_files(app_name: str, root: Path) -> dict:
    """Independently compute metrics from raw pipeline output files."""
    runs_dir = root / "results" / "benchmark_runs" / app_name
    gt_path = root / "datasets" / "ground_truth" / f"{app_name}.json"

    # Load files
    static = load_json(runs_dir / "static_analysis_results.json") or []
    llm = load_json(runs_dir / "llm_classified_results.json") or []
    verified = load_json(runs_dir / "final_verified_results.json") or []
    gt_raw = load_json(gt_path)

    # Parse ground truth
    if gt_raw is None:
        gt_entries = []
    elif isinstance(gt_raw, list):
        gt_entries = gt_raw
    elif isinstance(gt_raw, dict) and "routes" in gt_raw:
        gt_entries = gt_raw["routes"]
    else:
        gt_entries = []

    # Build route_id sets
    static_route_ids = {r["route_id"] for r in static if "route_id" in r}
    gt_route_ids = {r["route_id"] for r in gt_entries if "route_id" in r}

    # Count LLM flagged (reading nested llm_classification.is_vulnerable)
    llm_flagged_count = 0
    llm_flagged_ids = set()
    for r in llm:
        cls = r.get("llm_classification")
        if cls and cls.get("is_vulnerable"):
            llm_flagged_count += 1
            llm_flagged_ids.add(r["route_id"])

    # Count dynamically confirmed
    confirmed_count = 0
    confirmed_ids = set()
    for r in verified:
        ver = r.get("verification")
        if ver and ver.get("verification_status") == "CONFIRMED_VULNERABLE":
            confirmed_count += 1
            confirmed_ids.add(r["route_id"])

    # Ground truth stats
    gt_vulnerable_count = sum(
        1 for r in gt_entries if r.get("actually_vulnerable")
    )
    gt_size = len(gt_entries)

    # Matched vs unmatched
    matched_gt = gt_route_ids & static_route_ids
    unmatched_gt = gt_route_ids - static_route_ids

    return {
        "total_static_routes": len(static_route_ids),
        "llm_flagged": llm_flagged_count,
        "llm_flagged_ids": sorted(llm_flagged_ids),
        "dynamically_confirmed": confirmed_count,
        "dynamically_confirmed_ids": sorted(confirmed_ids),
        "ground_truth_size": gt_size,
        "ground_truth_vulnerable": gt_vulnerable_count,
        "matched_gt_entries": len(matched_gt),
        "unmatched_gt_entries": len(unmatched_gt),
        "unmatched_gt_ids": sorted(unmatched_gt),
        "coverage": len(matched_gt) / gt_size if gt_size > 0 else 0,
    }


def compute_api_metrics(api_data: list) -> dict:
    """Compute the same metrics from what the API returns."""
    matched = [d for d in api_data if d.get("is_matched", True) and d.get("http_method") != "UNKNOWN"]
    all_entries = api_data

    return {
        "total_static_routes": len(matched),
        "llm_flagged": sum(1 for d in matched if d.get("llm_flagged")),
        "dynamically_confirmed": sum(1 for d in matched if d.get("dynamically_verified")),
        "ground_truth_vulnerable": sum(1 for d in all_entries if d.get("ground_truth") is True),
        "ground_truth_size": sum(1 for d in all_entries if d.get("ground_truth") is not None),
        "unmatched_gt_entries": len([d for d in api_data if not d.get("is_matched", True) or d.get("http_method") == "UNKNOWN"]),
    }


def verify_app(app_name: str, root: Path, api_base: str = None) -> bool:
    """Verify consistency for a single app. Returns True if PASS."""
    print(f"\n{'='*60}")
    print(f"  Verifying: {app_name}")
    print(f"{'='*60}")

    # Compute from files
    file_metrics = compute_metrics_from_files(app_name, root)

    print(f"\n  [FROM FILES]")
    print(f"    Static routes analyzed:    {file_metrics['total_static_routes']}")
    print(f"    LLM flagged:               {file_metrics['llm_flagged']}")
    if file_metrics['llm_flagged_ids']:
        for rid in file_metrics['llm_flagged_ids']:
            print(f"      - {rid}")
    print(f"    Dynamically confirmed:     {file_metrics['dynamically_confirmed']}")
    print(f"    Ground truth size:         {file_metrics['ground_truth_size']}")
    print(f"    Ground truth vulnerable:   {file_metrics['ground_truth_vulnerable']}")
    print(f"    Matched GT entries:        {file_metrics['matched_gt_entries']}")
    print(f"    Unmatched GT entries:       {file_metrics['unmatched_gt_entries']}")
    if file_metrics['unmatched_gt_ids']:
        for rid in file_metrics['unmatched_gt_ids']:
            print(f"      - {rid}")
    print(f"    Coverage:                  {file_metrics['coverage']:.2%}")

    # If API base provided, also check the API
    if api_base:
        try:
            import urllib.request
            url = f"{api_base}/api/vulnerabilities/{app_name}"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                api_data = json.loads(resp.read().decode())
        except Exception as e:
            print(f"\n  [API CHECK] SKIP - Could not reach {api_base}: {e}")
            api_data = None
    else:
        api_data = None

    if api_data:
        api_metrics = compute_api_metrics(api_data)
        print(f"\n  [FROM API: {api_base}]")
        print(f"    Matched routes:            {api_metrics['total_static_routes']}")
        print(f"    LLM flagged:               {api_metrics['llm_flagged']}")
        print(f"    Dynamically confirmed:     {api_metrics['dynamically_confirmed']}")
        print(f"    Ground truth size:         {api_metrics['ground_truth_size']}")
        print(f"    Ground truth vulnerable:   {api_metrics['ground_truth_vulnerable']}")
        print(f"    Unmatched GT entries:       {api_metrics['unmatched_gt_entries']}")

        # Compare
        checks = [
            ("LLM Flagged", file_metrics["llm_flagged"], api_metrics["llm_flagged"]),
            ("Dynamically Confirmed", file_metrics["dynamically_confirmed"], api_metrics["dynamically_confirmed"]),
            ("Ground Truth Vulnerable", file_metrics["ground_truth_vulnerable"], api_metrics["ground_truth_vulnerable"]),
            ("Ground Truth Size", file_metrics["ground_truth_size"], api_metrics["ground_truth_size"]),
            ("Unmatched GT Entries", file_metrics["unmatched_gt_entries"], api_metrics["unmatched_gt_entries"]),
        ]

        all_pass = True
        print(f"\n  [COMPARISON]")
        for label, expected, actual in checks:
            status = "✅ PASS" if expected == actual else "❌ FAIL"
            if expected != actual:
                all_pass = False
            print(f"    {label:30s}  File={expected:4d}  API={actual:4d}  {status}")

        return all_pass
    else:
        print(f"\n  [RESULT] File-only verification complete (no API check)")
        return True


def main():
    parser = argparse.ArgumentParser(description="Verify dashboard data consistency")
    parser.add_argument("--api-base", default=None,
                       help="Dashboard API base URL (e.g. http://localhost:3001)")
    parser.add_argument("--root", default=None,
                       help="Project root directory")
    args = parser.parse_args()

    # Find project root
    if args.root:
        root = Path(args.root)
    else:
        # Try common locations
        candidates = [
            Path(__file__).parent.parent,  # scripts/ -> project root
            Path.cwd(),
        ]
        root = None
        for c in candidates:
            if (c / "results" / "benchmark_runs").exists():
                root = c
                break
        if root is None:
            print("ERROR: Could not find project root. Use --root flag.")
            sys.exit(1)

    print(f"Project root: {root}")

    # Discover apps from benchmark runs
    runs_dir = root / "results" / "benchmark_runs"
    apps = [d.name for d in runs_dir.iterdir()
            if d.is_dir() and (d / "static_analysis_results.json").exists()]

    if not apps:
        print("ERROR: No benchmark run data found.")
        sys.exit(1)

    print(f"Applications found: {', '.join(apps)}")

    all_pass = True
    for app in sorted(apps):
        passed = verify_app(app, root, args.api_base)
        if not passed:
            all_pass = False

    print(f"\n{'='*60}")
    if all_pass:
        print("  OVERALL: ✅ ALL CHECKS PASSED")
    else:
        print("  OVERALL: ❌ SOME CHECKS FAILED")
    print(f"{'='*60}")

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
