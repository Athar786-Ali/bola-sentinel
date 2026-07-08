"""
Evaluation layer — public package API.

Responsibility: Compare the three progressive pipeline stages against ground
truth, compute precision/recall/F1/FPR/FNR, quantify false-positive reduction
between stages, and write reproducible output (JSON metrics + Markdown report
+ evaluation run log).
"""

from .comparator import run_progressive_comparison
from .ground_truth_loader import load_all_ground_truth
from .standardized_output import build_standardized_findings

__all__ = [
    "load_all_ground_truth",
    "run_progressive_comparison",
    "build_standardized_findings",
]
