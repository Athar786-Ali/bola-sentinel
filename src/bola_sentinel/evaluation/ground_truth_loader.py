"""
Ground-truth loader for the bola-sentinel evaluation layer.

Reads every JSON file in ``datasets/ground_truth/`` and merges them into
a single dict mapping ``route_id → actually_vulnerable``.

Failure policy
--------------
If one or more files fail to parse the loader raises a single
``ValueError`` listing all failures, rather than silently skipping them.
Silently skipping bad files would produce misleadingly optimistic metrics.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def load_all_ground_truth(
    dir_path: str = "datasets/ground_truth",
) -> dict[str, bool]:
    """
    Read every ``.json`` file in *dir_path* and merge into one dict.

    Parameters
    ----------
    dir_path:
        Path to the directory containing ground-truth JSON files.

    Returns
    -------
    dict[str, bool]
        Mapping of ``route_id → actually_vulnerable`` merged across all
        files.  Later files override earlier ones for duplicate route IDs
        (a warning is logged for each conflict).

    Raises
    ------
    FileNotFoundError
        If *dir_path* does not exist.
    ValueError
        If any file fails to parse, listing every failure in one message.
    """
    root = Path(dir_path)
    if not root.exists():
        raise FileNotFoundError(
            f"Ground truth directory not found: {root.resolve()}\n"
            "Create it and add at least one ground-truth JSON file.\n"
            "See datasets/ground_truth/EXAMPLE.json for the expected format."
        )

    json_files = sorted(root.glob("*.json"))
    if not json_files:
        logger.warning(
            "No ground-truth JSON files found in %s — metrics will be empty.", root
        )
        return {}

    merged: dict[str, bool] = {}
    failures: list[str] = []

    for path in json_files:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append(f"  {path.name}: JSON parse error — {exc}")
            continue
        except OSError as exc:
            failures.append(f"  {path.name}: read error — {exc}")
            continue

        if not isinstance(raw, list):
            failures.append(
                f"  {path.name}: expected a JSON array, got {type(raw).__name__}"
            )
            continue

        entry_failures: list[str] = []
        for i, entry in enumerate(raw):
            if not isinstance(entry, dict):
                entry_failures.append(f"    entry[{i}]: expected dict, got {type(entry).__name__}")
                continue
            if "route_id" not in entry:
                entry_failures.append(f"    entry[{i}]: missing 'route_id'")
                continue
            if "actually_vulnerable" not in entry:
                entry_failures.append(f"    entry[{i}]: missing 'actually_vulnerable'")
                continue

            rid = str(entry["route_id"])
            vuln = bool(entry["actually_vulnerable"])

            if rid in merged and merged[rid] != vuln:
                logger.warning(
                    "Ground-truth conflict for route_id %r: %s says %s, "
                    "overriding previous value %s",
                    rid,
                    path.name,
                    vuln,
                    merged[rid],
                )
            merged[rid] = vuln

        if entry_failures:
            failures.append(
                f"  {path.name}: {len(entry_failures)} invalid entries:\n"
                + "\n".join(entry_failures)
            )
            continue

        logger.info(
            "Loaded ground truth from %s: %d entries", path.name, len(raw)
        )

    if failures:
        raise ValueError(
            f"Failed to load {len(failures)} ground-truth file(s):\n"
            + "\n".join(failures)
        )

    vulnerable_count = sum(1 for v in merged.values() if v)
    logger.info(
        "Ground truth loaded: %d routes total (%d vulnerable, %d not vulnerable)",
        len(merged),
        vulnerable_count,
        len(merged) - vulnerable_count,
    )
    return merged
