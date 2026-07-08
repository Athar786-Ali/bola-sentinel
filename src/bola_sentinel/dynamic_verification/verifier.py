"""
Verification orchestrator — top-level entry point for Phase 3.

Loads test users, filters to LLM-flagged-vulnerable routes, dispatches
execution, and assembles VerifiedRoute objects.
"""

from __future__ import annotations

import logging
from pathlib import Path

from bola_sentinel.models.schemas import ClassifiedRoute, VerificationResult, VerifiedRoute

from .executor import execute_verification
from .test_user_loader import load_test_users

logger = logging.getLogger(__name__)


def verify_all_routes(
    classified_routes: list[ClassifiedRoute],
    base_url: str,
    test_users_path: str = "test_users.json",
) -> list[VerifiedRoute]:
    """
    Run dynamic verification for every route where the LLM flagged
    ``is_vulnerable=True``.  All other routes pass through with
    ``verification=None``.

    Parameters
    ----------
    classified_routes:
        Output from the LLM reasoning layer.
    base_url:
        Base URL of the target application, e.g. ``"http://localhost:3000"``.
    test_users_path:
        Path to ``test_users.json``.

    Returns
    -------
    list[VerifiedRoute]
        One entry per input route, in the same order.
    """
    test_users = load_test_users(test_users_path)

    to_verify = [
        r for r in classified_routes
        if r.llm_classification is not None and r.llm_classification.is_vulnerable
    ]
    skip_count = len(classified_routes) - len(to_verify)

    logger.info(
        "verify_all_routes: %d total routes, %d to verify, %d skipping "
        "(is_vulnerable=False or llm_classification=None)",
        len(classified_routes),
        len(to_verify),
        skip_count,
    )

    verified: list[VerifiedRoute] = []

    for i, route in enumerate(classified_routes, start=1):
        if route.llm_classification is None or not route.llm_classification.is_vulnerable:
            logger.info(
                "[%d/%d] Skipping route %s (not LLM-flagged as vulnerable)",
                i,
                len(classified_routes),
                route.route_id,
            )
            verified.append(VerifiedRoute(**route.model_dump(), verification=None))
            continue

        logger.info(
            "[%d/%d] Verifying route %s (auth=%s, model=%s)",
            i,
            len(classified_routes),
            route.route_id,
            route.auth_check_status,
            route.llm_classification.applicable_model if route.llm_classification else "—",
        )

        vr = execute_verification(route, test_users, base_url)

        logger.info(
            "  → verdict: %s  (state_changed=%s, http=%s)",
            vr.verification_status,
            vr.object_state_changed,
            vr.http_status_received,
        )

        verified.append(VerifiedRoute(**route.model_dump(), verification=vr))

    # Summary stats
    confirmed = sum(
        1 for r in verified
        if r.verification and r.verification.verification_status == "CONFIRMED_VULNERABLE"
    )
    not_vuln = sum(
        1 for r in verified
        if r.verification and r.verification.verification_status == "NOT_VULNERABLE"
    )
    inconclusive = sum(
        1 for r in verified
        if r.verification and r.verification.verification_status == "INCONCLUSIVE"
    )

    logger.info(
        "verify_all_routes complete: CONFIRMED_VULNERABLE=%d  NOT_VULNERABLE=%d  INCONCLUSIVE=%d",
        confirmed,
        not_vuln,
        inconclusive,
    )

    return verified
