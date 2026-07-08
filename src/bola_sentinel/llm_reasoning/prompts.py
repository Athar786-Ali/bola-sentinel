"""
Prompt builders for the bola-sentinel LLM reasoning layer.

Separating prompt text from classifier logic makes it easy to:
  - A/B test prompt variants without changing business logic
  - Review exact prompts from log files independently of code
  - Extend or translate prompts for new model families

No LLM calls are made in this module — pure string construction only.
"""

from __future__ import annotations

from bola_sentinel.models.schemas import StaticAnalysisResult

# ── System prompt ──────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are a security expert specializing in Broken Object-Level Authorization \
(BOLA) vulnerabilities. You will be given static-analysis context for a \
single API route and must classify it against four authorization models:

1. OWNERSHIP - object should only be accessed by the user who created it \
(1:1 or 1:n user-to-object relationship)
2. MEMBERSHIP - object accessible by a specific group of users (many-to-many, \
e.g. forum/team members)
3. HIERARCHICAL - object's parent has an ownership/membership rule and the \
object inherits it (e.g. comments belonging to a post)
4. STATUS - object has a lifecycle state (open/closed/draft/archived) that \
gates which actions are allowed
5. NONE - none of the above models apply, or this looks like a false positive

Respond ONLY with valid JSON, no other text, in exactly this schema:
{
  "applicable_model": "OWNERSHIP" | "MEMBERSHIP" | "HIERARCHICAL" | "STATUS" | "NONE",
  "is_vulnerable": true or false,
  "confidence": "HIGH" | "MEDIUM" | "LOW",
  "explanation": "<one paragraph reasoning, reference the specific code>",
  "suggested_test_description": "<concrete description of what a verification test should attempt to prove this vulnerability>",
  "requires_two_users": true or false
}\
"""


def build_system_prompt() -> str:
    """
    Return the fixed system-role prompt for BOLA classification.

    The system prompt is the same for every route — it sets the model's
    persona and mandates the exact JSON output schema.
    """
    return _SYSTEM_PROMPT


# ── User prompt ────────────────────────────────────────────────────────────


def build_user_prompt(route: StaticAnalysisResult) -> str:
    """
    Build the per-route user prompt by rendering all static-analysis fields
    into clearly labelled sections.

    The handler source code is included in full so the model can reason
    about the actual logic, not just metadata.

    Parameters
    ----------
    route:
        A ``StaticAnalysisResult`` produced by the static analysis layer.

    Returns
    -------
    str
        The complete user-turn text to send to the model.
    """
    # ── Object-id params section ───────────────────────────────────────
    if route.object_id_params:
        params_lines = "\n".join(
            f"  - name={p.name!r}, location={p.location!r}"
            for p in route.object_id_params
        )
    else:
        params_lines = "  (none detected)"

    # ── DB operations section ──────────────────────────────────────────
    if route.db_operations:
        db_lines = "\n".join(
            f"  - [{op.operation_type}] {op.snippet}"
            for op in route.db_operations
        )
    else:
        db_lines = "  (none detected — route may delegate to a queue/service)"

    prompt = f"""\
=== ROUTE CONTEXT FOR BOLA CLASSIFICATION ===

Route ID:             {route.route_id}
HTTP Method:          {route.http_method}
Route Path:           {route.route_path}
Source File:          {route.file_path}
Line Number:          {route.line_number}
Language:             {route.language}
Auth Check Status:    {route.auth_check_status}

--- Object-ID Parameters ---
{params_lines}

--- Database / ORM Operations ---
{db_lines}

--- Full Handler Source Code ---
```{route.language}
{route.handler_code_raw}
```

=== TASK ===
Based on the context above, determine:
1. Which BOLA authorization model (OWNERSHIP/MEMBERSHIP/HIERARCHICAL/STATUS/NONE) \
applies to the object referenced by this route.
2. Whether the absence of an object-level ownership check (auth_check_status=\
{route.auth_check_status!r}) makes this route BOLA-vulnerable.
3. Your confidence level and concrete reasoning referencing the code above.
4. A specific dynamic verification test that would confirm or deny the vulnerability.

Remember: auth_check_status={route.auth_check_status!r} means the static \
analyser {"found no ownership check" if route.auth_check_status == "ABSENT" \
else "found a user-identity expression but could not confirm it binds to this object"}.

Respond ONLY with the JSON schema specified. No preamble, no explanation outside \
the JSON.\
"""
    return prompt
