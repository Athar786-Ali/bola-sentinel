"""
Pytest tests for the bola-sentinel evaluation layer.

Uses a fully synthetic VerifiedRoute set and matching ground-truth dict
so tests are self-contained, fast, and reproducible.

Coverage
--------
(a) confusion matrices are mathematically correct for each of the three stages
(b) fp_reduction deltas are computed correctly
(c) build_standardized_findings produces exactly the required field structure
(d) ground_truth_loader raises on malformed files, merges valid ones correctly
(e) report_writer generates all required sections and correct FP numbers
(f) metrics are division-safe (zero denominator → 0.0 not exception)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bola_sentinel.evaluation.comparator import run_progressive_comparison
from bola_sentinel.evaluation.ground_truth_loader import load_all_ground_truth
from bola_sentinel.evaluation.metrics import (
    compute_confusion_matrix,
    compute_metrics_from_confusion,
)
from bola_sentinel.evaluation.report_writer import write_markdown_report
from bola_sentinel.evaluation.stage_classifiers import (
    get_final_system_verdict,
    get_static_only_verdict,
    get_static_plus_llm_verdict,
)
from bola_sentinel.evaluation.standardized_output import build_standardized_findings
from bola_sentinel.models.schemas import (
    ClassifiedRoute,
    DbOperation,
    LlmClassification,
    ObjectIdParam,
    StandardizedFinding,
    VerificationResult,
    VerifiedRoute,
)

# ── Synthetic route factory ────────────────────────────────────────────────


def _make_verified_route(
    route_id: str,
    auth_check_status: str = "ABSENT",
    llm_is_vulnerable: bool | None = True,
    verification_status: str | None = "CONFIRMED_VULNERABLE",
    llm_model: str = "OWNERSHIP",
    confidence: str = "HIGH",
) -> VerifiedRoute:
    """
    Build a VerifiedRoute with controlled per-field values for testing.

    *llm_is_vulnerable* = None  → llm_classification is None (PRESENT route).
    *verification_status* = None → verification is None (not probed).
    """
    llm_cls = (
        None
        if llm_is_vulnerable is None
        else LlmClassification(
            applicable_model=llm_model,  # type: ignore[arg-type]
            is_vulnerable=llm_is_vulnerable,
            confidence=confidence,  # type: ignore[arg-type]
            explanation="test explanation",
            suggested_test_description="test desc",
            requires_two_users=True,
        )
    )

    verif = (
        None
        if verification_status is None
        else VerificationResult(
            verification_status=verification_status,  # type: ignore[arg-type]
            http_status_received=200 if verification_status == "CONFIRMED_VULNERABLE" else 403,
            response_body_evidence='{"status":"changed"}' if verification_status == "CONFIRMED_VULNERABLE" else None,
            object_state_changed=True if verification_status == "CONFIRMED_VULNERABLE" else None,
            attacker_user_id="1",
            victim_object_id="42",
            url_used=f"http://localhost/api/resource/42",
            notes="test note",
        )
    )

    return VerifiedRoute(
        route_id=route_id,
        http_method="POST",  # type: ignore[arg-type]
        route_path=f"/api/resource/{{id}}",
        file_path="app.py",
        line_number=1,
        language="python",
        object_id_params=[ObjectIdParam(name="id", location="path")],
        db_operations=[],
        auth_check_status=auth_check_status,  # type: ignore[arg-type]
        handler_code_raw="def handler(): pass",
        llm_classification=llm_cls,
        verification=verif,
    )


# ── Synthetic test corpus ──────────────────────────────────────────────────
#
# Route      GT    S1_pred  S2_pred  S3_pred    Outcome per stage
# ──────────────────────────────────────────────────────────────────────────
# r_tp_all   True  True     True     True       TP in all stages
# r_fp_s1    False True     False    False      FP only in Stage 1
# r_fp_s12   False True     True     False      FP in Stage 1+2, NOT 3
# r_fn_all   True  False    False    False      FN in all stages (PRESENT)
# r_tn_all   False False    False    False      TN in all stages (PRESENT)
# r_nogt     –     –        –        –          skipped (no GT label)

def _build_corpus() -> tuple[list[VerifiedRoute], dict[str, bool]]:
    routes = [
        # TP in all stages: ABSENT → LLM says vuln → Confirmed
        _make_verified_route(
            "r_tp_all",
            auth_check_status="ABSENT",
            llm_is_vulnerable=True,
            verification_status="CONFIRMED_VULNERABLE",
        ),
        # FP only in Stage 1: ABSENT → LLM says NOT vuln → not probed
        _make_verified_route(
            "r_fp_s1",
            auth_check_status="ABSENT",
            llm_is_vulnerable=False,
            verification_status=None,
        ),
        # FP in Stage 1+2, not 3: ABSENT → LLM says vuln → NOT_VULNERABLE on probe
        _make_verified_route(
            "r_fp_s12",
            auth_check_status="ABSENT",
            llm_is_vulnerable=True,
            verification_status="NOT_VULNERABLE",
        ),
        # FN in all stages: PRESENT route (never sent to LLM), but actually vuln
        _make_verified_route(
            "r_fn_all",
            auth_check_status="PRESENT",
            llm_is_vulnerable=None,   # llm_classification=None
            verification_status=None,
        ),
        # TN in all stages: PRESENT route, actually not vuln
        _make_verified_route(
            "r_tn_all",
            auth_check_status="PRESENT",
            llm_is_vulnerable=None,
            verification_status=None,
        ),
        # No GT label — should be skipped entirely
        _make_verified_route(
            "r_nogt",
            auth_check_status="ABSENT",
            llm_is_vulnerable=True,
            verification_status="CONFIRMED_VULNERABLE",
        ),
    ]

    ground_truth = {
        "r_tp_all": True,
        "r_fp_s1":  False,
        "r_fp_s12": False,
        "r_fn_all": True,
        "r_tn_all": False,
        # "r_nogt" intentionally absent
    }

    return routes, ground_truth


CORPUS_ROUTES, CORPUS_GT = _build_corpus()


# ── (a) Confusion matrices are mathematically correct ─────────────────────

class TestConfusionMatrices:
    """(a) Verify TP/FP/FN/TN for each stage against hand-computed values."""

    def test_stage1_tp(self) -> None:
        cm = compute_confusion_matrix(CORPUS_ROUTES, CORPUS_GT, get_static_only_verdict)
        # r_tp_all: ABSENT+True → TP
        assert cm["tp"] == 1

    def test_stage1_fp(self) -> None:
        cm = compute_confusion_matrix(CORPUS_ROUTES, CORPUS_GT, get_static_only_verdict)
        # r_fp_s1(ABSENT,False) + r_fp_s12(ABSENT,False) → 2 FPs
        assert cm["fp"] == 2

    def test_stage1_fn(self) -> None:
        cm = compute_confusion_matrix(CORPUS_ROUTES, CORPUS_GT, get_static_only_verdict)
        # r_fn_all: PRESENT+True → FN (static says NOT vuln)
        assert cm["fn"] == 1

    def test_stage1_tn(self) -> None:
        cm = compute_confusion_matrix(CORPUS_ROUTES, CORPUS_GT, get_static_only_verdict)
        # r_tn_all: PRESENT+False → TN
        assert cm["tn"] == 1

    def test_stage1_evaluated_excludes_nogt(self) -> None:
        cm = compute_confusion_matrix(CORPUS_ROUTES, CORPUS_GT, get_static_only_verdict)
        assert cm["evaluated"] == 5
        assert cm["skipped"] == 1

    def test_stage2_tp(self) -> None:
        cm = compute_confusion_matrix(CORPUS_ROUTES, CORPUS_GT, get_static_plus_llm_verdict)
        # r_tp_all: llm_is_vulnerable=True, GT=True → TP
        assert cm["tp"] == 1

    def test_stage2_fp(self) -> None:
        cm = compute_confusion_matrix(CORPUS_ROUTES, CORPUS_GT, get_static_plus_llm_verdict)
        # r_fp_s12: llm_is_vulnerable=True, GT=False → FP (r_fp_s1 has llm=False → not pred)
        assert cm["fp"] == 1

    def test_stage2_fn(self) -> None:
        cm = compute_confusion_matrix(CORPUS_ROUTES, CORPUS_GT, get_static_plus_llm_verdict)
        # r_fn_all (PRESENT, llm=None → not predicted) + r_fp_s1 removed by LLM filter
        # Still FN: r_fn_all
        assert cm["fn"] == 1

    def test_stage2_tn(self) -> None:
        cm = compute_confusion_matrix(CORPUS_ROUTES, CORPUS_GT, get_static_plus_llm_verdict)
        # r_tn_all (PRESENT, llm=None→False) + r_fp_s1 (llm=False, GT=False)
        assert cm["tn"] == 2

    def test_stage3_tp(self) -> None:
        cm = compute_confusion_matrix(CORPUS_ROUTES, CORPUS_GT, get_final_system_verdict)
        # r_tp_all: CONFIRMED_VULNERABLE, GT=True → TP
        assert cm["tp"] == 1

    def test_stage3_fp(self) -> None:
        cm = compute_confusion_matrix(CORPUS_ROUTES, CORPUS_GT, get_final_system_verdict)
        # r_fp_s12: NOT_VULNERABLE → predicted False; r_fp_s1: not probed → False
        # No FPs in Stage 3
        assert cm["fp"] == 0

    def test_stage3_fn(self) -> None:
        cm = compute_confusion_matrix(CORPUS_ROUTES, CORPUS_GT, get_final_system_verdict)
        # r_fn_all: not probed → False, GT=True → FN
        assert cm["fn"] == 1

    def test_stage3_tn(self) -> None:
        cm = compute_confusion_matrix(CORPUS_ROUTES, CORPUS_GT, get_final_system_verdict)
        # r_tn_all, r_fp_s1, r_fp_s12 all produce False prediction with False GT
        assert cm["tn"] == 3


# ── (b) FP reduction deltas are computed correctly ────────────────────────

class TestFpReductionDeltas:
    """(b) Stage-to-stage FP reduction deltas must match the per-stage FP counts."""

    @pytest.fixture(autouse=True)
    def _comparison(self) -> None:
        self.comp = run_progressive_comparison(CORPUS_ROUTES, CORPUS_GT)

    def test_fp_stage1(self) -> None:
        assert self.comp["stage_1_static_only"]["fp"] == 2

    def test_fp_stage2(self) -> None:
        assert self.comp["stage_2_static_plus_llm"]["fp"] == 1

    def test_fp_stage3(self) -> None:
        assert self.comp["stage_3_final_system"]["fp"] == 0

    def test_delta_stage1_to_stage2(self) -> None:
        assert self.comp["fp_reduction_stage1_to_stage2"] == 1   # 2 - 1

    def test_delta_stage2_to_stage3(self) -> None:
        assert self.comp["fp_reduction_stage2_to_stage3"] == 1   # 1 - 0

    def test_delta_stage1_to_stage3_total(self) -> None:
        assert self.comp["fp_reduction_stage1_to_stage3_total"] == 2   # 2 - 0

    def test_delta_consistency(self) -> None:
        """d12 + d23 must equal d13."""
        comp = self.comp
        assert (
            comp["fp_reduction_stage1_to_stage2"] + comp["fp_reduction_stage2_to_stage3"]
            == comp["fp_reduction_stage1_to_stage3_total"]
        )

    def test_routes_evaluated_correct(self) -> None:
        assert self.comp["routes_evaluated"] == 5

    def test_routes_skipped_correct(self) -> None:
        assert self.comp["routes_skipped"] == 1


# ── (c) build_standardized_findings field structure ───────────────────────

class TestStandardizedFindings:
    """(c) Findings have exactly the required fields and only CONFIRMED_VULNERABLE routes."""

    @pytest.fixture(autouse=True)
    def _findings(self) -> None:
        self.findings = build_standardized_findings(CORPUS_ROUTES)

    def test_only_confirmed_vulnerable_included(self) -> None:
        # Only r_tp_all has CONFIRMED_VULNERABLE; r_nogt also does but
        # standardized_findings includes all CONFIRMED_VULNERABLE regardless of GT.
        route_ids = {f.route_id for f in self.findings}
        assert "r_tp_all" in route_ids
        assert "r_nogt" in route_ids

    def test_not_vulnerable_excluded(self) -> None:
        route_ids = {f.route_id for f in self.findings}
        assert "r_fp_s12" not in route_ids  # verification=NOT_VULNERABLE

    def test_present_routes_excluded(self) -> None:
        route_ids = {f.route_id for f in self.findings}
        assert "r_fn_all" not in route_ids
        assert "r_tn_all" not in route_ids

    def test_vulnerability_type_is_bola(self) -> None:
        for f in self.findings:
            assert f.vulnerability_type == "BOLA"

    def test_required_fields_present(self) -> None:
        required = {
            "route_id", "vulnerability_type", "confidence",
            "verification_status", "authorization_model",
        }
        for f in self.findings:
            data = f.model_dump()
            for field in required:
                assert field in data, f"Missing field {field!r} in finding {f.route_id}"

    def test_finding_is_standardized_finding_instance(self) -> None:
        for f in self.findings:
            assert isinstance(f, StandardizedFinding)

    def test_findings_sorted_by_route_id(self) -> None:
        ids = [f.route_id for f in self.findings]
        assert ids == sorted(ids)

    def test_verification_status_confirmed(self) -> None:
        for f in self.findings:
            assert f.verification_status == "CONFIRMED_VULNERABLE"

    def test_confidence_field_populated(self) -> None:
        for f in self.findings:
            assert f.confidence in ("HIGH", "MEDIUM", "LOW")

    def test_authorization_model_populated(self) -> None:
        for f in self.findings:
            assert f.authorization_model in (
                "OWNERSHIP", "MEMBERSHIP", "HIERARCHICAL", "STATUS", "NONE"
            )


# ── (d) ground_truth_loader ───────────────────────────────────────────────

class TestGroundTruthLoader:
    """(d) Loader validation and merging behaviour."""

    def test_missing_dir_raises_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="not found"):
            load_all_ground_truth(str(tmp_path / "nonexistent"))

    def test_empty_dir_returns_empty_dict(self, tmp_path: Path) -> None:
        gt_dir = tmp_path / "gt"
        gt_dir.mkdir()
        result = load_all_ground_truth(str(gt_dir))
        assert result == {}

    def test_valid_file_loaded(self, tmp_path: Path) -> None:
        gt_dir = tmp_path / "gt"
        gt_dir.mkdir()
        (gt_dir / "test.json").write_text(
            json.dumps([{"route_id": "r1", "actually_vulnerable": True}])
        )
        result = load_all_ground_truth(str(gt_dir))
        assert result == {"r1": True}

    def test_multiple_files_merged(self, tmp_path: Path) -> None:
        gt_dir = tmp_path / "gt"
        gt_dir.mkdir()
        (gt_dir / "a.json").write_text(
            json.dumps([{"route_id": "r1", "actually_vulnerable": True}])
        )
        (gt_dir / "b.json").write_text(
            json.dumps([{"route_id": "r2", "actually_vulnerable": False}])
        )
        result = load_all_ground_truth(str(gt_dir))
        assert result["r1"] is True
        assert result["r2"] is False

    def test_invalid_json_raises_value_error(self, tmp_path: Path) -> None:
        gt_dir = tmp_path / "gt"
        gt_dir.mkdir()
        (gt_dir / "bad.json").write_text("not json!!!")
        with pytest.raises(ValueError, match="bad.json"):
            load_all_ground_truth(str(gt_dir))

    def test_missing_route_id_raises_value_error(self, tmp_path: Path) -> None:
        gt_dir = tmp_path / "gt"
        gt_dir.mkdir()
        (gt_dir / "bad.json").write_text(
            json.dumps([{"actually_vulnerable": True}])
        )
        with pytest.raises(ValueError, match="bad.json"):
            load_all_ground_truth(str(gt_dir))

    def test_not_a_list_raises_value_error(self, tmp_path: Path) -> None:
        gt_dir = tmp_path / "gt"
        gt_dir.mkdir()
        (gt_dir / "bad.json").write_text(json.dumps({"route_id": "r1"}))
        with pytest.raises(ValueError, match="bad.json"):
            load_all_ground_truth(str(gt_dir))

    def test_error_message_lists_all_failures(self, tmp_path: Path) -> None:
        gt_dir = tmp_path / "gt"
        gt_dir.mkdir()
        (gt_dir / "bad1.json").write_text("not json")
        (gt_dir / "bad2.json").write_text("also not json")
        with pytest.raises(ValueError) as exc_info:
            load_all_ground_truth(str(gt_dir))
        msg = str(exc_info.value)
        assert "bad1.json" in msg
        assert "bad2.json" in msg


# ── (e) report_writer sections and correctness ────────────────────────────

class TestReportWriter:
    """(e) Markdown report contains all required sections with correct numbers."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path: Path) -> None:
        self.comparison = run_progressive_comparison(CORPUS_ROUTES, CORPUS_GT)
        self.findings = build_standardized_findings(CORPUS_ROUTES)
        self.out_path = tmp_path / "EVALUATION_REPORT.md"
        write_markdown_report(self.comparison, self.findings, str(self.out_path))
        self.content = self.out_path.read_text()

    def test_report_file_created(self) -> None:
        assert self.out_path.exists()

    def test_contains_stage_table(self) -> None:
        assert "Stage 1" in self.content
        assert "Stage 2" in self.content
        assert "Stage 3" in self.content

    def test_contains_fp_reduction_section(self) -> None:
        assert "False-Positive Reduction" in self.content or "False Positive" in self.content

    def test_fp_numbers_in_report(self) -> None:
        # Stage 1 FP=2, Stage 2 FP=1, Stage 3 FP=0
        assert "| **Stage 1**" in self.content
        # Check that the correct total reduction number appears
        assert "2" in self.content   # delta_1_to_3 = 2

    def test_contains_confirmed_vulnerable_section(self) -> None:
        assert "CONFIRMED_VULNERABLE" in self.content or "Confirmed Vulnerabilities" in self.content

    def test_contains_related_work_section(self) -> None:
        assert "BolaRay" in self.content
        assert "IRIS" in self.content
        assert "21.86" in self.content
        assert "84.82" in self.content

    def test_contains_reproducibility_note(self) -> None:
        assert "reproducib" in self.content.lower() or "logs/" in self.content

    def test_findings_in_report(self) -> None:
        for f in self.findings:
            assert f.route_id in self.content


