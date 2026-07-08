"""
Object-ID parameter detector.

Extracts ObjectIdParam instances from route path templates and handler
source code.  Returns instances of the canonical ObjectIdParam schema
imported from bola_sentinel.models.schemas — no re-definition.

Detection strategy
------------------
1. Route-path parsing (location="path"):
   • Flask/Werkzeug: ``<int:post_id>``, ``<uuid:token>``, ``<id>``
   • FastAPI / OpenAPI: ``{orderId}``, ``{project_id}``
   • Express / path-to-regexp: ``:id``, ``:orderId``
   All three styles are tried on every route path regardless of the
   declared language, because mixed-framework codebases exist.

2. Handler code scanning (location="body" | "query"):
   • Python Flask: ``request.json.get("id")``, ``request.args.get("user_id")``
   • Python FastAPI: Pydantic body model access ``body.item_id``,
     direct param names declared in function signature are covered by
     the path parser above.
   • JavaScript Express: ``req.body.userId``, ``req.query.id``,
     ``req.params.orderId``

De-duplication: a parameter name + location combination is only emitted once.
"""

from __future__ import annotations

import re

from bola_sentinel.models.schemas import ObjectIdParam

# ── Route-path parameter patterns ─────────────────────────────────────────

# Flask/Werkzeug: <int:post_id> or <post_id>
_FLASK_PATH_PARAM_RE = re.compile(r"<(?:\w+:)?(\w+)>")

# FastAPI / OpenAPI brace style: {orderId}
_FASTAPI_PATH_PARAM_RE = re.compile(r"\{(\w+)\}")

# Express colon-prefix style: :orderId
_EXPRESS_PATH_PARAM_RE = re.compile(r":(\w+)")

# ── Handler code scanning: body params ────────────────────────────────────

# Python Flask: request.json.get("param_name") or request.json["param_name"]
_PY_BODY_PARAM_RE = re.compile(
    r"""request\s*\.\s*(?:json|get_json\s*\(\s*\))\s*(?:\.get\s*\(\s*['"](\w+)['"]\s*|\[\s*['"](\w+)['"]\s*\])""",
    re.IGNORECASE,
)

# Python Flask: request.form.get("param") / request.form["param"]
_PY_FORM_PARAM_RE = re.compile(
    r"""request\s*\.\s*form\s*(?:\.get\s*\(\s*['"](\w+)['"]\s*|\[\s*['"](\w+)['"]\s*\])""",
    re.IGNORECASE,
)

# Python Flask/FastAPI: request.args.get("param") / request.query_params["param"]
_PY_QUERY_PARAM_RE = re.compile(
    r"""request\s*\.\s*(?:args|query_params)\s*(?:\.get\s*\(\s*['"](\w+)['"]\s*|\[\s*['"](\w+)['"]\s*\])""",
    re.IGNORECASE,
)

# JavaScript Express: req.body.<param>
_JS_BODY_PARAM_RE = re.compile(r"req\s*\.\s*body\s*\.\s*(\w+)")

# JavaScript Express: req.query.<param>
_JS_QUERY_PARAM_RE = re.compile(r"req\s*\.\s*query\s*\.\s*(\w+)")

# JavaScript Express: req.params.<param> (path param reference in handler body)
_JS_PATH_PARAM_REF_RE = re.compile(r"req\s*\.\s*params\s*\.\s*(\w+)")

# Words that are common enough to not be meaningful object-id params.
_COMMON_NOISE: frozenset[str] = frozenset(
    {
        "page",
        "limit",
        "offset",
        "sort",
        "order",
        "format",
        "version",
        "v",
        "lang",
        "locale",
        "token",
        "password",
        "email",
        "username",
        "name",
        "title",
        "description",
        "content",
        "body",
        "text",
        "message",
        "status",
        "type",
        "action",
        "event",
    }
)

# Heuristic: names that look like IDs (contain "id", "pk", "key", "uuid",
# "slug" as a sub-word, or end with common ID suffixes).
_ID_LIKE_RE = re.compile(
    r"(?i)(?:^id$|_id$|id_|pk$|_pk$|_key$|key_id$|uuid|_uid$|slug|_ref$|_no$|_num$|number$|code$|^fk_)",
)


def _looks_like_id(name: str) -> bool:
    """
    Return True if *name* looks like an object-identifying parameter.

    This heuristic prevents flooding the result with every request body
    field.  We only promote fields that pattern-match as identifiers.
    """
    if name.lower() in _COMMON_NOISE:
        return False
    return bool(_ID_LIKE_RE.search(name))


def _collect_path_params(route_path: str) -> list[ObjectIdParam]:
    """
    Extract path-segment parameters from *route_path* using all three
    known path-template syntaxes (Flask, FastAPI, Express).
    """
    seen: set[str] = set()
    params: list[ObjectIdParam] = []

    for pattern in (
        _FLASK_PATH_PARAM_RE,
        _FASTAPI_PATH_PARAM_RE,
        _EXPRESS_PATH_PARAM_RE,
    ):
        for m in pattern.finditer(route_path):
            name = m.group(1)
            if name not in seen:
                seen.add(name)
                params.append(ObjectIdParam(name=name, location="path"))

    return params


def _collect_code_params(
    handler_code: str,
    language: str,
) -> list[ObjectIdParam]:
    """
    Scan *handler_code* for body / query parameter accesses and return
    ObjectIdParam instances for ID-like names.
    """
    seen: set[tuple[str, str]] = set()
    params: list[ObjectIdParam] = []

    def _add(name: str, location: str) -> None:
        key = (name, location)
        if key not in seen and _looks_like_id(name):
            seen.add(key)
            params.append(ObjectIdParam(name=name, location=location))  # type: ignore[arg-type]

    if language == "python":
        for m in _PY_BODY_PARAM_RE.finditer(handler_code):
            _add(m.group(1) or m.group(2), "body")
        for m in _PY_FORM_PARAM_RE.finditer(handler_code):
            _add(m.group(1) or m.group(2), "body")
        for m in _PY_QUERY_PARAM_RE.finditer(handler_code):
            _add(m.group(1) or m.group(2), "query")

    elif language == "javascript":
        for m in _JS_BODY_PARAM_RE.finditer(handler_code):
            _add(m.group(1), "body")
        for m in _JS_QUERY_PARAM_RE.finditer(handler_code):
            _add(m.group(1), "query")
        # req.params.X references are path params — skip; they're already
        # covered by _collect_path_params.

    return params


# ── Public API ─────────────────────────────────────────────────────────────


def detect_object_id_params(
    route_path: str,
    handler_code: str,
    language: str,
) -> list[ObjectIdParam]:
    """
    Detect object-identifying parameters for a single route.

    Parameters
    ----------
    route_path:
        The URL path template for the route, e.g. ``/orders/{orderId}/cancel``.
    handler_code:
        Full source text of the route handler function.
    language:
        ``"python"`` or ``"javascript"``.

    Returns
    -------
    list[ObjectIdParam]
        Deduplicated list of object-id parameters, path params first.
    """
    path_params = _collect_path_params(route_path)
    # Track names already found in the path to avoid body/query duplicates.
    path_param_names = {p.name for p in path_params}

    code_params = [
        p
        for p in _collect_code_params(handler_code, language)
        if p.name not in path_param_names
    ]

    return path_params + code_params
