"""
Stage verdict functions for the three-stage progressive evaluation.

Each function represents what a particular pipeline stage would flag as
vulnerable.  They are used as ``verdict_fn`` arguments to
``compute_confusion_matrix`` so the metrics layer stays independent of the
classification logic.

Stage framing
-------------
These are NOT three independent tools.  They are three progressive checkpoints
of the same pipeline:

  Stage 1 – Static Analysis Only
      Labels a route vulnerable iff the AST heuristic found no ownership
      check (auth_check_status == "ABSENT").  Highest recall, highest FPR.

  Stage 2 – Static Analysis + LLM Reasoning
      Only routes that the LLM also classified as vulnerable.  The LLM step
      reduces false positives from Stage 1 at the cost of some inference time.

  Stage 3 – Static Analysis + LLM + Dynamic Verification (Final System)
      Only routes where the live HTTP probe confirmed the vulnerability
      (CONFIRMED_VULNERABLE).  The strongest, evidence-backed verdict.

The progressive FP reduction from Stage 1 → 2 → 3 is the paper's central
research claim, quantified in ``comparator.py``.
"""

from __future__ import annotations

from bola_sentinel.models.schemas import VerifiedRoute


def get_static_only_verdict(route: VerifiedRoute) -> bool:
    """
    Stage 1: Static Analysis Only.

    Returns True iff the static analyser found no ownership check
    (``auth_check_status == "ABSENT"``).

    This mirrors what a pure static-analysis scanner would report with no
    further filtering.  It intentionally has the highest false-positive rate
    among the three stages.
    """
    return route.auth_check_status == "ABSENT"


def get_static_plus_llm_verdict(route: VerifiedRoute) -> bool:
    """
    Stage 2: Static Analysis + LLM Reasoning.

    Returns True iff the LLM classified the route as vulnerable.

    Semantics: the static layer first narrows the candidate set to
    ABSENT/UNCERTAIN routes; the LLM then makes a per-route binary call.
    Routes with ``llm_classification is None`` (PRESENT routes that were
    never sent to the LLM) return False.
    """
    return (
        route.llm_classification is not None
        and route.llm_classification.is_vulnerable is True
    )


def get_final_system_verdict(route: VerifiedRoute) -> bool:
    """
    Stage 3: Static Analysis + LLM + Dynamic Verification (Final System).

    Returns True iff the live HTTP probe produced a CONFIRMED_VULNERABLE
    verdict.  This is the strongest, evidence-backed answer: the system
    actually sent an attacker request and observed an access control failure.

    Routes that were not probed (``verification is None``) or produced
    INCONCLUSIVE / NOT_VULNERABLE results return False.
    """
    return (
        route.verification is not None
        and route.verification.verification_status == "CONFIRMED_VULNERABLE"
    )
