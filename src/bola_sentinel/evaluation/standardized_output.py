"""
Standardized-finding builder for the evaluation layer.

Produces a list of ``StandardizedFinding`` objects — one per
CONFIRMED_VULNERABLE route — using the fixed schema defined in Phase 0.
These are the findings that go into the report and into any downstream
tooling.  Every field must be present: no Optional shortcuts here.
"""

from __future__ import annotations

import logging

from bola_sentinel.models.schemas import StandardizedFinding, VerifiedRoute
from .stage_classifiers import get_final_system_verdict

logger = logging.getLogger(__name__)


def build_standardized_findings(
    verified_routes: list[VerifiedRoute],
) -> list[StandardizedFinding]:
    """
    Build ``StandardizedFinding`` objects for every route whose final-system
    verdict is True (CONFIRMED_VULNERABLE).

    Parameters
    ----------
    verified_routes:
        Output from the dynamic verification layer.

    Returns
    -------
    list[StandardizedFinding]
        One finding per CONFIRMED_VULNERABLE route, sorted by route_id.
    """
    findings: list[StandardizedFinding] = []

    for route in verified_routes:
        if not get_final_system_verdict(route):
            continue

        # Both llm_classification and verification are guaranteed non-None
        # for any route that passes get_final_system_verdict.
        llm = route.llm_classification
        ver = route.verification

        finding = StandardizedFinding(
            route_id=route.route_id,
            vulnerability_type="BOLA",
            confidence=llm.confidence if llm else "LOW",  # type: ignore[union-attr]
            verification_status=ver.verification_status if ver else "INCONCLUSIVE",  # type: ignore[union-attr]
            evidence=ver.response_body_evidence if ver else None,  # type: ignore[union-attr]
            authorization_model=(
                llm.applicable_model if llm else "NONE"  # type: ignore[union-attr]
            ),
        )
        findings.append(finding)
        logger.debug("Standardized finding: %s", route.route_id)

    findings.sort(key=lambda f: f.route_id)
    logger.info(
        "build_standardized_findings: %d CONFIRMED_VULNERABLE findings from %d routes",
        len(findings),
        len(verified_routes),
    )
    return findings
