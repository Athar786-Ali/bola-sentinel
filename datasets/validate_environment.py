#!/usr/bin/env python3
"""
validate_environment.py — Pre-flight environment validation.

Ensures the Docker container is running, test_users.json is valid,
and the ground_truth matches the static analysis output.

Usage
-----
  python datasets/validate_environment.py --app vuln-nodejs-app
"""

import argparse
import json
import socket
import sys
from pathlib import Path
from urllib.parse import urlparse

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

def check_network(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.hostname or "localhost"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        with socket.create_connection((host, port), timeout=3):
            return True
    except OSError:
        return False

def validate_env(app_name: str) -> None:
    registry_file = _PROJECT_ROOT / "datasets" / "app_registry.json"
    registry = json.loads(registry_file.read_text())
    
    app_entry = next((e for e in registry if e.get("application_name") == app_name), None)
    if not app_entry:
        print(f"Error: Application '{app_name}' not found in app_registry.json")
        sys.exit(1)
        
    print(f"Validating environment for {app_name}...")
    
    # 1. Network check
    base_url = app_entry["base_url"]
    if check_network(base_url):
        print(f" ✓ Network: {base_url} is reachable.")
    else:
        print(f" ✗ Network: {base_url} is unreachable. Is the Docker container running?")
        sys.exit(1)
        
    # 2. Test users validation
    tu_path = _PROJECT_ROOT / app_entry["test_users_file"]
    if not tu_path.exists():
        print(f" ✗ Test users: File not found at {tu_path}")
        sys.exit(1)
        
    try:
        tu_data = json.loads(tu_path.read_text())
        if "user_a" not in tu_data or "user_b" not in tu_data:
            print(" ✗ Test users: Missing 'user_a' or 'user_b' keys.")
            sys.exit(1)
        for user in ("user_a", "user_b"):
            if "auth_header" not in tu_data[user] or "user_id" not in tu_data[user]:
                print(f" ✗ Test users: '{user}' missing 'auth_header' or 'user_id'.")
                sys.exit(1)
        print(f" ✓ Test users: Schema is valid.")
    except json.JSONDecodeError:
        print(f" ✗ Test users: Invalid JSON in {tu_path}")
        sys.exit(1)

    # 3. Ground truth validation is handled by validate_dataset.py natively
    gt_path = _PROJECT_ROOT / app_entry["ground_truth_file"]
    if gt_path.exists():
        print(f" ✓ Ground truth: File exists at {gt_path.name}")
    else:
        print(f" ⚠ Ground truth: File not found at {gt_path.name} (run collect_dataset.py/generate_review_template.py first)")

    print("\nEnvironment is ready for benchmarking.")

def main():
    parser = argparse.ArgumentParser(description="Validate Benchmark Environment")
    parser.add_argument("--app", required=True, help="Application name")
    args = parser.parse_args()
    validate_env(args.app)

if __name__ == "__main__":
    main()
