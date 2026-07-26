"""
Attack request builder for the dynamic verification layer.

Constructs a fully-formed HTTP attack probe from a ClassifiedRoute and the
test-user configuration.  The attack always uses:

  • **Attacker**: user_a's ``auth_header``
  • **Victim target**: an object ID from user_b's ``owned_object_ids``

Resource-type matching strategy
--------------------------------
The route path is split into segments.  Each static (non-parameter) segment
is compared against the keys in user_b's ``owned_object_ids`` (case-
insensitive, and supporting singular/plural variants).  The first match wins.

Path-parameter substitution
----------------------------
Three template styles are handled:
  • Flask/Werkzeug  ``<int:project_id>`` or ``<project_id>``
  • FastAPI / OpenAPI  ``{orderId}``
  • Express / path-to-regexp  ``:orderId``
"""

from __future__ import annotations

import logging
import re
from typing import Any

from bola_sentinel.models.schemas import ClassifiedRoute

logger = logging.getLogger(__name__)

# ── Path-template substitution ─────────────────────────────────────────────

# Ordered list of (pattern, extractor) for recognising path parameters.
_PARAM_PATTERNS: list[tuple[re.Pattern[str], re.Pattern[str]]] = [
    # FastAPI / OpenAPI: {orderId}
    (re.compile(r"\{(\w+)\}"), re.compile(r"\{(\w+)\}")),
    # Flask with type: <int:project_id>  or bare <project_id>
    (re.compile(r"<(?:\w+:)?(\w+)>"), re.compile(r"<(?:\w+:)?(\w+)>")),
    # Express: :orderId (must not match URL scheme if present, but we operate on path only)
    (re.compile(r":(\w+)"), re.compile(r":(\w+)")),
]


def _extract_param_names(segment: str) -> list[str]:
    """Return parameter names found in a path *segment*."""
    names: list[str] = []
    for detect_re, _ in _PARAM_PATTERNS:
        for m in detect_re.finditer(segment):
            names.append(m.group(1))
    return names


def _is_param_segment(segment: str) -> bool:
    """Return True if the segment is a path parameter placeholder."""
    return bool(
        re.search(r"\{.+\}", segment)
        or re.search(r"<[^>]+>", segment)
        or re.search(r":(\w+)", segment)
    )


def _substitute_param(path: str, param_name: str, value: str) -> str:
    """
    Replace ONE named parameter in *path* with *value*, handling all three
    template styles.
    """
    # FastAPI / OpenAPI: {param_name}
    path = re.sub(re.escape("{" + param_name + "}"), value, path)
    # Flask with optional type prefix: <int:param_name> or <param_name>
    path = re.sub(r"<(?:\w+:)?" + re.escape(param_name) + r">", value, path)
    # Express: :param_name
    path = re.sub(r":(" + re.escape(param_name) + r")\b", value, path)
    return path


# ── Resource-type matching ─────────────────────────────────────────────────

def _normalise(name: str) -> str:
    """Lower-case and strip trailing 's' for singular/plural matching."""
    return name.lower().rstrip("s")