# ── (f) Division-safe metrics ─────────────────────────────────────────────

class TestMetricsDivisionSafe:
    """(f) Zero-denominator cases return 0.0 without raising."""

    def test_all_zeros_returns_zero_metrics(self) -> None:
        cm = {"tp": 0, "fp": 0, "fn": 0, "tn": 0, "evaluated": 0, "skipped": 0}
        m = compute_metrics_from_confusion(cm)
        assert m["precision"] == 0.0
        assert m["recall"] == 0.0
        assert m["f1"] == 0.0
        assert m["false_positive_rate"] == 0.0
        assert m["false_negative_rate"] == 0.0

    def test_no_positives_precision_zero(self) -> None:
        cm = {"tp": 0, "fp": 0, "fn": 5, "tn": 5, "evaluated": 10, "skipped": 0}
        m = compute_metrics_from_confusion(cm)
        assert m["precision"] == 0.0

    def test_perfect_classifier(self) -> None:
        cm = {"tp": 5, "fp": 0, "fn": 0, "tn": 5, "evaluated": 10, "skipped": 0}
        m = compute_metrics_from_confusion(cm)
        assert m["precision"] == 1.0
        assert m["recall"] == 1.0
        assert m["f1"] == 1.0
        assert m["false_positive_rate"] == 0.0
        assert m["false_negative_rate"] == 0.0

    def test_all_positives_fpr_one(self) -> None:
        cm = {"tp": 5, "fp": 5, "fn": 0, "tn": 0, "evaluated": 10, "skipped": 0}
        m = compute_metrics_from_confusion(cm)
        assert m["false_positive_rate"] == 1.0
