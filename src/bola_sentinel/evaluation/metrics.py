"""
Precision / recall / F1 / FPR / Coverage and related metrics for BOLA
detection evaluation.

Post-audit design (July 2026)
------------------------------
The confusion matrix now iterates over **ground_truth.keys()** as the single
source of truth, not over the pipeline output.  This ensures that:
  - Ground-truth vulnerabilities missed entirely by the pipeline are correctly
    counted as False Negatives (FN).
  - Ground-truth safe routes never surfaced by the pipeline are correctly
    counted as True Negatives (TN).

Coverage is a new, independent metric that measures the pipeline's discovery
capability (how many ground-truth routes were found at all), distinct from
Recall (which measures classification accuracy on discovered vulnerable routes).

All computations are division-safe: any metric whose denominator is zero
is returned as 0.0 with no exception raised.
"""

from __future__ import annotations

import logging
from typing import Callable

from bola_sentinel.models.schemas import VerifiedRoute

logger = logging.getLogger(__name__)


def compute_confusion_matrix(
    routes: list[VerifiedRoute],
    ground_truth: dict[str, bool],
    verdict_fn: Callable[[VerifiedRoute], bool],
) -> dict[str, int]:
    """
    Compute a confusion matrix by comparing *verdict_fn* against *ground_truth*.

    The iteration is driven by **ground_truth.keys()** — every labelled route
    is evaluated regardless of whether the pipeline discovered it.

    For ground-truth routes NOT present in the pipeline output:
      - If actually_vulnerable → FN  (missed vulnerability)
      - If NOT actually_vulnerable → TN  (correctly absent, safe route)

    For ground-truth routes present in the pipeline output:
      - Standard TP / FP / FN / TN logic using verdict_fn.

    Parameters
    ----------
    routes:
        Output from the verification layer (``list[VerifiedRoute]``).
    ground_truth:
        Mapping of ``route_id → actually_vulnerable`` from ground-truth files.
    verdict_fn:
        A callable accepting a ``VerifiedRoute`` and returning ``bool``.
        Use the stage functions from ``stage_classifiers.py``.

    Returns
    -------
    dict with keys "tp", "fp", "fn", "tn", "evaluated", "skipped".
        ``evaluated`` = routes in ground truth that were found in the pipeline.
        ``skipped`` = routes in the pipeline that have no ground-truth label.
    """
    tp = fp = fn = tn = 0
    evaluated = 0  # GT routes found in pipeline output
    skipped = 0    # Pipeline routes with no GT label

    # Build a lookup index from route_id to VerifiedRoute for O(1) access.
    route_index: dict[str, VerifiedRoute] = {r.route_id: r for r in routes}

    # Count pipeline routes that have no ground-truth label.
    for route in routes:
        if route.route_id not in ground_truth:
            skipped += 1

    # Iterate over ground truth as the single source of truth.
    for route_id, actually_vulnerable in ground_truth.items():
        if route_id in route_index:
            # Pipeline discovered this route — evaluate normally.
            evaluated += 1
            predicted = verdict_fn(route_index[route_id])
            if predicted and actually_vulnerable:
                tp += 1
            elif predicted and not actually_vulnerable:
                fp += 1
            elif not predicted and actually_vulnerable:
                fn += 1
            else:
                tn += 1
        else:
            # Pipeline never discovered this route.
            if actually_vulnerable:
                fn += 1   # Missed vulnerability
            else:
                tn += 1   # Correctly absent safe route

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "evaluated": evaluated,
        "skipped": skipped,
    }


def compute_coverage(
    routes: list[VerifiedRoute],
    ground_truth: dict[str, bool],
) -> float:
    """
    Compute discovery coverage: fraction of ground-truth routes found by
    the pipeline.

    Coverage measures **discovery capability only** — whether the pipeline
    found the route at all, regardless of whether it classified it correctly.

    Coverage is independent from Precision and Recall:
      - Coverage = How many ground-truth routes were discovered.
      - Recall   = How many actual vulnerable routes were correctly classified.
      - Precision = How many predicted vulnerable routes are actually vulnerable.

    Parameters
    ----------
    routes:
        Output from the verification layer (``list[VerifiedRoute]``).
    ground_truth:
        Mapping of ``route_id → actually_vulnerable`` from ground-truth files.

    Returns
    -------
    float
        Coverage as a ratio in [0.0, 1.0].
    """
    if not ground_truth:
        return 0.0

    route_ids = {r.route_id for r in routes}
    discovered = sum(1 for gt_id in ground_truth if gt_id in route_ids)
    return round(discovered / len(ground_truth), 4)


def compute_metrics_from_confusion(cm: dict[str, int]) -> dict[str, float | int]:
    """
    Compute precision, recall, F1, FPR, FNR, and accuracy from a confusion
    matrix.

    Parameters
    ----------
    cm:
        Dict with at minimum keys "tp", "fp", "fn", "tn".

    Returns
    -------
    dict containing:
        precision, recall, f1, false_positive_rate, false_negative_rate,
        accuracy, tp, fp, fn, tn, evaluated, skipped.
    """
    tp = cm["tp"]
    fp = cm["fp"]
    fn = cm["fn"]
    tn = cm["tn"]

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    false_positive_rate = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    false_negative_rate = fn / (fn + tp) if (fn + tp) > 0 else 0.0
    total = tp + fp + fn + tn
    accuracy = (tp + tn) / total if total > 0 else 0.0

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "evaluated": cm.get("evaluated", 0),
        "skipped": cm.get("skipped", 0),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "false_positive_rate": round(false_positive_rate, 4),
        "false_negative_rate": round(false_negative_rate, 4),
        "accuracy": round(accuracy, 4),
    }
