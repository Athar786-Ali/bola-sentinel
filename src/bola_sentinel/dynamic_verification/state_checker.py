"""
Object-state checker for the dynamic verification layer.

Provides best-effort before/after state snapshots to confirm that an attack
probe actually mutated the victim's object — the strongest evidence of a
real BOLA vulnerability.

Design constraints
------------------
• State capture MUST NOT block a verification if the target app has no
  readable GET endpoint.  All functions return None on failure instead of
  raising.
• Failures are logged as warnings so the researcher sees them without the
  pipeline crashing.
• The ``states_differ`` result is a tri-state (True / False / None) that
  feeds into the executor's multi-signal decision logic.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Status codes that mean "the object is gone" after an attack.
_GONE_STATUSES: frozenset[int] = frozenset({404, 410})

# Timeout for state-capture GET requests (separate from attack timeout).
_STATE_TIMEOUT = httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=5.0)

# Regex to strip trailing action-word segments from a path
# (e.g. /cancel, /archive, /publish, /delete, /restore).
_ACTION_SUFFIX_RE = re.compile(
    r"/(cancel|archive|publish|delete|restore|approve|reject|close|open|"
    r"activate|deactivate|lock|unlock|submit|complete|start|stop|pause|resume)"
    r"$",
    re.IGNORECASE,
)


def find_read_endpoint(route_path: str, victim_object_id: str, base_url: str) -> str | None:
    """
    Construct a best-effort GET URL for the same resource that *route_path*
    targets.

    Strategy
    --------
    1. Strip trailing action words (``/cancel``, ``/archive``, …).
    2. Ensure the remaining path contains exactly the victim object id (the
       last path parameter is the one that was already substituted before
       this call — ``route_path`` here is the *resolved* URL path, not the
       template).

    Parameters
    ----------
    route_path:
        **Resolved** URL path with the victim object id already substituted,
        e.g. ``"/orders/21/cancel"``.
    victim_object_id:
        The victim's object id string, used to verify it appears in the path.
    base_url:
        Base URL of the target application.

    Returns
    -------
    str | None
        A full URL suitable for a GET request, or None if a sensible GET
        endpoint cannot be inferred.
    """
    # Strip action suffixes.
    cleaned = _ACTION_SUFFIX_RE.sub("", route_path)
    if cleaned == route_path and route_path.endswith("/" + victim_object_id):
        # Path ends with the id already — use as-is.
        cleaned = route_path

    # Sanity-check: the cleaned path should contain the victim id.
    if victim_object_id not in cleaned:
        logger.debug(
            "find_read_endpoint: victim_object_id %r not found in cleaned path %r — skipping",
            victim_object_id,
            cleaned,
        )
        return None

    return base_url.rstrip("/") + cleaned


def capture_object_state(
    read_url: str,
    headers: dict[str, str],
    client: httpx.Client | None = None,
) -> dict[str, Any] | None:
    """
    Send a GET request to *read_url* and return the JSON response body.

    Parameters
    ----------
    read_url:
        Full URL of the resource to read.
    headers:
        Request headers (typically the **victim's** auth header so we can
        confirm the object still exists from the victim's perspective).
    client:
        Optional httpx.Client to use (for testing / connection reuse).

    Returns
    -------
    dict | None
        Parsed JSON body, or None on any failure.
    """
    _client = client or httpx.Client(timeout=_STATE_TIMEOUT)
    try:
        resp = _client.get(read_url, headers=headers)
        if resp.status_code in _GONE_STATUSES:
            # Object doesn't exist — encode this as a distinguishable sentinel.
            return {"_bola_sentinel_status": resp.status_code, "_gone": True}
        if resp.status_code == 200:
            try:
                return dict(resp.json())
            except Exception:
                # Non-JSON 200 body — return raw text wrapped.
                return {"_bola_sentinel_raw": resp.text[:500]}
        logger.debug(
            "capture_object_state: unexpected status %d for %s",
            resp.status_code,
            read_url,
        )
        return None
    except Exception as exc:
        logger.debug("capture_object_state failed for %s: %s", read_url, exc)
        return None
    finally:
        if client is None:
            _client.close()


def states_differ(
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
) -> bool | None:
    """
    Compare *before* and *after* state dicts for meaningful differences.

    Return values
    -------------
    True
        The object demonstrably changed (e.g. a field value mutated, or the
        object was deleted / disappeared).
    False
        Both snapshots exist and are equivalent — the request was a no-op.
    None
        Comparison was not possible (one or both snapshots unavailable).
    """
    if before is None or after is None:
        return None

    # If the object is now gone (404/410) it was deleted — state changed.
    if after.get("_gone") and not before.get("_gone"):
        return True

    # Both snapshots exist: do a deep equality check ignoring timestamp fields.
    _NOISE_KEYS: frozenset[str] = frozenset(
        {"updatedAt", "updated_at", "lastModified", "last_modified",
         "timestamp", "ts", "_ts", "etag", "ETag", "version", "__v"}
    )

    def _strip_noise(d: dict) -> dict:
        return {k: v for k, v in d.items() if k not in _NOISE_KEYS and not k.startswith("_bola_sentinel")}

    stripped_before = _strip_noise(before)
    stripped_after = _strip_noise(after)

    if stripped_before == stripped_after:
        return False

    # Check that at least one non-trivial field actually changed (guard
    # against servers that always return a fresh "nonce" or "requestId").
    meaningful_keys = set(stripped_before) | set(stripped_after)
    for key in meaningful_keys:
        if stripped_before.get(key) != stripped_after.get(key):
            return True

    return False
