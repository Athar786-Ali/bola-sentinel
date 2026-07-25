#!/usr/bin/env python3
"""
generate_review_template.py — Automated ground-truth template generator.

Reads Phase 1 static analysis output and generates a JSON template
for all discovered routes. Leaves the human-curated fields empty for
manual completion.

Usage
-----
  python datasets/generate_review_template.py \\
      --app vuln-nodejs-app \\
      --input results/benchmark_runs/vuln-nodejs-app/static_analysis_results.json
"""

import argparse
import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

def generate_template(app_name: str, input_file: Path) -> Path:
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    data = json.loads(input_file.read_text(encoding="utf-8"))
    template_entries = []
    
    # Static analyzer outputs a list of routes
    for route_obj in data:
        route_id = route_obj["route_id"]
        
        entry = {
            "route_id": route_id,
            "actually_vulnerable": None,  # TODO: true/false
            "source": "manual",
            "cve_id": None,
            "cwe_id": None,               # e.g., "CWE-284"
            "owasp_category": None,       # e.g., "API1:2023 BOLA"
            "notes": f"[{route_obj['http_method']} {route_obj['route_path']}] TODO: explain",
            "source_reference": None,
            "evidence": None,
            "review_metadata": {
                "reviewer": "TODO",
                "review_date": "2026-07-25T00:00:00Z",
                "confidence": "Medium"
            }
        }
        template_entries.append(entry)
        
    out_dir = _PROJECT_ROOT / "datasets" / "ground_truth"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{app_name}_TEMPLATE.json"
    
    out_file.write_text(json.dumps(template_entries, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_file

def main():
    parser = argparse.ArgumentParser(description="Generate Ground-Truth Template")
    parser.add_argument("--app", required=True, help="Application name")
    parser.add_argument("--input", required=True, help="Path to static_analysis_results.json")
    args = parser.parse_args()
    
    try:
        out_file = generate_template(args.app, Path(args.input))
        print(f"✓ Generated template at {out_file.relative_to(_PROJECT_ROOT)}")
        print(f"  Total routes mapped: {len(json.loads(out_file.read_text()))}")
        print("  Next: Edit this file, fill in the null/TODO fields, and rename to .json")
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
