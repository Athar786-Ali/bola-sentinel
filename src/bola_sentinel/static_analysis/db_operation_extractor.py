"""
Database operation extractor for route handler code.

Returns DbOperation instances (from the canonical schema) by scanning handler
source code for ORM calls and raw SQL patterns.  Coverage spans the most
common Python and JavaScript ORM libraries used in REST APIs at risk of BOLA.

Supported patterns
------------------
Python:
  SQLAlchemy ORM:
    session.add(obj)               → CREATE
    session.delete(obj)            → DELETE
    db.session.delete(obj)         → DELETE
    .update({…}) / .update(field=) → UPDATE
    .filter(…).delete()            → DELETE
    .filter(…).update({…})         → UPDATE
    db.session.get(Model, id)      → READ (included — state may change later)
    Model.query.get(id)            → READ

  Raw SQL strings:
    INSERT INTO …                  → CREATE
    UPDATE … SET …                 → UPDATE
    DELETE FROM …                  → DELETE
    SELECT … (only if followed by state-change context)

JavaScript:
  Sequelize:
    Model.create(…)                → CREATE
    instance.destroy()             → DELETE
    Model.destroy({where:…})       → DELETE
    instance.update(…)             → UPDATE
    Model.update(…,{where:…})      → UPDATE
    Model.findByPk(…)              → READ
    Model.findOne(…)               → READ

  Mongoose:
    Model.findByIdAndDelete(…)     → DELETE
    Model.findOneAndDelete(…)      → DELETE
    Model.findByIdAndUpdate(…)     → UPDATE
    Model.findOneAndUpdate(…)      → UPDATE
    Model.findByIdAndRemove(…)     → DELETE
    new Model(…).save()            → CREATE
    Model.create(…)                → CREATE

Design note: POST routes with zero detected DB operations are NOT dropped
by this module.  The caller (analyzer.py) preserves them as-is with an
empty db_operations list, because many real BOLA-vulnerable POST actions
(e.g. archive/cancel) delegate to a queue or microservice without a
direct ORM call visible in the handler.
"""

from __future__ import annotations

import re
from typing import NamedTuple

from bola_sentinel.models.schemas import DbOperation

# ── Pattern table ──────────────────────────────────────────────────────────


class _Pattern(NamedTuple):
    operation_type: str   # "READ" | "CREATE" | "UPDATE" | "DELETE"
    regex: re.Pattern[str]


