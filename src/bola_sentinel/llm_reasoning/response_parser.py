"""
Robust LLM response parser for bola-sentinel.

Handles the common ways LLMs wrap their JSON output:
  - Bare valid JSON
  - JSON inside ```json ... ``` or ``` ... ``` code fences
  - JSON preceded/followed by conversational text
  - Multiple JSON objects (takes the first valid one)
  - Whitespace / BOM / control characters

The parsing pipeline is deterministic and ordered:
  1. Try direct parse (fastest path for well-behaved models)
  2. Strip markdown code fences and retry
  3. Extract the first {...} block via brace matching and retry
  4. Give up — return a structured error

No randomness, no heuristics, no silent defaults.
"""

from __future__ import annotations

import json
import logging
import re

from pydantic import ValidationError

from bola_sentinel.models.schemas import LlmClassification

logger = logging.getLogger(__name__)


class ParseResult:
    """Container for the outcome of a parse attempt."""

    __slots__ = ("success", "classification", "raw_response", "cleaned_response",
                 "strategy_used", "error_message", "attempts")

    def __init__(
        self,
        success: bool,
        classification: LlmClassification | None,
        raw_response: str,
        cleaned_response: str,
        strategy_used: str,
        error_message: str | None,
        attempts: list[dict],
    ):
        self.success = success
        self.classification = classification
        self.raw_response = raw_response
        self.cleaned_response = cleaned_response
        self.strategy_used = strategy_used
        self.error_message = error_message
        self.attempts = attempts

    def to_log_dict(self) -> dict:
        """Serialisable representation for logging."""
        return {
            "success": self.success,
            "strategy_used": self.strategy_used,
            "error_message": self.error_message,
            "cleaned_response": self.cleaned_response[:500],
            "attempts": self.attempts,
        }


# ── Internal helpers ───────────────────────────────────────────────────────

# Matches ```json ... ``` or ``` ... ``` blocks.
_CODE_FENCE_RE = re.compile(
    r"```(?:json)?\s*\n?(.*?)\n?\s*```",
    re.DOTALL | re.IGNORECASE,
)


def _strip_bom_and_control(text: str) -> str:
    """Remove BOM, NUL bytes, and other invisible control characters."""
    text = text.lstrip("\ufeff")
    text = text.replace("\x00", "")
    return text.strip()


def _try_validate(json_str: str) -> LlmClassification:
    """Attempt Pydantic validation. Raises on failure."""
    return LlmClassification.model_validate_json(json_str)


def _try_validate_dict(d: dict) -> LlmClassification:
    """Attempt Pydantic validation from a dict. Raises on failure."""
    return LlmClassification.model_validate(d)


def _extract_first_json_object(text: str) -> str | None:
    """
    Extract the first balanced {...} block from text using brace counting.

    This handles cases where the LLM wraps JSON in commentary:
      "Here is the result:\\n{...}\\nLet me know if you need more."
    """
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape_next = False

    for i in range(start, len(text)):
        ch = text[i]

        if escape_next:
            escape_next = False
            continue

        if ch == "\\":
            if in_string:
                escape_next = True
            continue

        if ch == '"' and not escape_next:
            in_string = not in_string
            continue

        if in_string:
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start: i + 1]

    return None


# ── Public API ─────────────────────────────────────────────────────────────


def parse_llm_response(raw_response: str) -> ParseResult:
    """
    Parse a raw LLM response string into an LlmClassification.

    Attempts multiple parsing strategies in order of increasing aggression.
    Returns a ParseResult with full diagnostic information for logging.

    Parameters
    ----------
    raw_response:
        The verbatim string returned by the LLM (Ollama ``response`` field).

    Returns
    -------
    ParseResult
        Always returned (never raises).  Check ``.success`` to determine
        if parsing succeeded.
    """
    attempts: list[dict] = []
    cleaned = _strip_bom_and_control(raw_response)

    # ── Strategy 1: Direct parse ──────────────────────────────────────
    strategy = "direct_parse"
    try:
        classification = _try_validate(cleaned)
        logger.debug("Parse succeeded with strategy: %s", strategy)
        return ParseResult(
            success=True,
            classification=classification,
            raw_response=raw_response,
            cleaned_response=cleaned,
            strategy_used=strategy,
            error_message=None,
            attempts=attempts,
        )
    except (ValidationError, ValueError, json.JSONDecodeError) as exc:
        attempts.append({"strategy": strategy, "error": str(exc)[:200]})

    # ── Strategy 2: Strip markdown code fences ────────────────────────
    strategy = "strip_code_fences"
    fence_matches = _CODE_FENCE_RE.findall(cleaned)
    for i, match in enumerate(fence_matches):
        fence_content = match.strip()
        try:
            classification = _try_validate(fence_content)
            logger.debug("Parse succeeded with strategy: %s (match %d)", strategy, i)
            return ParseResult(
                success=True,
                classification=classification,
                raw_response=raw_response,
                cleaned_response=fence_content,
                strategy_used=strategy,
                error_message=None,
                attempts=attempts,
            )
        except (ValidationError, ValueError, json.JSONDecodeError) as exc:
            attempts.append({"strategy": f"{strategy}[{i}]", "error": str(exc)[:200]})

    # ── Strategy 3: Extract first balanced JSON object ────────────────
    strategy = "brace_extraction"
    extracted = _extract_first_json_object(cleaned)
    if extracted:
        try:
            classification = _try_validate(extracted)
            logger.debug("Parse succeeded with strategy: %s", strategy)
            return ParseResult(
                success=True,
                classification=classification,
                raw_response=raw_response,
                cleaned_response=extracted,
                strategy_used=strategy,
                error_message=None,
                attempts=attempts,
            )
        except (ValidationError, ValueError, json.JSONDecodeError) as exc:
            attempts.append({"strategy": strategy, "error": str(exc)[:200]})

        # ── Strategy 3b: Extracted JSON is valid JSON but fails schema ──
        # Try parsing as dict and normalising field types.
        strategy = "brace_extraction_with_coercion"
        try:
            raw_dict = json.loads(extracted)
            if isinstance(raw_dict, dict):
                classification = _try_validate_dict(raw_dict)
                logger.debug("Parse succeeded with strategy: %s", strategy)
                return ParseResult(
                    success=True,
                    classification=classification,
                    raw_response=raw_response,
                    cleaned_response=extracted,
                    strategy_used=strategy,
                    error_message=None,
                    attempts=attempts,
                )
        except (ValidationError, ValueError, json.JSONDecodeError) as exc:
            attempts.append({"strategy": strategy, "error": str(exc)[:200]})
    else:
        attempts.append({"strategy": strategy, "error": "No {...} block found in response"})

    # ── All strategies exhausted ──────────────────────────────────────
    error_summary = "; ".join(
        f"[{a['strategy']}] {a['error'][:80]}" for a in attempts
    )
    logger.warning(
        "All parsing strategies exhausted for LLM response (len=%d). "
        "Attempts: %s\nRaw (first 300 chars): %.300s",
        len(raw_response),
        error_summary,
        raw_response,
    )

    return ParseResult(
        success=False,
        classification=None,
        raw_response=raw_response,
        cleaned_response=cleaned,
        strategy_used="NONE",
        error_message=error_summary,
        attempts=attempts,
    )