def _match_resource(
    route_path: str,
    owned_object_ids: dict[str, list[str]],
) -> tuple[str | None, str | None, str | None]:
    """
    Find the resource type and associated parameter name in *route_path*.

    Returns
    -------
    tuple[resource_key, param_name, victim_object_id]
        All three are None if no match is found.
    """
    segments = [s for s in route_path.split("/") if s]

    # Build normalised lookup of owned_object_ids keys.
    normalised_owned: dict[str, str] = {
        _normalise(k): k for k in owned_object_ids
    }

    for i, segment in enumerate(segments):
        if _is_param_segment(segment):
            continue  # skip parameter segments

        norm_seg = _normalise(segment)
        if norm_seg not in normalised_owned:
            logger.debug(
                "[DEBUG-MATCH] Route path: %s. Tried keyword '%s' (normalised to '%s'). No match in test_users.json keys: %s",
                route_path, segment, norm_seg, list(normalised_owned.keys())
            )
            continue

        resource_key = normalised_owned[norm_seg]
        ids = owned_object_ids.get(resource_key, [])
        if not ids:
            continue

        victim_id = ids[0]  # pick first available victim object

        # Find the ID parameter: look at the next segment after the resource.
        param_name: str | None = None
        if i + 1 < len(segments) and _is_param_segment(segments[i + 1]):
            names = _extract_param_names(segments[i + 1])
            if names:
                param_name = names[0]
                
        logger.debug(
            "[DEBUG-MATCH] SUCCESS! Route path: %s -> matched segment '%s' to test_user key '%s'. ID param: %s",
            route_path, segment, resource_key, param_name
        )

        return resource_key, param_name, victim_id

    return None, None, None


# ── Public API ─────────────────────────────────────────────────────────────


def build_attack_request(
    route: ClassifiedRoute,
    test_users: dict,
    base_url: str,
) -> dict[str, Any] | None:
    """
    Construct an HTTP attack probe for *route*.

    The attacker is user_a (their token).  The target object belongs to
    user_b.

    Parameters
    ----------
    route:
        A ``ClassifiedRoute`` with ``is_vulnerable=True``.
    test_users:
        Validated dict loaded by ``load_test_users()``.
    base_url:
        Base URL of the target application, e.g. ``"http://localhost:3000"``.

    Returns
    -------
    dict | None
        Dict with keys ``url``, ``method``, ``headers``, ``attacker_user_id``,
        ``victim_object_id``.  Returns ``None`` if no matching object type
        was found (a warning is logged with manual-mapping instructions).
    """
    user_a = test_users["user_a"]
    user_b = test_users["user_b"]
    owned = user_b.get("owned_object_ids", {})

    resource_key, param_name, victim_id = _match_resource(route.route_path, owned)

    if resource_key is None or victim_id is None:
        logger.warning(
            "build_attack_request: no matching object type for route %s "
            "(path=%r).  Available resource types in test_users.user_b.owned_object_ids: %s.  "
            "Add a matching resource key manually and re-run verification.",
            route.route_id,
            route.route_path,
            list(owned.keys()),
        )
        return None

    # Substitute victim object id into the path template.
    resolved_path = route.route_path
    if param_name:
        resolved_path = _substitute_param(resolved_path, param_name, victim_id)

    # If any parameter placeholders remain (e.g. a second nested param),
    # replace them with "1" as a best-effort placeholder and log a note.
    remaining = re.findall(r"\{(\w+)\}|<(?:\w+:)?(\w+)>|(?<!/):(\w+)", resolved_path)
    if remaining:
        remaining_names = [next(g for g in groups if g) for groups in remaining]
        logger.warning(
            "Route %s has unresolved path parameters after substitution: %s.  "
            "Using '1' as placeholder — consider adding more owned_object_ids entries.",
            route.route_id,
            remaining_names,
        )
        for pname in remaining_names:
            resolved_path = _substitute_param(resolved_path, pname, "1")

    url = base_url.rstrip("/") + resolved_path

    # Parse the auth_header value: it may be in "HeaderName: value" format
    # (e.g. "Cookie: authToken=xxx" or "Bearer xxx").
    auth_value = user_a["auth_header"]
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if ": " in auth_value and not auth_value.startswith("Bearer "):
        # Full header format: "Cookie: authToken=xxx" or "Authorization: Bearer xxx"
        header_name, header_val = auth_value.split(": ", 1)
        headers[header_name] = header_val
    else:
        # Just a value — assume it's an Authorization header
        headers["Authorization"] = auth_value

    return {
        "url": url,
        "method": route.http_method,
        "headers": headers,
        "attacker_user_id": str(user_a["user_id"]),
        "victim_object_id": str(victim_id),
        "resource_type": resource_key,
    }
