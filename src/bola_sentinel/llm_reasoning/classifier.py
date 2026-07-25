"""
BOLA route classifier — LLM reasoning layer.

Orchestrates: prompt building → mandatory logging → Ollama call →
mandatory response logging → JSON parsing → fallback on failure.

Call ordering contract (enforced in classify_route)
----------------------------------------------------
1. build_system_prompt + build_user_prompt
2. log_llm_input          ← BEFORE the network call, always
3. call_ollama
4. log_llm_output         ← IMMEDIATELY after the call, always
5. model_validate_json    ← parse; set parsed_successfully accordingly
6. Return ClassifiedRoute (or fallback LlmClassification on parse failure)
"""

from __future__ import annotations

import logging

from pydantic import ValidationError

from bola_sentinel.models.schemas import (
    ClassifiedRoute,
    LlmClassification,
    StaticAnalysisResult,
)

from .logger import log_llm_input, log_llm_output
from .ollama_client import call_ollama
from .prompts import build_system_prompt, build_user_prompt

logger = logging.getLogger(__name__)

# Auth-check statuses that warrant LLM analysis.
_CLASSIFY_STATUSES: frozenset[str] = frozenset({"ABSENT", "UNCERTAIN"})

# ── Fallback classification returned when the LLM response cannot be parsed ──

_FALLBACK_CLASSIFICATION = LlmClassification(
    applicable_model="NONE",
    is_vulnerable=False,
    confidence="LOW",
    explanation=(
        "LLM response parsing failed — see logs/llm_outputs/ for the raw "
        "text.  This route should be reviewed manually."
    ),
    suggested_test_description=(
        "Manual review required: LLM output could not be parsed."
    ),
    requires_two_users=False,
)


# ── Public API ─────────────────────────────────────────────────────────────


def classify_route(route: StaticAnalysisResult) -> LlmClassification:
    """
    Classify a single route via the local Ollama model.

    Enforces the mandatory log-before / log-after call ordering.  Returns
    a fallback ``LlmClassification`` (confidence="LOW", is_vulnerable=False)
    if the model produces unparseable output rather than crashing.

    Parameters
    ----------
    route:
        A ``StaticAnalysisResult`` with auth_check_status in {"ABSENT",
        "UNCERTAIN"}.

    Returns
    -------
    LlmClassification
        Parsed (or fallback) classification result.
    """
    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt(route)

    # ── Step 2: log inputs BEFORE the network call ─────────────────────
    log_llm_input(
        route_id=route.route_id,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    )

    # ── Step 3: call Ollama ────────────────────────────────────────────
    raw_response: str
    try:
        raw_response = call_ollama(prompt=user_prompt, system_prompt=system_prompt)
    except RuntimeError as exc:
        # Network / model error — log an empty response and return fallback.
        log_llm_output(
            route_id=route.route_id,
            raw_response=f"[ERROR: {exc}]",
            parsed_successfully=False,
        )
        logger.error(
            "Ollama call failed for route %s: %s",
            route.route_id,
            exc,
        )
        return _FALLBACK_CLASSIFICATION

    # ── Step 4: log raw response IMMEDIATELY after receipt ─────────────
    # We log before parsing so the raw text is on disk even if parsing blows up.
    # parsed_successfully is initially unknown — we update after the attempt.
    # Because the logger writes a new timestamped file each call, we write
    # twice only on failure; on success we write once with the correct flag.
    # The implementation writes once here with the eventual parsed_successfully
    # value by deferring the write until after the parse attempt below.

    # ── Step 4 + 5: parse with robust multi-strategy parser ─────────
    from .response_parser import parse_llm_response

    parse_result = parse_llm_response(raw_response)

    if parse_result.success:
        classification = parse_result.classification  # type: ignore[assignment]
        parsed_successfully = True
        logger.info(
            "Parsed LLM response for route %s (strategy=%s)",
            route.route_id,
            parse_result.strategy_used,
        )
    else:
        logger.warning(
            "All parsing strategies exhausted for route %s. "
            "Error: %s\nRaw response (first 300 chars): %.300s",
            route.route_id,
            parse_result.error_message,
            raw_response,
        )
        classification = _FALLBACK_CLASSIFICATION
        parsed_successfully = False

    # ── Log output with full parse diagnostics ────────────────────────
    log_llm_output(
        route_id=route.route_id,
        raw_response=raw_response,
        parsed_successfully=parsed_successfully,
        parse_diagnostics=parse_result.to_log_dict(),
    )

    return classification


def classify_all_routes(
    routes: list[StaticAnalysisResult],
) -> list[ClassifiedRoute]:
    """
    Classify every route in *routes* and return ``ClassifiedRoute`` objects.

    Routing rules
    -------------
    - auth_check_status in {"ABSENT", "UNCERTAIN"} → send to LLM, attach
      LlmClassification result.
    - auth_check_status == "PRESENT" → pass through unchanged with
      llm_classification=None (no LLM call, no log files written).

    Parameters
    ----------
    routes:
        List of ``StaticAnalysisResult`` objects from the static analysis
        layer.

    Returns
    -------
    list[ClassifiedRoute]
        One entry per input route, preserving order.
    """
    total = len(routes)
    to_classify = sum(1 for r in routes if r.auth_check_status in _CLASSIFY_STATUSES)

    logger.info(
        "classify_all_routes: %d total routes, %d will be sent to LLM (%d skipped: PRESENT)",
        total,
        to_classify,
        total - to_classify,
    )

    classified: list[ClassifiedRoute] = []
    llm_index = 0

    for i, route in enumerate(routes, start=1):
        if route.auth_check_status in _CLASSIFY_STATUSES:
            llm_index += 1
            logger.info(
                "[%d/%d] LLM classifying route %s (auth=%s) [LLM call %d/%d]",
                i,
                total,
                route.route_id,
                route.auth_check_status,
                llm_index,
                to_classify,
            )
            llm_result = classify_route(route)
            classified.append(
                ClassifiedRoute(
                    **route.model_dump(),
                    llm_classification=llm_result,
                )
            )
        else:
            # PRESENT — no LLM call needed.
            logger.info(
                "[%d/%d] Skipping route %s (auth=PRESENT)",
                i,
                total,
                route.route_id,
            )
            classified.append(
                ClassifiedRoute(
                    **route.model_dump(),
                    llm_classification=None,
                )
            )

    vulnerable_count = sum(
        1
        for r in classified
        if r.llm_classification and r.llm_classification.is_vulnerable
    )
    logger.info(
        "classify_all_routes complete: %d classified, %d is_vulnerable=True",
        len(classified),
        vulnerable_count,
    )

    return classified
