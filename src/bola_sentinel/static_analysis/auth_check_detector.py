"""
Authorization-check detector for route handler source code.

Goal: determine — statically — whether a route handler verifies that the
authenticated user *owns* or *may access* the specific object referenced by
the route's object-id parameter(s).

Return values
-------------
"PRESENT"
    A conditional or query filter that binds an *object-id parameter* to an
    *authenticated-user identifier* was found.  Both halves must be present:
    a user-identity expression (current_user.id, req.user.id, …) AND a
    comparison / WHERE-filter that also involves the object-id.

"ABSENT"
    No user-identity expression was found in the handler at all.

"UNCERTAIN"
    A user-identity expression was found, but it does not appear to be
    directly compared or filtered against the object-id.  The handler may
    do RBAC (role-check only) rather than object-level ownership.

Design rationale
----------------
Pure-regex static analysis cannot reach the accuracy of a full type-checker,
so we intentionally err toward "UNCERTAIN" rather than toward "ABSENT" when
ambiguity exists.  The LLM reasoning layer (Phase 2) is responsible for
resolving UNCERTAIN cases.
"""

from __future__ import annotations

import re

from bola_sentinel.models.schemas import ObjectIdParam

# ── User-identity expression patterns ─────────────────────────────────────

# Python identity expressions (resolved to the authenticated user's ID).
_PY_USER_ID_EXPRS: list[re.Pattern[str]] = [
    re.compile(r"current_user\s*\.\s*id", re.IGNORECASE),
    re.compile(r"current_user\s*\.\s*_id", re.IGNORECASE),
    re.compile(r"g\s*\.\s*user(?:_id|\.id)?", re.IGNORECASE),
    re.compile(r"request\s*\.\s*user\s*\.\s*(?:id|_id)", re.IGNORECASE),
    re.compile(r"session\s*\[\s*['\"]user_id['\"]\s*\]", re.IGNORECASE),
    re.compile(r"session\s*\.get\s*\(\s*['\"]user_id['\"]", re.IGNORECASE),
    re.compile(r"get_jwt_identity\s*\(\s*\)", re.IGNORECASE),
    re.compile(r"token_data\s*\[\s*['\"](?:sub|user_id|id)['\"]", re.IGNORECASE),
    # Flask-Login / Flask-Security custom attributes
    re.compile(r"login_manager\s*\.\s*current_user\s*\.\s*id", re.IGNORECASE),
    # SQLAlchemy ORM queried user id
    re.compile(r"current_user\s*\.\s*user_id", re.IGNORECASE),
]

# JavaScript (Express) identity expressions.
_JS_USER_ID_EXPRS: list[re.Pattern[str]] = [
    re.compile(r"req\s*\.\s*user\s*\.\s*(?:id|_id|userId)", re.IGNORECASE),
    re.compile(r"req\s*\.\s*session\s*\.\s*(?:userId|user_id|uid)", re.IGNORECASE),
    re.compile(r"req\s*\.\s*userId", re.IGNORECASE),
    re.compile(r"decodedToken\s*\.\s*(?:id|_id|userId)", re.IGNORECASE),
    re.compile(r"jwt\s*\.\s*verify\s*\([^)]+\)\s*\.\s*(?:id|userId)", re.IGNORECASE),
]

_LANG_USER_EXPRS: dict[str, list[re.Pattern[str]]] = {
    "python": _PY_USER_ID_EXPRS,
    "javascript": _JS_USER_ID_EXPRS,
}

# ── Ownership-binding patterns ─────────────────────────────────────────────
# These look for explicit comparisons or ORM filters that join the user
# identity with an object attribute.

# Python: == / != comparisons between current_user.id and any identifier,
# or .filter(…user_id…current_user…) style ORM calls.
_PY_OWNERSHIP_PATTERNS: list[re.Pattern[str]] = [
    # Direct equality/inequality comparison involving user identity
    re.compile(
        r"(?:current_user\s*\.\s*(?:id|_id)\s*(?:==|!=)\s*\w+|"
        r"\w+\s*(?:==|!=)\s*current_user\s*\.\s*(?:id|_id))",
        re.IGNORECASE,
    ),
    # g.user / request.user comparison
    re.compile(
        r"(?:g\s*\.\s*user(?:_id|\.id)?\s*(?:==|!=)\s*\w+|"
        r"\w+\s*(?:==|!=)\s*g\s*\.\s*user(?:_id|\.id)?)",
        re.IGNORECASE,
    ),
    # session["user_id"] comparison
    re.compile(
        r"session\s*\[\s*['\"]user_id['\"]\s*\]\s*(?:==|!=)",
        re.IGNORECASE,
    ),
    # SQLAlchemy .filter containing both an owner field and user identity
    re.compile(
        r"\.filter\s*\([^)]*(?:owner|user)_?id[^)]*(?:current_user|g\.user|request\.user)[^)]*\)",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"\.filter\s*\([^)]*(?:current_user|g\.user|request\.user)[^)]*(?:owner|user)_?id[^)]*\)",
        re.IGNORECASE | re.DOTALL,
    ),
    # filter_by(user_id=current_user.id)
    re.compile(
        r"filter_by\s*\([^)]*user_?id\s*=\s*current_user\s*\.",
        re.IGNORECASE,
    ),
    # Abort / raise on mismatch (indicates ownership was checked)
    re.compile(
        r"abort\s*\(\s*403\s*\)",
        re.IGNORECASE,
    ),
    re.compile(
        r"HTTPException\s*\(\s*status_code\s*=\s*403",
        re.IGNORECASE,
    ),
]

