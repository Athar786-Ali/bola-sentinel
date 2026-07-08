"""
Evaluation-run logger for reproducibility.

Every ``evaluate`` CLI invocation writes a single timestamped JSON file to
``logs/evaluation_logs/`` capturing the full input/output context:
counts, matched ground-truth entries, final metrics, and stage deltas.

This log file is the audit trail that ties the console/report numbers back
to the exact data that was processed.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bola_sentinel.config import settings

logger = logging.getLogger(__name__)

_UNSAFE_CHARS_RE = re.compile(r"[/\\:*?\"<>|{}\s]")


def _timestamp() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def log_evaluation_run(
    verified_route_count: int,
    ground_truth_file_count: int,
    ground_truth_route_count: int,
    routes_evaluated: int,
    routes_skipped: int,
    comparison: dict[str, Any],
) -> Path:
    """
    Persist a complete record of this evaluation run to disk.

    Parameters
    ----------
    verified_route_count:
        Total number of VerifiedRoute objects read from the input file.
    ground_truth_file_count:
        Number of ground-truth JSON files loaded.
    ground_truth_route_count:
        Total unique route_ids in ground truth after merge.
    routes_evaluated:
        Routes with a ground-truth label (contributed to metrics).
    routes_skipped:
        Routes without a ground-truth label (excluded from metrics).
    comparison:
        The full dict returned by ``run_progressive_comparison``.

    Returns
    -------
    Path
        Path of the written log file.
    """
    logs_dir = Path(settings.logs_dir) / "evaluation_logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    ts = _timestamp()
    out_path = logs_dir / f"evaluation_{ts}.json"

    record = {
        "timestamp": ts,
        "input": {
            "verified_route_count": verified_route_count,
            "ground_truth_file_count": ground_truth_file_count,
            "ground_truth_route_count": ground_truth_route_count,
            "routes_evaluated": routes_evaluated,
            "routes_skipped": routes_skipped,
        },
        "results": comparison,
    }

    try:
        out_path.write_text(
            json.dumps(record, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        logger.info("Evaluation run log written to %s", out_path)
    except OSError:
        logger.exception("Failed to write evaluation run log")

    return out_path
