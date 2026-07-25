"""
Benchmark dataset schema for bola-sentinel.

DatasetEntry is the authoritative source-of-truth record for each
benchmark entry.  It stores the human-curated metadata about a known
BOLA/IDOR vulnerability (or confirmed-safe route) in a target application.

IMPORTANT — route_id contract
------------------------------
Phase 1's static analyzer is the ONLY authoritative source of route_id
values.  Do NOT reconstruct or guess route_ids in this module.

Workflow:
  1. Run `bola-sentinel analyze <source_path>` on the target application.
  2. Open results/static_analysis_results.json.
  3. Find the route you want to label and copy its exact "route_id" value.
  4. Pass that value as the `route_id` argument to `to_ground_truth_entry`.

If the analyzer format ever changes, running analyze again and updating
ground_truth files is the correct repair — not patching this schema.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ReviewMetadata(BaseModel):
    """Structured review metadata for the ground-truth entry."""
    reviewer: str = Field(..., description="Name or handle of the reviewer")
    review_date: str = Field(..., description="ISO-8601 Timestamp of the review")
    confidence: Literal["High", "Medium", "Low"] = Field(..., description="Reviewer confidence in this ground truth")


class DatasetEntry(BaseModel):
    """
    One benchmark record: a single known-vulnerable or known-safe route.

    Fill these in from the CVE report, patch commit, or manual code review.
    Never set expected_verdict based on the tool's own output.
    """

    application_name: str = Field(
        ...,
        description="Short identifier matching an entry in app_registry.json, "
                    "e.g. 'juice_shop' or 'cve_2024_27564'.",
    )
    vulnerability_name: str = Field(
        ...,
        description="Human-readable name, e.g. 'Order BOLA via /api/Orders/:id'.",
    )
    cve_id: str | None = Field(
        default=None,
        description="CVE identifier if applicable, e.g. 'CVE-2024-12345'. "
                    "Null for non-CVE findings.",
    )
    cwe_id: str | None = Field(
        default=None,
        description="CWE identifier, e.g. 'CWE-284: Improper Access Control'.",
    )
    owasp_category: str | None = Field(
        default=None,
        description="OWASP API Top 10 category, e.g. 'API1:2023 BOLA'.",
    )
    route: str = Field(
        ...,
        description="Route path as it appears in the source code, "
                    "e.g. '/api/Orders/:id' or '/api/users/{userId}/profile'.",
    )
    method: Literal["POST", "PUT", "PATCH", "DELETE"] = Field(
        ...,
        description="HTTP method of the vulnerable route.",
    )
    vulnerable_version: str = Field(
        ...,
        description="Earliest known-vulnerable version, e.g. '14.3.1'.",
    )
    patched_version: str | None = Field(
        default=None,
        description="Version where the fix was released.  Null if unpatched.",
    )
    expected_verdict: bool = Field(
        ...,
        description=(
            "Ground truth: True = this route IS vulnerable to BOLA/IDOR. "
            "False = this route is safe (used as a true-negative). "
            "MUST come from the CVE report, patch commit, or manual review — "
            "never from the tool's own output."
        ),
    )
    source: Literal["juice_shop", "cve", "advisory", "manual"] = Field(
        ...,
        description="Evidence source for expected_verdict.",
    )
    source_reference: str | None = Field(
        default=None,
        description="Link to the vulnerable file/line in GitHub.",
    )
    evidence: str | None = Field(
        default=None,
        description="Specific code snippet or payload proving the vulnerability.",
    )
    notes: str = Field(
        default="",
        description="Free-form evidence notes: link to CVE, commit hash, etc.",
    )
    review_metadata: ReviewMetadata | None = Field(
        default=None,
        description="Metadata detailing who established this ground truth.",
    )


def to_ground_truth_entry(entry: DatasetEntry, route_id: str) -> dict:
    """
    Convert a DatasetEntry into the exact ground_truth.json format consumed
    by Phase 4's evaluation module.

    Parameters
    ----------
    entry:
        A populated DatasetEntry.
    route_id:
        The EXACT route_id string from Phase 1's analyzer output.
    """
    # Build a standardized notes field incorporating new evidence and references
    notes_parts = [f"[{entry.vulnerability_name}]"]
    if entry.notes:
        notes_parts.append(entry.notes)
    if entry.cwe_id:
        notes_parts.append(f"CWE: {entry.cwe_id}")
    if entry.owasp_category:
        notes_parts.append(f"OWASP: {entry.owasp_category}")
    if entry.source_reference:
        notes_parts.append(f"Source: {entry.source_reference}")
        
    return {
        "route_id": route_id,
        "actually_vulnerable": entry.expected_verdict,
        "source": entry.source,
        "cve_id": entry.cve_id,
        "notes": " | ".join(notes_parts).strip(),
    }
