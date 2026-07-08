"""
Markdown report writer for the evaluation layer.

Generates a structured research report from the progressive comparison
results.  The report is designed to support the paper's central claim:
adding LLM reasoning and then dynamic verification progressively reduces
false positives compared to static analysis alone.

Every number in the report traces back to logs/evaluation_logs/ for
full reproducibility.
"""

from __future__ import annotations

import logging
from pathlib import Path

from bola_sentinel.models.schemas import StandardizedFinding

logger = logging.getLogger(__name__)


def _pct(rate: float) -> str:
    """Format a 0-1 rate as a percentage string."""
    return f"{rate * 100:.1f}%"


def _fmt(val: float) -> str:
    """Format a metric value to 3 decimal places."""
    return f"{val:.3f}"


def write_markdown_report(
    comparison: dict,
    standardized_findings: list[StandardizedFinding],
    output_path: str = "results/EVALUATION_REPORT.md",
) -> Path:
    """
    Write a structured Markdown evaluation report.

    Sections
    --------
    1. Header & summary
    2. Three-stage comparison table
    3. Confusion matrices per stage
    4. False-positive reduction section (the paper's primary claim)
    5. Standardized findings
    6. Related-work reference section

    Parameters
    ----------
    comparison:
        Dict returned by ``run_progressive_comparison``.
    standardized_findings:
        List returned by ``build_standardized_findings``.
    output_path:
        Output file path for the Markdown report.

    Returns
    -------
    Path
        Path of the written report file.
    """
    s1 = comparison["stage_1_static_only"]
    s2 = comparison["stage_2_static_plus_llm"]
    s3 = comparison["stage_3_final_system"]

    fp1 = s1["fp"]
    fp2 = s2["fp"]
    fp3 = s3["fp"]

    delta_1_2 = comparison["fp_reduction_stage1_to_stage2"]
    delta_2_3 = comparison["fp_reduction_stage2_to_stage3"]
    delta_1_3 = comparison["fp_reduction_stage1_to_stage3_total"]

    gt_size = comparison["ground_truth_size"]
    evaluated = comparison["routes_evaluated"]
    skipped = comparison["routes_skipped"]

    lines: list[str] = []

    # ── Header ────────────────────────────────────────────────────────
    lines += [
        "# BOLA-Sentinel Evaluation Report",
        "",
        "> **Reproducibility**: All numbers in this report are derived from "
        "`results/final_verified_results.json`, `datasets/ground_truth/`, and "
        "`logs/evaluation_logs/`.  Re-running `bola-sentinel evaluate` on the same "
        "inputs will produce identical results.",
        "",
        "## Overview",
        "",
        f"| Item | Count |",
        f"|------|-------|",
        f"| Ground-truth routes | {gt_size} |",
        f"| Routes evaluated (matched to ground truth) | {evaluated} |",
        f"| Routes skipped (no ground-truth label) | {skipped} |",
        f"| CONFIRMED_VULNERABLE findings | {len(standardized_findings)} |",
        "",
    ]

    # ── Three-stage comparison table ──────────────────────────────────
    lines += [
        "## Three-Stage Progressive Comparison",
        "",
        "Each stage is a checkpoint of the **same pipeline**, not an independent tool.",
        "",
        "| Stage | TP | FP | FN | TN | Precision | Recall | F1 | FPR | FNR |",
        "|-------|----|----|----|----|-----------|--------|-----|-----|-----|",
        f"| **Stage 1** – Static Analysis Only | "
        f"{s1['tp']} | {s1['fp']} | {s1['fn']} | {s1['tn']} | "
        f"{_fmt(s1['precision'])} | {_fmt(s1['recall'])} | {_fmt(s1['f1'])} | "
        f"{_pct(s1['false_positive_rate'])} | {_pct(s1['false_negative_rate'])} |",
        f"| **Stage 2** – Static + LLM Reasoning | "
        f"{s2['tp']} | {s2['fp']} | {s2['fn']} | {s2['tn']} | "
        f"{_fmt(s2['precision'])} | {_fmt(s2['recall'])} | {_fmt(s2['f1'])} | "
        f"{_pct(s2['false_positive_rate'])} | {_pct(s2['false_negative_rate'])} |",
        f"| **Stage 3** – Full Pipeline (Final) | "
        f"{s3['tp']} | {s3['fp']} | {s3['fn']} | {s3['tn']} | "
        f"{_fmt(s3['precision'])} | {_fmt(s3['recall'])} | {_fmt(s3['f1'])} | "
        f"{_pct(s3['false_positive_rate'])} | {_pct(s3['false_negative_rate'])} |",
        "",
        "> FPR = False Positive Rate = FP / (FP + TN).  "
        "FNR = False Negative Rate = FN / (FN + TP).",
        "",
    ]

    # ── Confusion matrices ─────────────────────────────────────────────
    lines += [
        "## Confusion Matrices",
        "",
        "### Stage 1 – Static Analysis Only",
        "",
        _confusion_table(s1),
        "",
        "### Stage 2 – Static Analysis + LLM Reasoning",
        "",
        _confusion_table(s2),
        "",
        "### Stage 3 – Full Pipeline (Final System)",
        "",
        _confusion_table(s3),
        "",
    ]

    # ── False-positive reduction (primary claim) ───────────────────────
    lines += [
        "## False-Positive Reduction — Primary Research Claim",
        "",
        "The table below shows how each added pipeline stage reduced the "
        "absolute number of false positives compared to the previous stage.",
        "",
        "| Transition | FP Before | FP After | Reduction |",
        "|------------|-----------|----------|-----------|",
        f"| Stage 1 → Stage 2 (adding LLM reasoning) | "
        f"{fp1} | {fp2} | **{delta_1_2}** fewer FPs |",
        f"| Stage 2 → Stage 3 (adding dynamic verification) | "
        f"{fp2} | {fp3} | **{delta_2_3}** fewer FPs |",
        f"| Stage 1 → Stage 3 (total reduction) | "
        f"{fp1} | {fp3} | **{delta_1_3}** fewer FPs |",
        "",
    ]

    # Plain-language summary
    if delta_1_2 > 0:
        lines.append(
            f"Adding LLM reasoning (Stage 1 → Stage 2) reduced false positives "
            f"by **{delta_1_2}** (from {fp1} to {fp2})."
        )
    else:
        lines.append(
            "LLM reasoning did not reduce false positives on this dataset "
            "(Stage 1 FP = Stage 2 FP)."
        )
    lines.append("")
    if delta_2_3 > 0:
        lines.append(
            f"Adding dynamic verification (Stage 2 → Stage 3) reduced false "
            f"positives by a further **{delta_2_3}** (from {fp2} to {fp3})."
        )
    else:
        lines.append(
            "Dynamic verification did not further reduce false positives on this "
            "dataset (Stage 2 FP = Stage 3 FP)."
        )
    lines += [
        "",
        f"**Total pipeline reduction**: {delta_1_3} fewer false positives versus "
        f"static analysis alone.",
        "",
    ]

    # ── Standardized findings ─────────────────────────────────────────
    lines += [
        "## Confirmed Vulnerabilities (CONFIRMED_VULNERABLE)",
        "",
    ]
    if not standardized_findings:
        lines.append("No routes were confirmed vulnerable by the full pipeline.")
    else:
        lines += [
            "| Route ID | Auth Model | Confidence | Evidence |",
            "|----------|-----------|------------|----------|",
        ]
        for f in standardized_findings:
            evidence = (f.evidence or "").replace("|", "\\|").replace("\n", " ")[:80]
            lines.append(
                f"| `{f.route_id}` | {f.authorization_model} | "
                f"{f.confidence} | {evidence} |"
            )
    lines.append("")

    # ── Full findings JSON block ───────────────────────────────────────
    if standardized_findings:
        import json as _json
        lines += [
            "### Full Standardized Findings (JSON)",
            "",
            "```json",
            _json.dumps(
                [f.model_dump(mode="json") for f in standardized_findings],
                indent=2,
            ),
            "```",
            "",
        ]

    # ── Related work reference section ────────────────────────────────
    lines += [
        "## Related Work — Reference Context",
        "",
        "The following published numbers are provided for **context only**.  "
        "They come from different datasets and experimental setups and cannot "
        "be used for a direct head-to-head comparison without running those "
        "tools on the same ground-truth corpus.",
        "",
        "| Tool | Reported Metric | Value |",
        "|------|-----------------|-------|",
        "| BolaRay (static + heuristic) | False Positive Rate (FPR) on their dataset | 21.86% |",
        "| IRIS (LLM-based) | False Discovery Rate (FDR) on their dataset | 84.82% |",
        "",
        "Our Stage 1 (static-only) FPR on this dataset is "
        f"**{_pct(s1['false_positive_rate'])}**, and our final-system FPR is "
        f"**{_pct(s3['false_positive_rate'])}**.",
        "",
        "> These numbers are not directly comparable to BolaRay or IRIS without "
        "running all three tools on an identical held-out benchmark.",
        "",
    ]

    # ── Write file ────────────────────────────────────────────────────
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(lines) + "\n"
    out_path.write_text(content, encoding="utf-8")
    logger.info("Markdown report written to %s (%d chars)", out_path, len(content))
    return out_path


def _confusion_table(m: dict) -> str:
    """Render a 2×2 confusion matrix as a Markdown table."""
    lines = [
        "|  | **Predicted Positive** | **Predicted Negative** |",
        "|--|----------------------|----------------------|",
        f"| **Actually Positive** | TP = {m['tp']} | FN = {m['fn']} |",
        f"| **Actually Negative** | FP = {m['fp']} | TN = {m['tn']} |",
    ]
    return "\n".join(lines)
