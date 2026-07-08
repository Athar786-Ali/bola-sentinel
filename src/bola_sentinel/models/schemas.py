"""
Shared Pydantic schemas for the bola-sentinel pipeline.

IMPORTANT: These definitions are the single source of truth for the entire
project.  Every layer (static_analysis, llm_reasoning, dynamic_verification,
evaluation) imports from this module.  Do NOT redefine or rename fields in
downstream modules — extend via subclassing if needed.

Schema hierarchy
----------------
ObjectIdParam        – one object-id parameter extracted from a route
DbOperation          – one database operation found in a route handler
StaticAnalysisResult – output of the static analysis layer (one per route)
  └─ ClassifiedRoute – extends with LlmClassification (LLM reasoning layer)
       └─ VerifiedRoute – extends with VerificationResult (dynamic layer)

StandardizedFinding  – flat, report-level shape used in final JSON output
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ── Layer 1: Static Analysis ───────────────────────────────────────────────


class ObjectIdParam(BaseModel):
    """
    An object-identifying parameter extracted from a route definition.

    Example: the ``{orderId}`` path segment in ``GET /orders/{orderId}``.
    """

    name: str = Field(
        ...,
        description="Parameter name as it appears in the route (e.g. 'orderId').",
    )
    location: Literal["path", "query", "body"] = Field(
        ...,
        description="Where the parameter is carried: path segment, query string, or request body.",
    )


class DbOperation(BaseModel):
    """
    A single database / ORM operation identified inside a route handler.
    """

    operation_type: Literal["READ", "CREATE", "UPDATE", "DELETE"] = Field(
        ...,
        description="CRUD category of the operation.",
    )
    snippet: str = Field(
        ...,
        description="Raw source code snippet containing the DB operation call.",
    )


class StaticAnalysisResult(BaseModel):
    """
    Output produced by the static analysis layer for a single API route.

    This is the primary input to the LLM reasoning layer.
    """

    route_id: str = Field(
        ...,
        description=(
            "Stable, unique identifier for this route, e.g. "
            "'GET /api/users/{userId}/orders'."
        ),
    )
    http_method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] = Field(
        ...,
        description="HTTP verb of the route.",
    )
    route_path: str = Field(
        ...,
        description="URL path pattern including parameter placeholders.",
    )
    file_path: str = Field(
        ...,
        description="Absolute or repo-relative path to the source file.",
    )
    line_number: int = Field(
        ...,
        ge=1,
        description="Line number where the route handler begins.",
    )
    language: Literal["python", "javascript"] = Field(
        ...,
        description="Source language of the route handler.",
    )
    object_id_params: list[ObjectIdParam] = Field(
        default_factory=list,
        description="Object-identifying parameters found in this route.",
    )
    db_operations: list[DbOperation] = Field(
        default_factory=list,
        description="Database operations found inside the handler body.",
    )
    auth_check_status: Literal["PRESENT", "ABSENT", "UNCERTAIN"] = Field(
        ...,
        description=(
            "Static determination of whether an object-level authorization "
            "check is present in the handler.  UNCERTAIN means the static "
            "analyser could not make a confident determination."
        ),
    )
    handler_code_raw: str = Field(
        ...,
        description="Full raw source of the route handler function / method.",
    )


# ── Layer 2: LLM Reasoning ─────────────────────────────────────────────────


class LlmClassification(BaseModel):
    """
    Structured output returned by the local LLM for a single route.

    The LLM is asked to reason about the *authorization model* of the object
    referenced by the route and whether the absence of an ownership check
    creates a BOLA/IDOR vulnerability.
    """

    applicable_model: Literal["OWNERSHIP", "MEMBERSHIP", "HIERARCHICAL", "STATUS", "NONE"] = Field(
        ...,
        description=(
            "Which authorization model applies to the object accessed by "
            "this route.  NONE means no object-level access control is "
            "relevant (e.g., public resource)."
        ),
    )
    is_vulnerable: bool = Field(
        ...,
        description="True if the LLM concludes the route is likely BOLA-vulnerable.",
    )
    confidence: Literal["HIGH", "MEDIUM", "LOW"] = Field(
        ...,
        description="LLM's self-reported confidence in the classification.",
    )
    explanation: str = Field(
        ...,
        description="Free-text chain-of-thought reasoning from the LLM.",
    )
    suggested_test_description: str = Field(
        ...,
        description=(
            "Human-readable description of the dynamic verification probe "
            "the LLM suggests, e.g. 'Access victim's order with attacker token'."
        ),
    )
    requires_two_users: bool = Field(
        ...,
        description=(
            "True if the suggested verification requires two distinct user "
            "accounts (attacker + victim).  False if a single account is "
            "sufficient (e.g., enumeration-only tests)."
        ),
    )


class ClassifiedRoute(StaticAnalysisResult):
    """
    A StaticAnalysisResult enriched with LLM classification.

    Produced by the LLM reasoning layer; consumed by the dynamic
    verification layer.
    """

    llm_classification: LlmClassification | None = Field(
        default=None,
        description=(
            "LLM classification result.  None if LLM reasoning was skipped "
            "(e.g., auth_check_status == PRESENT with high confidence)."
        ),
    )


# ── Layer 3: Dynamic Verification ─────────────────────────────────────────


class VerificationResult(BaseModel):
    """
    Evidence collected by live HTTP probing of a ClassifiedRoute.

    Dynamic verification is the primary false-positive reduction mechanism:
    a route is only confirmed vulnerable when live evidence is captured.
    """

    verification_status: Literal[
        "CONFIRMED_VULNERABLE", "NOT_VULNERABLE", "INCONCLUSIVE"
    ] = Field(
        ...,
        description=(
            "Outcome of the dynamic probe.  CONFIRMED_VULNERABLE requires "
            "positive evidence (e.g., 200 OK with victim data).  "
            "INCONCLUSIVE is used when the probe could not be executed or "
            "when the response is ambiguous."
        ),
    )
    http_status_received: int | None = Field(
        default=None,
        description="HTTP status code returned by the server for the probe request.",
    )
    response_body_evidence: str | None = Field(
        default=None,
        description=(
            "Relevant excerpt of the response body that supports the "
            "verification_status conclusion."
        ),
    )
    object_state_changed: bool | None = Field(
        default=None,
        description=(
            "True if a write operation visibly changed object state under "
            "the victim's account.  None if a state-change check was not "
            "applicable or not attempted."
        ),
    )
    attacker_user_id: str | None = Field(
        default=None,
        description="Identifier of the user account used as the attacker.",
    )
    victim_object_id: str | None = Field(
        default=None,
        description="Identifier of the object belonging to the victim.",
    )
    url_used: str | None = Field(
        default=None,
        description="Exact URL that was probed.",
    )
    notes: str = Field(
        default="",
        description="Additional context, error messages, or caveats.",
    )


class VerifiedRoute(ClassifiedRoute):
    """
    A ClassifiedRoute enriched with dynamic verification evidence.

    This is the final per-route artefact before the evaluation layer.
    """

    verification: VerificationResult | None = Field(
        default=None,
        description=(
            "Dynamic verification result.  None if verification was skipped "
            "(e.g., route was not classified as vulnerable by the LLM)."
        ),
    )


# ── Layer 4: Evaluation / Reporting ───────────────────────────────────────


class StandardizedFinding(BaseModel):
    """
    Flat, report-level shape used in final JSON output files written to
    results/.

    This is what evaluation metrics are computed against when compared with
    ground-truth JSON files in datasets/ground_truth/.
    """

    route_id: str = Field(
        ...,
        description="Route identifier matching StaticAnalysisResult.route_id.",
    )
    vulnerability_type: str = Field(
        default="BOLA",
        description="Vulnerability class.  Always 'BOLA' for this project.",
    )
    confidence: str = Field(
        ...,
        description="Propagated from LlmClassification.confidence.",
    )
    verification_status: str = Field(
        ...,
        description="Propagated from VerificationResult.verification_status.",
    )
    evidence: str = Field(
        ...,
        description=(
            "Human-readable summary of evidence: LLM explanation + key "
            "dynamic verification details."
        ),
    )
    authorization_model: str = Field(
        ...,
        description="Propagated from LlmClassification.applicable_model.",
    )
