"""
Mandatory LLM call logger for bola-sentinel research reproducibility.

Every single LLM interaction MUST produce two log files:
  logs/llm_inputs/{route_id}_{timestamp}.json   — prompt sent
  logs/llm_outputs/{route_id}_{timestamp}.json  — raw response received

These files are the audit trail for the paper.  Without them, a run cannot
be reproduced or reviewed.  Logging is therefore NOT optional instrumentation
— it is called unconditionally by classifier.py before and after every LLM
call.

File-naming note: route_ids contain slashes (e.g. "POST_/orders/{id}_42").
Slashes are replaced with underscores in file names to avoid accidental
directory creation.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from bola_sentinel.config import settings

logger = logging.getLogger(__name__)

# Regex to sanitise route_id into a safe file-name component.
_UNSAFE_CHARS_RE = re.compile(r"[/\\:*?\"<>|{}\s]")


def _safe_name(route_id: str) -> str:
    """Replace path-unsafe characters with underscores, collapse runs."""
    sanitised = _UNSAFE_CHARS_RE.sub("_", route_id)
    return re.sub(r"_+", "_", sanitised).strip("_")[:80]


def _timestamp() -> str:
    """Return a compact ISO-8601 UTC timestamp safe for file names."""
    return datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def log_llm_input(
    route_id: str,
    system_prompt: str,
    user_prompt: str,
) -> Path:
    """
    Persist the exact prompts about to be sent to the LLM.

    Must be called BEFORE the LLM call so that the inputs are preserved even
    if the call crashes or times out.

    Parameters
    ----------
    route_id:
        Identifies which route this call is for (used in the file name).
    system_prompt:
        Full system-role text sent to Ollama.
    user_prompt:
        Full user-turn text sent to Ollama.

    Returns
    -------
    Path
        The path of the written log file.
    """
    inputs_dir = Path(settings.logs_dir) / "llm_inputs"
    _ensure_dir(inputs_dir)

    ts = _timestamp()
    filename = f"{_safe_name(route_id)}_{ts}.json"
    out_path = inputs_dir / filename

    payload = {
        "route_id": route_id,
        "timestamp": ts,
        "model": settings.ollama_model,
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
    }

    try:
        out_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError:
        logger.exception("Failed to write LLM input log for route %s", route_id)

    return out_path


def log_llm_output(
    route_id: str,
    raw_response: str,
    parsed_successfully: bool,
) -> Path:
    """
    Persist the raw LLM response immediately after it is received.

    Must be called IMMEDIATELY after call_ollama() returns (or raises), so
    the raw text is on disk before any parsing is attempted.

    Parameters
    ----------
    route_id:
        Identifies which route this response belongs to.
    raw_response:
        The verbatim string returned by call_ollama().
    parsed_successfully:
        True if the response was subsequently parsed into LlmClassification
        without error.  Pass False first if calling before parsing; the
        classifier may update this in a second call if needed — but the
        simpler pattern is to call once after parsing with the known outcome.

    Returns
    -------
    Path
        The path of the written log file.
    """
    outputs_dir = Path(settings.logs_dir) / "llm_outputs"
    _ensure_dir(outputs_dir)

    ts = _timestamp()
    filename = f"{_safe_name(route_id)}_{ts}.json"
    out_path = outputs_dir / filename

    payload = {
        "route_id": route_id,
        "timestamp": ts,
        "model": settings.ollama_model,
        "raw_response": raw_response,
        "parsed_successfully": parsed_successfully,
    }

    try:
        out_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError:
        logger.exception("Failed to write LLM output log for route %s", route_id)

    return out_path
