"""
Evidence logger for the dynamic verification layer.

Every verification attempt — regardless of outcome — produces a complete
JSON log file in logs/verification_logs/.  These files ARE the evidence
artifacts for the research paper.  They must contain every field listed
in the spec so a reviewer can reconstruct the exact probe without re-running
the tool.

File naming: {route_id}_{timestamp}.json
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


def _safe_name(route_id: str) -> str:
    sanitised = _UNSAFE_CHARS_RE.sub("_", route_id)
    return re.sub(r"_+", "_", sanitised).strip("_")[:80]


def _timestamp() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def log_verification_attempt(
    route_id: str,
    attack_request: dict[str, Any],
    response_status: int,
    response_body: str,
    state_before: dict[str, Any] | None,
    state_after: dict[str, Any] | None,
    final_verdict: str,
) -> Path:
    """
    Write a complete verification evidence record to disk.

    Parameters
    ----------
    route_id:
        Identifier of the route being verified.
    attack_request:
        The full probe request dict (url, method, headers, attacker/victim ids).
    response_status:
        HTTP status code received from the target application.
    response_body:
        Raw response body text (may be truncated to 2000 chars for storage).
    state_before:
        Object state captured before the attack probe (None if unavailable).
    state_after:
        Object state captured after the attack probe (None if unavailable).
    final_verdict:
        One of ``"CONFIRMED_VULNERABLE"`` / ``"NOT_VULNERABLE"`` / ``"INCONCLUSIVE"``.

    Returns
    -------
    Path
        Path of the written log file.
    """
    logs_dir = Path(settings.logs_dir) / "verification_logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    ts = _timestamp()
    filename = f"{_safe_name(route_id)}_{ts}.json"
    out_path = logs_dir / filename

    # Redact Authorization header values from the stored evidence for safety.
    safe_headers = {
        k: ("<redacted>" if k.lower() in ("authorization", "x-api-key") else v)
        for k, v in attack_request.get("headers", {}).items()
    }
    safe_attack_request = {**attack_request, "headers": safe_headers}

    record = {
        "route_id": route_id,
        "timestamp": ts,
        "final_verdict": final_verdict,
        "attack_request": safe_attack_request,
        "response": {
            "status_code": response_status,
            "body_snippet": response_body[:2000],
        },
        "state_check": {
            "before": state_before,
            "after": state_after,
            "state_changed": (
                None
                if state_before is None or state_after is None
                else state_before != state_after
            ),
        },
    }

    try:
        out_path.write_text(
            json.dumps(record, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        logger.debug("Verification evidence written to %s", out_path)
    except OSError:
        logger.exception("Failed to write verification log for route %s", route_id)

    return out_path
