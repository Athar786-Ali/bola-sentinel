"""
bola-sentinel CLI entry point.

Commands
--------
  bola-sentinel analyze <target_path>  – run static analysis (Phase 1)
  bola-sentinel verify  <results_file> – run dynamic verification (Phase 3)
  bola-sentinel evaluate <results> <gt> – compute metrics (Phase 4)
  bola-sentinel report  <results_file> – pretty-print results (Phase 4)
"""

from __future__ import annotations

import json
import logging
import os
import sys
from collections import Counter
from pathlib import Path

import typer

from bola_sentinel.config import settings

app = typer.Typer(
    name="bola-sentinel",
    help=(
        "Hybrid static-analysis + local-LLM + dynamic-verification engine "
        "for detecting BOLA/IDOR vulnerabilities in REST APIs."
    ),
    add_completion=False,
)


def _setup_logging() -> None:
    """Configure basic logging to stderr."""
    level = logging.DEBUG if os.environ.get("BOLA_DEBUG") else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(name)s  %(levelname)s  %(message)s",
        stream=sys.stderr,
    )


@app.command("analyze")
def analyze(
    target: str = typer.Argument(..., help="Path to the target codebase root."),
    output: str = typer.Option(
        None,
        "--output",
        "-o",
        help="Output JSON path.  Defaults to <results_dir>/static_analysis_results.json.",
    ),
) -> None:
    """Run static analysis on a target codebase and write results JSON."""
    _setup_logging()

    from bola_sentinel.static_analysis import analyze_codebase

    target_path = Path(target).resolve()
    if not target_path.is_dir():
        typer.echo(f"Error: target path {target_path} is not a directory.", err=True)
        raise typer.Exit(code=1)

    results = analyze_codebase(str(target_path))

    # ── Determine output path ─────────────────────────────────────────
    if output:
        out_path = Path(output)
    else:
        out_path = Path(settings.results_dir) / "static_analysis_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # ── Serialize ─────────────────────────────────────────────────────
    data = [r.model_dump(mode="json") for r in results]
    out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    # ── Summary ───────────────────────────────────────────────────────
    typer.echo(f"\n{'─' * 60}")
    typer.echo(f"  Static Analysis Complete")
    typer.echo(f"{'─' * 60}")
    typer.echo(f"  Target:          {target_path}")
    typer.echo(f"  Routes found:    {len(results)}")

    method_counts = Counter(r.http_method for r in results)
    for method in ("POST", "PUT", "PATCH", "DELETE"):
        count = method_counts.get(method, 0)
        if count:
            typer.echo(f"    {method:8s}       {count}")

    auth_counts = Counter(r.auth_check_status for r in results)
    typer.echo(f"  Auth status:")
    for status in ("PRESENT", "ABSENT", "UNCERTAIN"):
        count = auth_counts.get(status, 0)
        typer.echo(f"    {status:12s}   {count}")

    typer.echo(f"  Output:          {out_path}")
    typer.echo(f"{'─' * 60}\n")


@app.command("classify")
def classify(
    input_file: str = typer.Option(
        None,
        "--input",
        "-i",
        help="Static analysis JSON to classify.  Defaults to <results_dir>/static_analysis_results.json.",
    ),
    output: str = typer.Option(
        None,
        "--output",
        "-o",
        help="Output JSON path.  Defaults to <results_dir>/llm_classified_results.json.",
    ),
) -> None:
    """Send ABSENT/UNCERTAIN routes to the local Ollama model for BOLA classification."""
    _setup_logging()

    from bola_sentinel.llm_reasoning import classify_all_routes
    from bola_sentinel.models.schemas import StaticAnalysisResult

    # ── Resolve input path ────────────────────────────────────────────
    in_path = Path(input_file) if input_file else Path(settings.results_dir) / "static_analysis_results.json"
    if not in_path.is_file():
        typer.echo(f"Error: input file not found: {in_path}", err=True)
        typer.echo("Run `bola-sentinel analyze <target>` first.", err=True)
        raise typer.Exit(code=1)

    raw_list = json.loads(in_path.read_text(encoding="utf-8"))
    routes = [StaticAnalysisResult.model_validate(r) for r in raw_list]

    # ── Classify ──────────────────────────────────────────────────────
    classified = classify_all_routes(routes)

    # ── Write output ──────────────────────────────────────────────────
    out_path = Path(output) if output else Path(settings.results_dir) / "llm_classified_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps([r.model_dump(mode="json") for r in classified], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # ── Summary ───────────────────────────────────────────────────────
    llm_routes = [r for r in classified if r.llm_classification is not None]
    vulnerable = [r for r in llm_routes if r.llm_classification.is_vulnerable]  # type: ignore[union-attr]
    parse_failures = [
        r for r in llm_routes
        if r.llm_classification.applicable_model == "NONE"
        and "parsing failed" in r.llm_classification.explanation
    ]

    model_counts = Counter(
        r.llm_classification.applicable_model
        for r in llm_routes
    )
    confidence_counts = Counter(
        r.llm_classification.confidence
        for r in llm_routes
    )

    typer.echo(f"\n{'─' * 60}")
    typer.echo(f"  LLM Classification Complete")
    typer.echo(f"{'─' * 60}")
    typer.echo(f"  Total routes:        {len(classified)}")
    typer.echo(f"  Sent to LLM:         {len(llm_routes)}")
    typer.echo(f"  Skipped (PRESENT):   {len(classified) - len(llm_routes)}")
    typer.echo(f"  is_vulnerable=True:  {len(vulnerable)}")
    typer.echo(f"  Parse failures:      {len(parse_failures)}")
    typer.echo(f"  By authorization model:")
    for model in ("OWNERSHIP", "MEMBERSHIP", "HIERARCHICAL", "STATUS", "NONE"):
        count = model_counts.get(model, 0)
        if count:
            typer.echo(f"    {model:14s}   {count}")
    typer.echo(f"  By confidence:")
    for conf in ("HIGH", "MEDIUM", "LOW"):
        count = confidence_counts.get(conf, 0)
        if count:
            typer.echo(f"    {conf:8s}         {count}")
    typer.echo(f"  Output:              {out_path}")
    typer.echo(f"{'─' * 60}\n")


