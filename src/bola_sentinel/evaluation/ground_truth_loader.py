"""
Ground-truth loader for the bola-sentinel evaluation layer.

Reads a **single** application-specific JSON file from
``datasets/ground_truth/{app_name}.json`` and returns a mapping of
``route_id → actually_vulnerable``.

Design decision (post-audit)
-----------------------------
The original loader (``load_all_ground_truth``) merged every ``.json`` file in
the directory, including ``EXAMPLE.json`` and ground-truth files for other
benchmark applications.  This caused cross-contamination: the reported
``ground_truth_size`` was inflated and foreign entries polluted confusion
matrices.

The replacement (``load_ground_truth_for_app``) loads exactly one file per
evaluation run, isolating datasets by application name.

Failure policy
--------------
If the requested file does not exist or fails to parse, the loader raises a
clear error.  Silently skipping bad files would produce misleadingly optimistic
metrics.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def load_ground_truth_for_app(
    app_name: str,
    dir_path: str = "datasets/ground_truth",
) -> dict[str, bool]:
    """
    Load ground truth for a single benchmark application.

    Parameters
    ----------
    app_name:
        Application name.  The loader reads ``{dir_path}/{app_name}.json``.
    dir_path:
        Path to the directory containing ground-truth JSON files.

    Returns
    -------
    dict[str, bool]
        Mapping of ``route_id → actually_vulnerable`` for the given app.

    Raises
    ------
    FileNotFoundError
        If the ground-truth file for *app_name* does not exist.
    ValueError
        If the file fails to parse or contains invalid entries.
    """
    root = Path(dir_path)
    gt_file = root / f"{app_name}.json"

    if not gt_file.exists():
        raise FileNotFoundError(
            f"Ground truth file not found: {gt_file.resolve()}\n"
            f"Expected file: datasets/ground_truth/{app_name}.json\n"
            "Create this file with the ground-truth entries for your "
            "benchmark application.\n"
            "See datasets/ground_truth/EXAMPLE.json for the expected format."
        )

    try:
        raw = json.loads(gt_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Ground truth file {gt_file.name}: JSON parse error — {exc}"
        ) from exc

    if not isinstance(raw, list):
        raise ValueError(
            f"Ground truth file {gt_file.name}: expected a JSON array, "
            f"got {type(raw).__name__}"
        )

    merged: dict[str, bool] = {}
    failures: list[str] = []

    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            failures.append(
                f"  entry[{i}]: expected dict, got {type(entry).__name__}"
            )
            continue
        if "route_id" not in entry:
            failures.append(f"  entry[{i}]: missing 'route_id'")
            continue
        if "actually_vulnerable" not in entry:
            failures.append(f"  entry[{i}]: missing 'actually_vulnerable'")
            continue

        rid = str(entry["route_id"])
        vuln = bool(entry["actually_vulnerable"])

        if rid in merged and merged[rid] != vuln:
            logger.warning(
                "Ground-truth conflict for route_id %r in %s: "
                "entry[%d] says %s, overriding previous value %s",
                rid,
                gt_file.name,
                i,
                vuln,
                merged[rid],
            )
        merged[rid] = vuln

    if failures:
        raise ValueError(
            f"Ground truth file {gt_file.name}: "
            f"{len(failures)} invalid entries:\n" + "\n".join(failures)
        )

    vulnerable_count = sum(1 for v in merged.values() if v)
    logger.info(
        "Ground truth loaded from %s: %d routes total "
        "(%d vulnerable, %d not vulnerable)",
        gt_file.name,
        len(merged),
        vulnerable_count,
        len(merged) - vulnerable_count,
    )
    return merged


# ── Backward compatibility alias ──────────────────────────────────────────
# Deprecated: use load_ground_truth_for_app instead.

def load_all_ground_truth(
    dir_path: str = "datasets/ground_truth",
) -> dict[str, bool]:
    """
    DEPRECATED — use ``load_ground_truth_for_app(app_name, dir_path)`` instead.

    This function is preserved only for backward compatibility with tests
    that have not yet been updated.  It raises a clear deprecation warning.
    """
    import warnings
    warnings.warn(
        "load_all_ground_truth() is deprecated.  "
        "Use load_ground_truth_for_app(app_name) instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    # Fallback: merge all non-EXAMPLE JSON files (old behaviour minus the bug)
    root = Path(dir_path)
    if not root.exists():
        raise FileNotFoundError(f"Ground truth directory not found: {root.resolve()}")

    merged: dict[str, bool] = {}
    for path in sorted(root.glob("*.json")):
        if path.name.upper().startswith("EXAMPLE"):
            continue
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            continue
        for entry in raw:
            if isinstance(entry, dict) and "route_id" in entry and "actually_vulnerable" in entry:
                merged[str(entry["route_id"])] = bool(entry["actually_vulnerable"])

    return merged