# --------------------------------------------------------------------------
# Python patterns
# --------------------------------------------------------------------------
_PY_PATTERNS: list[_Pattern] = [
    # SQLAlchemy — session.add / db.session.add → CREATE
    _Pattern(
        "CREATE",
        re.compile(
            r"""(?:db\.)?session\s*\.\s*add\s*\(""",
            re.IGNORECASE,
        ),
    ),
    # SQLAlchemy — bulk insert / insert(Model)
    _Pattern(
        "CREATE",
        re.compile(
            r"""db\.session\.execute\s*\(\s*insert\s*\(""",
            re.IGNORECASE,
        ),
    ),
    # SQLAlchemy — session.delete → DELETE
    _Pattern(
        "DELETE",
        re.compile(
            r"""(?:db\.)?session\s*\.\s*delete\s*\(""",
            re.IGNORECASE,
        ),
    ),
    # SQLAlchemy — .filter(…).delete() → DELETE
    _Pattern(
        "DELETE",
        re.compile(
            r"""\.filter\s*\([^)]*\)\s*\.delete\s*\(""",
            re.IGNORECASE,
        ),
    ),
    # SQLAlchemy — .filter(…).update({…}) → UPDATE
    _Pattern(
        "UPDATE",
        re.compile(
            r"""\.filter\s*\([^)]*\)\s*\.update\s*\(""",
            re.IGNORECASE,
        ),
    ),
    # SQLAlchemy — direct .update({…}) on a query/relationship → UPDATE
    _Pattern(
        "UPDATE",
        re.compile(
            r"""\.update\s*\(\s*\{""",
            re.IGNORECASE,
        ),
    ),
    # SQLAlchemy — setattr + session.commit pattern (attribute mutation → UPDATE)
    _Pattern(
        "UPDATE",
        re.compile(
            r"""setattr\s*\(\s*\w+\s*,\s*['"]""",
            re.IGNORECASE,
        ),
    ),
    # SQLAlchemy — db.session.get / Model.query.get → READ
    _Pattern(
        "READ",
        re.compile(
            r"""(?:(?:db\.)?session\.get\s*\(|\.query\.get\s*\(|\.get\s*\(\s*\w+\s*,)""",
            re.IGNORECASE,
        ),
    ),
    # SQLAlchemy — .first() / .one() / .all() → READ
    _Pattern(
        "READ",
        re.compile(
            r"""\.(?:first|one|one_or_none|scalar|all)\s*\(\s*\)""",
            re.IGNORECASE,
        ),
    ),
    # Raw SQL — INSERT
    _Pattern(
        "CREATE",
        re.compile(
            r"""INSERT\s+INTO\s+\w+""",
            re.IGNORECASE,
        ),
    ),
    # Raw SQL — UPDATE
    _Pattern(
        "UPDATE",
        re.compile(
            r"""UPDATE\s+\w+\s+SET\s+""",
            re.IGNORECASE,
        ),
    ),
    # Raw SQL — DELETE
    _Pattern(
        "DELETE",
        re.compile(
            r"""DELETE\s+FROM\s+\w+""",
            re.IGNORECASE,
        ),
    ),
    # Raw SQL — SELECT
    _Pattern(
        "READ",
        re.compile(
            r"""SELECT\s+.+?\s+FROM\s+\w+""",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
]

# --------------------------------------------------------------------------
# JavaScript patterns
# --------------------------------------------------------------------------
_JS_PATTERNS: list[_Pattern] = [
    # Sequelize / Mongoose — .create({…}) → CREATE
    _Pattern(
        "CREATE",
        re.compile(
            r"""\.\s*create\s*\(""",
            re.IGNORECASE,
        ),
    ),
    # Mongoose — new Model(…).save() → CREATE
    _Pattern(
        "CREATE",
        re.compile(
            r"""\.save\s*\(\s*\)""",
            re.IGNORECASE,
        ),
    ),
    # Sequelize — instance.destroy() / Model.destroy({where:…}) → DELETE
    _Pattern(
        "DELETE",
        re.compile(
            r"""\.destroy\s*\(""",
            re.IGNORECASE,
        ),
    ),
    # Mongoose — findByIdAndDelete / findOneAndDelete / findByIdAndRemove
    _Pattern(
        "DELETE",
        re.compile(
            r"""\.find(?:ById(?:And(?:Delete|Remove))|OneAnd(?:Delete|Remove))\s*\(""",
            re.IGNORECASE,
        ),
    ),
    # Sequelize / Mongoose — .update({…}) → UPDATE
    _Pattern(
        "UPDATE",
        re.compile(
            r"""\.update\s*\(""",
            re.IGNORECASE,
        ),
    ),
    # Mongoose — findByIdAndUpdate / findOneAndUpdate
    _Pattern(
        "UPDATE",
        re.compile(
            r"""\.find(?:ById|One)AndUpdate\s*\(""",
            re.IGNORECASE,
        ),
    ),
    # Sequelize / Mongoose — findByPk / findById / findOne / findAll → READ
    _Pattern(
        "READ",
        re.compile(
            r"""\.find(?:ByPk|ById|One|All|Many)\s*\(""",
            re.IGNORECASE,
        ),
    ),
    # Mongoose / Sequelize — .findById( → READ
    _Pattern(
        "READ",
        re.compile(
            r"""\.findById\s*\(""",
            re.IGNORECASE,
        ),
    ),
    # Raw SQL (template literals or strings) — INSERT / UPDATE / DELETE / SELECT
    _Pattern(
        "CREATE",
        re.compile(r"""INSERT\s+INTO\s+\w+""", re.IGNORECASE),
    ),
    _Pattern(
        "UPDATE",
        re.compile(r"""UPDATE\s+\w+\s+SET\s+""", re.IGNORECASE),
    ),
    _Pattern(
        "DELETE",
        re.compile(r"""DELETE\s+FROM\s+\w+""", re.IGNORECASE),
    ),
    _Pattern(
        "READ",
        re.compile(r"""SELECT\s+.+?\s+FROM\s+\w+""", re.IGNORECASE | re.DOTALL),
    ),
]

_LANGUAGE_PATTERNS: dict[str, list[_Pattern]] = {
    "python": _PY_PATTERNS,
    "javascript": _JS_PATTERNS,
}

# How many characters around the match to include as the snippet.
_SNIPPET_CONTEXT = 80


def _extract_snippet(code: str, match: re.Match[str]) -> str:
    """
    Return a short, single-line context snippet centred on the regex match.
    """
    start = max(0, match.start() - 20)
    end = min(len(code), match.end() + _SNIPPET_CONTEXT)
    raw = code[start:end]
    # Collapse whitespace / newlines for readability.
    snippet = re.sub(r"\s+", " ", raw).strip()
    return snippet[:200]  # hard cap to avoid bloated output


# ── Public API ─────────────────────────────────────────────────────────────


def extract_db_operations(
    handler_code: str,
    language: str,
) -> list[DbOperation]:
    """
    Scan *handler_code* for ORM / SQL patterns and return DbOperation objects.

    A route with *zero* detected operations is NOT an error — the caller
    must preserve such routes (particularly POST routes) rather than
    dropping them, as they may delegate to queues or micro-services.

    Parameters
    ----------
    handler_code:
        Full source text of the route handler.
    language:
        ``"python"`` or ``"javascript"``.

    Returns
    -------
    list[DbOperation]
        Deduplicated list of operations, preserving first-occurrence order.
    """
    patterns = _LANGUAGE_PATTERNS.get(language, [])
    if not patterns:
        return []

    seen_snippets: set[str] = set()
    ops: list[DbOperation] = []

    for patt in patterns:
        for m in patt.regex.finditer(handler_code):
            snippet = _extract_snippet(handler_code, m)
            # Deduplicate by snippet content (handles overlapping patterns).
            if snippet not in seen_snippets:
                seen_snippets.add(snippet)
                ops.append(
                    DbOperation(operation_type=patt.operation_type, snippet=snippet)  # type: ignore[arg-type]
                )

    return ops
