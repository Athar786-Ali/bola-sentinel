"""
Precision / recall / F1 and related metrics for BOLA detection evaluation.

All computations are division-safe: any metric whose denominator is zero
is returned as 0.0 with no exception raised.  This keeps the metrics layer
stable even when a stage produces zero positives (e.g., Stage 3 on a
dataset where nothing was dynamically verified yet).
"""

from __future__ import annotations

from typing import Callable

from bola_sentinel.models.schemas import VerifiedRoute


def compute_confusion_matrix(
    routes: list[VerifiedRoute],
    ground_truth: dict[str, bool],
    verdict_fn: Callable[[VerifiedRoute], bool],
) -> dict[str, int]:
    """
    Compute a confusion matrix by comparing *verdict_fn* against *ground_truth*.

    Only routes whose ``route_id`` appears in *ground_truth* contribute to
    the counts — unmatched routes are silently skipped (they cannot be
    evaluated without a label).

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
    dict with keys "tp", "fp", "fn", "tn" and integer values.
        Also includes "evaluated" (total routes with a ground-truth label)
        and "skipped" (routes without a label).
    """
    tp = fp = fn = tn = evaluated = skipped = 0

    for route in routes:
        if route.route_id not in ground_truth:
            skipped += 1
            continue

        evaluated += 1
        predicted = verdict_fn(route)
        actual = ground_truth[route.route_id]

        if predicted and actual:
            tp += 1
        elif predicted and not actual:
            fp += 1
        elif not predicted and actual:
            fn += 1
        else:
            tn += 1

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "evaluated": evaluated,
        "skipped": skipped,
    }


def compute_metrics_from_confusion(cm: dict[str, int]) -> dict[str, float | int]:
    """
    Compute precision, recall, F1, FPR, and FNR from a confusion matrix.

    Parameters
    ----------
    cm:
        Dict with at minimum keys "tp", "fp", "fn", "tn".

    Returns
    -------
    dict containing:
        precision, recall, f1, false_positive_rate, false_negative_rate,
        tp, fp, fn, tn, evaluated, skipped.
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

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "evaluated": cm.get("evaluated", tp + fp + fn + tn),
        "skipped": cm.get("skipped", 0),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "false_positive_rate": round(false_positive_rate, 4),
        "false_negative_rate": round(false_negative_rate, 4),
    }