# JavaScript ownership patterns.
_JS_OWNERSHIP_PATTERNS: list[re.Pattern[str]] = [
    # Direct comparison
    re.compile(
        r"req\s*\.\s*user\s*\.\s*(?:id|_id|userId)\s*(?:===?|!==?)\s*\w+",
        re.IGNORECASE,
    ),
    re.compile(
        r"\w+\s*(?:===?|!==?)\s*req\s*\.\s*user\s*\.\s*(?:id|_id|userId)",
        re.IGNORECASE,
    ),
    # .toString() comparison (Mongoose ObjectId)
    re.compile(
        r"\.toString\s*\(\s*\)\s*(?:===?|!==?)\s*req\s*\.\s*user",
        re.IGNORECASE,
    ),
    re.compile(
        r"req\s*\.\s*user[^.]*\.toString\s*\(\s*\)\s*(?:===?|!==?)",
        re.IGNORECASE,
    ),
    # Mongoose query with userId filter
    re.compile(
        r"\.findOne\s*\(\s*\{[^}]*user(?:Id|_id)\s*:\s*req\s*\.\s*user",
        re.IGNORECASE | re.DOTALL,
    ),
    # res.status(403) send/json (indicates check happened)
    re.compile(
        r"res\s*\.\s*status\s*\(\s*403\s*\)",
        re.IGNORECASE,
    ),
    # createError(403)
    re.compile(
        r"createError\s*\(\s*403\s*\)",
        re.IGNORECASE,
    ),
]

_LANG_OWNERSHIP: dict[str, list[re.Pattern[str]]] = {
    "python": _PY_OWNERSHIP_PATTERNS,
    "javascript": _JS_OWNERSHIP_PATTERNS,
}


def _has_user_identity(code: str, language: str) -> bool:
    """Return True if *code* contains any user-identity expression."""
    for pattern in _LANG_USER_EXPRS.get(language, []):
        if pattern.search(code):
            return True
    return False


def _has_ownership_binding(
    code: str,
    language: str,
    object_id_params: list[ObjectIdParam],
) -> bool:
    """
    Return True if an ownership-binding pattern is found in *code* that
    relates to at least one of the *object_id_params*.

    Strategy: first check the broad ownership patterns; if any match,
    additionally verify that at least one object-id param name appears in
    a window of text around the match (to avoid triggering on unrelated
    auth checks in the same handler).
    """
    object_id_names = {p.name for p in object_id_params}

    for pattern in _LANG_OWNERSHIP.get(language, []):
        for m in pattern.finditer(code):
            # If no object-id params are known, any ownership check counts.
            if not object_id_names:
                return True
            # Widen the context window around the match and check if any
            # object-id name appears nearby.
            window_start = max(0, m.start() - 200)
            window_end = min(len(code), m.end() + 200)
            window = code[window_start:window_end]
            if any(name in window for name in object_id_names):
                return True

    return False


# ── Public API ─────────────────────────────────────────────────────────────


def detect_auth_check(
    handler_code: str,
    object_id_params: list[ObjectIdParam],
    language: str = "python",
) -> str:
    """
    Statically assess whether *handler_code* contains an object-level
    authorization check.

    Parameters
    ----------
    handler_code:
        Full source text of the route handler (decorators + body).
    object_id_params:
        Object-id parameters detected for this route (used to verify that
        ownership checks reference the same object, not a different one).
    language:
        ``"python"`` or ``"javascript"``.

    Returns
    -------
    str
        ``"PRESENT"`` | ``"ABSENT"`` | ``"UNCERTAIN"``
    """
    has_user = _has_user_identity(handler_code, language)

    if not has_user:
        return "ABSENT"

    has_binding = _has_ownership_binding(handler_code, language, object_id_params)

    if has_binding:
        return "PRESENT"

    # User identity is referenced but not clearly bound to the object-id.
    return "UNCERTAIN"
