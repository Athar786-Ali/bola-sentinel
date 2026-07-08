"""
Progressive three-stage comparator.

The core claim of this research is that adding LLM reasoning and then
dynamic verification to a static-analysis baseline progressively reduces
false positives.  This module computes the evidence for that claim.

The output dict is both serialized to ``results/evaluation_metrics.json``
and used to generate ``results/EVALUATION_REPORT.md``.
"""

from __future__ import annotations

import logging

from bola_sentinel.models.schemas import VerifiedRoute

from .metrics import compute_confusion_matrix, compute_metrics_from_confusion
from .stage_classifiers import (
    get_final_system_verdict,
    get_static_only_verdict,
    get_static_plus_llm_verdict,
)

logger = logging.getLogger(__name__)


def run_progressive_comparison(
    verified_routes: list[VerifiedRoute],
    ground_truth: dict[str, bool],
) -> dict:
    """
    Compute metrics for all three progressive pipeline stages and the
    deltas between consecutive stages.

    Parameters
    ----------
    verified_routes:
        Output from the dynamic verification layer.
    ground_truth:
        Mapping of ``route_id → actually_vulnerable`` from ground-truth files.

    Returns
    -------
    dict with keys:
        ``stage_1_static_only``, ``stage_2_static_plus_llm``,
        ``stage_3_final_system``, ``fp_reduction_stage1_to_stage2``,
        ``fp_reduction_stage2_to_stage3``, ``fp_reduction_stage1_to_stage3_total``,
        ``ground_truth_size``, ``routes_evaluated``, ``routes_skipped``.
    """
    # ── Stage 1: Static Analysis Only ─────────────────────────────────
    cm1 = compute_confusion_matrix(verified_routes, ground_truth, get_static_only_verdict)
    m1 = compute_metrics_from_confusion(cm1)
    logger.info("Stage 1 (Static Only):       %s", _log_summary(m1))

    # ── Stage 2: Static + LLM ──────────────────────────────────────────
    cm2 = compute_confusion_matrix(verified_routes, ground_truth, get_static_plus_llm_verdict)
    m2 = compute_metrics_from_confusion(cm2)
    logger.info("Stage 2 (Static + LLM):      %s", _log_summary(m2))

    # ── Stage 3: Final System ──────────────────────────────────────────
    cm3 = compute_confusion_matrix(verified_routes, ground_truth, get_final_system_verdict)
    m3 = compute_metrics_from_confusion(cm3)
    logger.info("Stage 3 (Full Pipeline):     %s", _log_summary(m3))

    # ── FP reduction deltas ────────────────────────────────────────────
    fp1 = m1["fp"]
    fp2 = m2["fp"]
    fp3 = m3["fp"]

    delta_1_to_2 = fp1 - fp2
    delta_2_to_3 = fp2 - fp3
    delta_1_to_3 = fp1 - fp3

    logger.info(
        "FP reduction: Stage1→2: %d  Stage2→3: %d  Stage1→3 total: %d",
        delta_1_to_2,
        delta_2_to_3,
        delta_1_to_3,
    )

    gt_size = len(ground_truth)
    evaluated = m1["evaluated"]   # same for all stages (same route set + ground truth)
    skipped = m1["skipped"]

    return {
        "ground_truth_size": gt_size,
        "routes_evaluated": evaluated,
        "routes_skipped": skipped,
        "stage_1_static_only": m1,
        "stage_2_static_plus_llm": m2,
        "stage_3_final_system": m3,
        "fp_reduction_stage1_to_stage2": delta_1_to_2,
        "fp_reduction_stage2_to_stage3": delta_2_to_3,
        "fp_reduction_stage1_to_stage3_total": delta_1_to_3,
    }


def _log_summary(m: dict) -> str:
    return (
        f"TP={m['tp']} FP={m['fp']} FN={m['fn']} TN={m['tn']}  "
        f"P={m['precision']:.3f} R={m['recall']:.3f} F1={m['f1']:.3f} "
        f"FPR={m['false_positive_rate']:.3f}"
    )