@app.command("verify")
def verify(
    target_url: str = typer.Option(
        ...,
        "--target-url",
        help="Base URL of the target application, e.g. http://localhost:3000",
    ),
    input_file: str = typer.Option(
        None,
        "--input",
        "-i",
        help="Classified results JSON.  Defaults to <results_dir>/llm_classified_results.json.",
    ),
    output: str = typer.Option(
        None,
        "--output",
        "-o",
        help="Output path.  Defaults to <results_dir>/final_verified_results.json.",
    ),
    test_users_file: str = typer.Option(
        "test_users.json",
        "--test-users",
        help="Path to test_users.json.",
    ),
) -> None:
    """Send live HTTP probes to confirm/deny LLM-flagged BOLA vulnerabilities."""
    _setup_logging()

    from collections import Counter as _Counter

    from bola_sentinel.dynamic_verification import verify_all_routes
    from bola_sentinel.models.schemas import ClassifiedRoute

    in_path = (
        Path(input_file)
        if input_file
        else Path(settings.results_dir) / "llm_classified_results.json"
    )
    if not in_path.is_file():
        typer.echo(f"Error: input file not found: {in_path}", err=True)
        typer.echo("Run `bola-sentinel classify` first.", err=True)
        raise typer.Exit(code=1)

    raw_list = json.loads(in_path.read_text(encoding="utf-8"))
    classified = [ClassifiedRoute.model_validate(r) for r in raw_list]

    verified = verify_all_routes(classified, target_url, test_users_file)

    out_path = (
        Path(output)
        if output
        else Path(settings.results_dir) / "final_verified_results.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps([r.model_dump(mode="json") for r in verified], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # ── Summary ───────────────────────────────────────────────────────
    probed = [r for r in verified if r.verification is not None]
    confirmed = [r for r in probed if r.verification.verification_status == "CONFIRMED_VULNERABLE"]  # type: ignore[union-attr]
    confirmed_strong = [r for r in confirmed if r.verification.object_state_changed is True]  # type: ignore[union-attr]
    confirmed_weak = [r for r in confirmed if r.verification.object_state_changed is None]  # type: ignore[union-attr]
    not_vuln = [r for r in probed if r.verification.verification_status == "NOT_VULNERABLE"]  # type: ignore[union-attr]
    inconclusive = [r for r in probed if r.verification.verification_status == "INCONCLUSIVE"]  # type: ignore[union-attr]

    typer.echo(f"\n{'─' * 60}")
    typer.echo(f"  Dynamic Verification Complete")
    typer.echo(f"{'─' * 60}")
    typer.echo(f"  Target URL:              {target_url}")
    typer.echo(f"  Routes verified:         {len(probed)}")
    typer.echo(f"  Skipped (not flagged):   {len(verified) - len(probed)}")
    typer.echo(f"  CONFIRMED_VULNERABLE:    {len(confirmed)}")
    typer.echo(f"    with state-change evidence:  {len(confirmed_strong)}")
    typer.echo(f"    status+body only (weak):     {len(confirmed_weak)}")
    typer.echo(f"  NOT_VULNERABLE:          {len(not_vuln)}  ← false positives caught")
    typer.echo(f"  INCONCLUSIVE:            {len(inconclusive)}")
    typer.echo(f"  Output:                  {out_path}")
    typer.echo(f"{'─' * 60}\n")


@app.command("evaluate")
def evaluate(
    app_name: str = typer.Option(
        ..., "--app-name",
        help="Application name (matches datasets/ground_truth/{app_name}.json).",
    ),
    input_file: str = typer.Option(
        None, "--input", "-i",
        help="Verified results JSON. Defaults to <results_dir>/final_verified_results.json.",
    ),
    ground_truth_dir: str = typer.Option(
        "datasets/ground_truth",
        "--ground-truth", "-g",
        help="Directory containing ground-truth JSON files.",
    ),
    metrics_output: str = typer.Option(
        None, "--metrics-output",
        help="Metrics JSON path. Defaults to <results_dir>/evaluation_metrics.json.",
    ),
    report_output: str = typer.Option(
        None, "--report-output",
        help="Report path. Defaults to results/EVALUATION_REPORT.md.",
    ),
) -> None:
    """Run the three-stage progressive evaluation and write the research report."""
    _setup_logging()

    from bola_sentinel.evaluation import (
        build_standardized_findings,
        load_ground_truth_for_app,
        run_progressive_comparison,
    )
    from bola_sentinel.evaluation.evaluation_logger import log_evaluation_run
    from bola_sentinel.evaluation.report_writer import write_markdown_report
    from bola_sentinel.models.schemas import VerifiedRoute

    # ── Load verified results ────────────────────────────────────────
    in_path = (
        Path(input_file)
        if input_file
        else Path(settings.results_dir) / "final_verified_results.json"
    )
    if not in_path.is_file():
        typer.echo(f"Error: input file not found: {in_path}", err=True)
        typer.echo("Run `bola-sentinel verify --target-url <url>` first.", err=True)
        raise typer.Exit(code=1)

    raw_list = json.loads(in_path.read_text(encoding="utf-8"))
    verified_routes = [VerifiedRoute.model_validate(r) for r in raw_list]

    # ── Load ground truth (app-scoped) ───────────────────────────────
    try:
        ground_truth = load_ground_truth_for_app(app_name, ground_truth_dir)
    except (FileNotFoundError, ValueError) as exc:
        typer.echo(f"Error loading ground truth: {exc}", err=True)
        raise typer.Exit(code=1)

    # ── Run comparison ───────────────────────────────────────────────
    comparison = run_progressive_comparison(verified_routes, ground_truth)
    findings = build_standardized_findings(verified_routes)

    # ── Write outputs ────────────────────────────────────────────────
    metrics_path = (
        Path(metrics_output)
        if metrics_output
        else Path(settings.results_dir) / "evaluation_metrics.json"
    )
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(
        json.dumps(comparison, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    report_path_str = report_output or "results/EVALUATION_REPORT.md"
    write_markdown_report(comparison, findings, report_path_str)

    # ── Log run for reproducibility ──────────────────────────────────
    log_evaluation_run(
        verified_route_count=len(verified_routes),
        ground_truth_file_count=1,  # always exactly one file now
        ground_truth_route_count=len(ground_truth),
        routes_evaluated=comparison["routes_evaluated"],
        routes_skipped=comparison["routes_skipped"],
        comparison=comparison,
    )

    # ── Console output ───────────────────────────────────────────────
    s1 = comparison["stage_1_static_only"]
    s2 = comparison["stage_2_static_plus_llm"]
    s3 = comparison["stage_3_final_system"]
    d12 = comparison["fp_reduction_stage1_to_stage2"]
    d23 = comparison["fp_reduction_stage2_to_stage3"]
    d13 = comparison["fp_reduction_stage1_to_stage3_total"]
    cov = comparison["coverage"]

    def _row(label: str, m: dict) -> str:
        return (
            f"  {label:36s}  "
            f"P={m['precision']:.3f}  R={m['recall']:.3f}  "
            f"F1={m['f1']:.3f}  FPR={m['false_positive_rate']*100:.1f}%  "
            f"Acc={m['accuracy']:.3f}  "
            f"FP={m['fp']}  FN={m['fn']}  TP={m['tp']}"
        )

    typer.echo(f"\n{'─' * 80}")
    typer.echo(f"  Evaluation Complete — Progressive Stage Comparison")
    typer.echo(f"  Application: {app_name}")
    typer.echo(f"{'─' * 80}")
    typer.echo(f"  Ground-truth routes:         {comparison['ground_truth_size']}")
    typer.echo(f"  Routes discovered by pipeline: {comparison['routes_evaluated']}")
    typer.echo(f"  Pipeline routes without GT:    {comparison['routes_skipped']}")
    typer.echo(f"  Coverage:                      {cov*100:.1f}%")
    typer.echo(f"{'─' * 80}")
    typer.echo(_row("Stage 1  Static Only", s1))
    typer.echo(_row("Stage 2  Static + LLM", s2))
    typer.echo(_row("Stage 3  Full Pipeline (Final)", s3))
    typer.echo(f"{'─' * 80}")
    typer.echo(f"  False-Positive Reduction:")
    typer.echo(f"    Stage 1 → 2 (adding LLM):               {d12:+d} FPs")
    typer.echo(f"    Stage 2 → 3 (adding dynamic verif.):    {d23:+d} FPs")
    typer.echo(f"    Stage 1 → 3 total reduction:            {d13:+d} FPs")
    typer.echo(f"{'─' * 80}")
    typer.echo(f"  CONFIRMED_VULNERABLE findings:  {len(findings)}")
    typer.echo(f"  Metrics JSON:  {metrics_path}")
    typer.echo(f"  Report:        {report_path_str}")
    typer.echo(f"{'─' * 80}\n")


if __name__ == "__main__":
    app()
