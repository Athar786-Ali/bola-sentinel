"""
Verification orchestrator — top-level entry point for Phase 3.

Loads test users, filters to LLM-flagged-vulnerable routes, dispatches
execution, and assembles VerifiedRoute objects.
"""

from __future__ import annotations

import logging
from pathlib import Path

from bola_sentinel.models.schemas import ClassifiedRoute, VerificationResult, VerifiedRoute

import httpx

from .executor import execute_verification
from .test_user_loader import load_test_users

logger = logging.getLogger(__name__)


def _refresh_tokens(test_users: dict, base_url: str) -> dict:
    """
    Re-authenticate test users to obtain fresh JWTs.

    If a user entry contains ``login_email``, ``login_password``, and
    ``login_url``, this function POSTs to the login endpoint and replaces
    ``auth_header`` with the new token.

    Falls back silently to the existing token if login fails — the
    verification will then get 401s as before.
    """
    for user_key in ("user_a", "user_b"):
        user = test_users.get(user_key, {})
        email = user.get("login_email")
        password = user.get("login_password")
        login_url = user.get("login_url")

        if not (email and password and login_url):
            continue

        url = base_url.rstrip("/") + login_url
        try:
            resp = httpx.post(
                url,
                json={"email": email, "password": password},
                timeout=10.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                # Support Juice Shop format: {"authentication": {"token": "..."}}
                token = None
                if "authentication" in data:
                    token = data["authentication"].get("token")
                elif "token" in data:
                    token = data["token"]
                elif "access_token" in data:
                    token = data["access_token"]

                if token:
                    test_users[user_key]["auth_header"] = f"Bearer {token}"
                    logger.info(
                        "Token refresh for %s: success (via %s)",
                        user_key, login_url,
                    )
                else:
                    logger.warning(
                        "Token refresh for %s: login returned 200 but no token found in response",
                        user_key,
                    )
            else:
                logger.warning(
                    "Token refresh for %s: login returned HTTP %d — using existing token",
                    user_key, resp.status_code,
                )
        except Exception as exc:
            logger.warning(
                "Token refresh for %s failed: %s — using existing token",
                user_key, exc,
            )

    return test_users


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

    # ── Token refresh ─────────────────────────────────────────────────
    # If login credentials are provided, re-authenticate to get fresh
    # JWTs.  This prevents expired-token failures during long benchmark
    # runs where tokens issued at setup time may have expired.
    test_users = _refresh_tokens(test_users, base_url)

    # ── Pre-flight reachability check ─────────────────────────────────
    # Verify the target application is actually reachable BEFORE running
    # any probes.  Fail fast with a clear message instead of silently
    # marking every route INCONCLUSIVE.
    try:
        preflight = httpx.get(base_url, timeout=10.0, follow_redirects=True)
        logger.info(
            "Pre-flight check: %s responded with HTTP %d — target is reachable.",
            base_url,
            preflight.status_code,
        )
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        logger.error(
            "Pre-flight check FAILED: target app at %s is not reachable (%s). "
            "Start the target application before running verification.",
            base_url,
            exc,
        )
        # Return all routes — vulnerable ones get INCONCLUSIVE, others pass through.
        fail_result = VerificationResult(
            verification_status="INCONCLUSIVE",
            notes=(
                f"Target app at {base_url} is not reachable — "
                f"start it before running verify. Error: {exc}"
            ),
        )
        return [
            VerifiedRoute(
                **r.model_dump(),
                verification=fail_result
                if (r.llm_classification and r.llm_classification.is_vulnerable)
                else None,
            )
            for r in classified_routes
        ]

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

        try:
            vr = execute_verification(route, test_users, base_url)
        except Exception as exc:
            logger.error(
                "[%d/%d] Unexpected error verifying route %s: %s — marking INCONCLUSIVE",
                i,
                len(classified_routes),
                route.route_id,
                exc,
            )
            vr = VerificationResult(
                verification_status="INCONCLUSIVE",
                notes=f"Unexpected error during verification: {type(exc).__name__}: {exc}",
            )

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
