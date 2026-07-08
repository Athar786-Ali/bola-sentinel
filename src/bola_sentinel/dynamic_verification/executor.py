"""
Verification executor — the core of the dynamic verification layer.

Orchestrates: attack-request building → before-snapshot → HTTP probe →
after-snapshot → multi-signal verdict → evidence logging.

Verdict decision logic
----------------------
The system NEVER relies on HTTP status codes alone.  Full decision matrix:

┌─────────────────┬───────────────────┬──────────────────────────────────┐
│  Status code    │  states_differ()  │  Verdict                         │
├─────────────────┼───────────────────┼──────────────────────────────────┤
│  401 / 403      │  any              │  NOT_VULNERABLE (request denied) │
│  404            │  any              │  NOT_VULNERABLE (obj not found)  │
│  200/201/204    │  True             │  CONFIRMED_VULNERABLE ★ strong   │
│  200/201/204    │  None + no denial │  CONFIRMED_VULNERABLE ★ weak*    │
│  200/201/204    │  False            │  NOT_VULNERABLE (no-op response) │
│  other          │  any              │  INCONCLUSIVE                    │
└─────────────────┴───────────────────┴──────────────────────────────────┘

★ weak: state-check was not available; verdict relies on status + body only.
  This is explicitly flagged in notes and object_state_changed=None.

This split is the primary research evidence that Phase 4 measures.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from bola_sentinel.models.schemas import ClassifiedRoute, VerificationResult

from .attack_builder import build_attack_request
from .evidence_logger import log_verification_attempt
from .state_checker import (
    capture_object_state,
    find_read_endpoint,
    states_differ,
)

logger = logging.getLogger(__name__)

# HTTP status codes that unambiguously mean the server rejected the request.
_DENIED_STATUSES: frozenset[int] = frozenset({401, 403})

# HTTP status codes that indicate success (request was accepted).
_SUCCESS_STATUSES: frozenset[int] = frozenset({200, 201, 202, 204})

# Timeout for the attack probe itself.
_ATTACK_TIMEOUT = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)

# Words in a response body that signal denial even on a 2xx status.
_DENIAL_TERMS_RE = re.compile(
    r"\b(forbidden|unauthorized|not\s+allowed|permission\s+denied|"
    r"access\s+denied|insufficient\s+permissions?|not\s+authorized|"
    r"you\s+don.t\s+have|you\s+do\s+not\s+have)\b",
    re.IGNORECASE,
)


def _body_looks_like_denial(body: str) -> bool:
    return bool(_DENIAL_TERMS_RE.search(body[:2000]))


def execute_verification(
    route: ClassifiedRoute,
    test_users: dict[str, Any],
    base_url: str,
    client: httpx.Client | None = None,
) -> VerificationResult:
    """
    Execute a full BOLA verification probe for *route*.

    Parameters
    ----------
    route:
        A ``ClassifiedRoute`` with ``llm_classification.is_vulnerable=True``.
    test_users:
        Validated dict from ``load_test_users()``.
    base_url:
        Base URL of the target application.
    client:
        Optional httpx.Client for testing / connection reuse.  If None,
        a fresh client is created and closed after each call.

    Returns
    -------
    VerificationResult
        Fully populated result including evidence fields.
    """
    _owns_client = client is None
    _client = client or httpx.Client(timeout=_ATTACK_TIMEOUT)

    # ── Step 1: Build attack request ───────────────────────────────────
    attack = build_attack_request(route, test_users, base_url)
    if attack is None:
        result = VerificationResult(
            verification_status="INCONCLUSIVE",
            notes=(
                "No matching object type found in test_users.user_b.owned_object_ids "
                "for route path. Add resource IDs to test_users.json and re-run."
            ),
        )
        log_verification_attempt(
            route_id=route.route_id,
            attack_request={},
            response_status=0,
            response_body="",
            state_before=None,
            state_after=None,
            final_verdict="INCONCLUSIVE",
        )
        if _owns_client:
            _client.close()
        return result

    victim_id = attack["victim_object_id"]
    attacker_id = attack["attacker_user_id"]

    # ── Step 2: Before-snapshot (best-effort) ──────────────────────────
    # Use the VICTIM's auth header for state reads so we confirm the object
    # exists and belongs to the victim.
    victim_headers = {"Authorization": test_users["user_b"]["auth_header"]}

    # Resolve the path for state reading: strip template syntax from the URL.
    attack_url_path = "/" + "/".join(attack["url"].split("/")[3:])
    read_url = find_read_endpoint(attack_url_path, victim_id, base_url)
    state_before: dict | None = None
    if read_url:
        state_before = capture_object_state(read_url, victim_headers, _client)
        if state_before is None:
            logger.debug(
                "execute_verification: before-snapshot unavailable for route %s "
                "(read_url=%s) — state check will be skipped",
                route.route_id,
                read_url,
            )

    # ── Step 3: Send attack probe ──────────────────────────────────────
    response_status: int
    response_body: str
    try:
        resp = _client.request(
            method=attack["method"],
            url=attack["url"],
            headers=attack["headers"],
        )
        response_status = resp.status_code
        response_body = resp.text
    except httpx.ConnectError as exc:
        result = VerificationResult(
            verification_status="INCONCLUSIVE",
            attacker_user_id=attacker_id,
            victim_object_id=victim_id,
            url_used=attack["url"],
            notes=f"Target application unreachable: {exc}",
        )
        log_verification_attempt(
            route_id=route.route_id,
            attack_request=attack,
            response_status=0,
            response_body="",
            state_before=state_before,
            state_after=None,
            final_verdict="INCONCLUSIVE",
        )
        if _owns_client:
            _client.close()
        return result
    except httpx.TimeoutException as exc:
        result = VerificationResult(
            verification_status="INCONCLUSIVE",
            attacker_user_id=attacker_id,
            victim_object_id=victim_id,
            url_used=attack["url"],
            notes=f"Request timed out: {exc}",
        )
        log_verification_attempt(
            route_id=route.route_id,
            attack_request=attack,
            response_status=0,
            response_body="",
            state_before=state_before,
            state_after=None,
            final_verdict="INCONCLUSIVE",
        )
        if _owns_client:
            _client.close()
        return result

    # ── Step 4: After-snapshot (best-effort) ───────────────────────────
    state_after: dict | None = None
    if read_url and state_before is not None:
        state_after = capture_object_state(read_url, victim_headers, _client)

    # ── Step 5: Multi-signal verdict ───────────────────────────────────
    verdict: str
    state_changed: bool | None
    notes_parts: list[str] = []

    if response_status in _DENIED_STATUSES:
        verdict = "NOT_VULNERABLE"
        state_changed = None
        notes_parts.append(f"Request explicitly denied with HTTP {response_status}.")

    elif response_status == 404:
        verdict = "NOT_VULNERABLE"
        state_changed = None
        notes_parts.append("Object not found under attacker's context (HTTP 404).")

    elif response_status in _SUCCESS_STATUSES:
        diff = states_differ(state_before, state_after)

        if diff is True:
            # Strongest evidence: object actually changed.
            verdict = "CONFIRMED_VULNERABLE"
            state_changed = True
            notes_parts.append(
                "STRONG EVIDENCE: Object state changed after attacker probe "
                "(before≠after snapshot)."
            )
        elif diff is False:
            # Request accepted but object is unchanged — likely a no-op.
            verdict = "NOT_VULNERABLE"
            state_changed = False
            notes_parts.append(
                "Request returned 2xx but object state is unchanged — "
                "likely a no-op or server-side guard not reflected in status."
            )
        else:
            # diff is None — no baseline available. Fall back to body analysis.
            state_changed = None
            if _body_looks_like_denial(response_body):
                verdict = "NOT_VULNERABLE"
                notes_parts.append(
                    "HTTP 2xx but response body contains denial language — "
                    "treating as not vulnerable."
                )
            else:
                verdict = "CONFIRMED_VULNERABLE"
                notes_parts.append(
                    "WEAK EVIDENCE: HTTP 2xx with no denial language. "
                    "State check was unavailable — verdict relies on status+body only. "
                    "Manual confirmation recommended."
                )
    else:
        verdict = "INCONCLUSIVE"
        state_changed = None
        notes_parts.append(f"Unexpected HTTP status {response_status}.")

    notes = " ".join(notes_parts)

    # ── Step 6: Log full evidence ──────────────────────────────────────
    log_verification_attempt(
        route_id=route.route_id,
        attack_request=attack,
        response_status=response_status,
        response_body=response_body,
        state_before=state_before,
        state_after=state_after,
        final_verdict=verdict,
    )

    # ── Step 7: Return populated VerificationResult ────────────────────
    result = VerificationResult(
        verification_status=verdict,
        http_status_received=response_status,
        response_body_evidence=response_body[:500] if response_body else None,
        object_state_changed=state_changed,
        attacker_user_id=attacker_id,
        victim_object_id=victim_id,
        url_used=attack["url"],
        notes=notes,
    )

    if _owns_client:
        _client.close()

    return result
