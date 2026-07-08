"""
Pytest tests for the bola-sentinel LLM reasoning layer.

All tests mock call_ollama so no real Ollama instance is required.

Coverage
--------
(a) Valid JSON response → parses into correct LlmClassification fields.
(b) Malformed / non-JSON response → fallback path triggered, is_vulnerable=False, confidence=LOW.
(c) log_llm_input and log_llm_output are BOTH called exactly once per classify_route call.
(d) classify_all_routes: PRESENT routes are passed through without an LLM call.
(e) classify_all_routes: ABSENT and UNCERTAIN routes both trigger LLM calls.
(f) Ollama connection error → fallback, not crash.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, call, patch

import pytest

from bola_sentinel.llm_reasoning.classifier import classify_all_routes, classify_route
from bola_sentinel.models.schemas import (
    ClassifiedRoute,
    DbOperation,
    LlmClassification,
    ObjectIdParam,
    StaticAnalysisResult,
)

# ── Fixtures ───────────────────────────────────────────────────────────────

_VALID_LLM_JSON = json.dumps(
    {
        "applicable_model": "OWNERSHIP",
        "is_vulnerable": True,
        "confidence": "HIGH",
        "explanation": "No ownership check was found before the DB delete call.",
        "suggested_test_description": "Access victim order with attacker token.",
        "requires_two_users": True,
    }
)

_INVALID_LLM_RESPONSE = "This is not JSON at all, sorry!"

_PARTIAL_JSON = json.dumps(
    {
        "applicable_model": "OWNERSHIP",
        # missing required fields: is_vulnerable, confidence, explanation, etc.
    }
)


def _make_route(
    http_method: str = "POST",
    route_path: str = "/orders/{orderId}/cancel",
    auth_check_status: str = "ABSENT",
    route_id: str | None = None,
) -> StaticAnalysisResult:
    """Build a minimal StaticAnalysisResult for testing."""
    if route_id is None:
        route_id = f"{http_method}_{route_path}_42"
    return StaticAnalysisResult(
        route_id=route_id,
        http_method=http_method,  # type: ignore[arg-type]
        route_path=route_path,
        file_path="tests/fixtures/express_app/routes.js",
        line_number=42,
        language="javascript",
        object_id_params=[ObjectIdParam(name="orderId", location="path")],
        db_operations=[DbOperation(operation_type="DELETE", snippet="order.destroy()")],
        auth_check_status=auth_check_status,  # type: ignore[arg-type]
        handler_code_raw="async (req, res) => { const order = await Order.findByPk(req.params.orderId); await order.destroy(); }",
    )


# ── Test: valid JSON response ──────────────────────────────────────────────


class TestClassifyRouteValidResponse:
    """(a) Valid JSON response parses into correct LlmClassification."""

    def test_applicable_model(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LOGS_DIR", str(tmp_path))
        with patch("bola_sentinel.llm_reasoning.classifier.call_ollama", return_value=_VALID_LLM_JSON):
            result = classify_route(_make_route())
        assert result.applicable_model == "OWNERSHIP"

    def test_is_vulnerable_true(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LOGS_DIR", str(tmp_path))
        with patch("bola_sentinel.llm_reasoning.classifier.call_ollama", return_value=_VALID_LLM_JSON):
            result = classify_route(_make_route())
        assert result.is_vulnerable is True

    def test_confidence_high(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LOGS_DIR", str(tmp_path))
        with patch("bola_sentinel.llm_reasoning.classifier.call_ollama", return_value=_VALID_LLM_JSON):
            result = classify_route(_make_route())
        assert result.confidence == "HIGH"

    def test_requires_two_users(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LOGS_DIR", str(tmp_path))
        with patch("bola_sentinel.llm_reasoning.classifier.call_ollama", return_value=_VALID_LLM_JSON):
            result = classify_route(_make_route())
        assert result.requires_two_users is True

    def test_result_is_llm_classification(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LOGS_DIR", str(tmp_path))
        with patch("bola_sentinel.llm_reasoning.classifier.call_ollama", return_value=_VALID_LLM_JSON):
            result = classify_route(_make_route())
        assert isinstance(result, LlmClassification)


# ── Test: malformed / invalid response triggers fallback ──────────────────


class TestClassifyRouteFallback:
    """(b) Malformed response triggers fallback: is_vulnerable=False, confidence=LOW."""

    def test_non_json_triggers_fallback(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LOGS_DIR", str(tmp_path))
        with patch("bola_sentinel.llm_reasoning.classifier.call_ollama", return_value=_INVALID_LLM_RESPONSE):
            result = classify_route(_make_route())
        assert result.is_vulnerable is False
        assert result.confidence == "LOW"
        assert result.applicable_model == "NONE"

    def test_non_json_fallback_explanation_mentions_logs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LOGS_DIR", str(tmp_path))
        with patch("bola_sentinel.llm_reasoning.classifier.call_ollama", return_value=_INVALID_LLM_RESPONSE):
            result = classify_route(_make_route())
        assert "logs/llm_outputs" in result.explanation or "parsing failed" in result.explanation

    def test_partial_json_triggers_fallback(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LOGS_DIR", str(tmp_path))
        with patch("bola_sentinel.llm_reasoning.classifier.call_ollama", return_value=_PARTIAL_JSON):
            result = classify_route(_make_route())
        # Missing required fields → ValidationError → fallback
        assert result.is_vulnerable is False
        assert result.confidence == "LOW"

    def test_connection_error_triggers_fallback(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LOGS_DIR", str(tmp_path))
        with patch(
            "bola_sentinel.llm_reasoning.classifier.call_ollama",
            side_effect=RuntimeError("Cannot connect to Ollama"),
        ):
            result = classify_route(_make_route())
        assert result.is_vulnerable is False
        assert result.confidence == "LOW"


# ── Test: mandatory logging ────────────────────────────────────────────────


class TestMandatoryLogging:
    """(c) log_llm_input and log_llm_output are called exactly once per classify_route."""

    def test_log_input_called_exactly_once(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LOGS_DIR", str(tmp_path))
        with (
            patch("bola_sentinel.llm_reasoning.classifier.call_ollama", return_value=_VALID_LLM_JSON),
            patch("bola_sentinel.llm_reasoning.classifier.log_llm_input") as mock_input,
            patch("bola_sentinel.llm_reasoning.classifier.log_llm_output"),
        ):
            classify_route(_make_route())
        assert mock_input.call_count == 1

    def test_log_output_called_exactly_once(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LOGS_DIR", str(tmp_path))
        with (
            patch("bola_sentinel.llm_reasoning.classifier.call_ollama", return_value=_VALID_LLM_JSON),
            patch("bola_sentinel.llm_reasoning.classifier.log_llm_input"),
            patch("bola_sentinel.llm_reasoning.classifier.log_llm_output") as mock_output,
        ):
            classify_route(_make_route())
        assert mock_output.call_count == 1

    def test_log_output_called_exactly_once_on_fallback(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LOGS_DIR", str(tmp_path))
        with (
            patch("bola_sentinel.llm_reasoning.classifier.call_ollama", return_value=_INVALID_LLM_RESPONSE),
            patch("bola_sentinel.llm_reasoning.classifier.log_llm_input"),
            patch("bola_sentinel.llm_reasoning.classifier.log_llm_output") as mock_output,
        ):
            classify_route(_make_route())
        assert mock_output.call_count == 1

    def test_log_input_called_before_ollama(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify call ordering: log_llm_input must be called before call_ollama."""
        monkeypatch.setenv("LOGS_DIR", str(tmp_path))
        call_order: list[str] = []

        def fake_log_input(*args, **kwargs) -> None:
            call_order.append("log_input")

        def fake_ollama(*args, **kwargs) -> str:
            call_order.append("ollama")
            return _VALID_LLM_JSON

        with (
            patch("bola_sentinel.llm_reasoning.classifier.log_llm_input", side_effect=fake_log_input),
            patch("bola_sentinel.llm_reasoning.classifier.call_ollama", side_effect=fake_ollama),
            patch("bola_sentinel.llm_reasoning.classifier.log_llm_output"),
        ):
            classify_route(_make_route())

        assert call_order == ["log_input", "ollama"], (
            f"Expected log_input before ollama, got: {call_order}"
        )

    def test_log_output_called_after_ollama(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify call ordering: log_llm_output must be called after call_ollama."""
        monkeypatch.setenv("LOGS_DIR", str(tmp_path))
        call_order: list[str] = []

        def fake_ollama(*args, **kwargs) -> str:
            call_order.append("ollama")
            return _VALID_LLM_JSON

        def fake_log_output(*args, **kwargs) -> None:
            call_order.append("log_output")

        with (
            patch("bola_sentinel.llm_reasoning.classifier.log_llm_input"),
            patch("bola_sentinel.llm_reasoning.classifier.call_ollama", side_effect=fake_ollama),
            patch("bola_sentinel.llm_reasoning.classifier.log_llm_output", side_effect=fake_log_output),
        ):
            classify_route(_make_route())

        assert call_order == ["ollama", "log_output"], (
            f"Expected ollama before log_output, got: {call_order}"
        )

    def test_log_input_receives_route_id(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LOGS_DIR", str(tmp_path))
        route = _make_route(route_id="POST_/orders/{orderId}_42")
        with (
            patch("bola_sentinel.llm_reasoning.classifier.call_ollama", return_value=_VALID_LLM_JSON),
            patch("bola_sentinel.llm_reasoning.classifier.log_llm_input") as mock_input,
            patch("bola_sentinel.llm_reasoning.classifier.log_llm_output"),
        ):
            classify_route(route)
        assert mock_input.call_args.kwargs.get("route_id") == "POST_/orders/{orderId}_42" or \
               mock_input.call_args.args[0] == "POST_/orders/{orderId}_42"

    def test_log_output_receives_raw_response(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LOGS_DIR", str(tmp_path))
        with (
            patch("bola_sentinel.llm_reasoning.classifier.call_ollama", return_value=_VALID_LLM_JSON),
            patch("bola_sentinel.llm_reasoning.classifier.log_llm_input"),
            patch("bola_sentinel.llm_reasoning.classifier.log_llm_output") as mock_output,
        ):
            classify_route(_make_route())
        # Check raw_response arg is the actual response text
        args = mock_output.call_args
        raw = args.kwargs.get("raw_response") or args.args[1]
        assert raw == _VALID_LLM_JSON

    def test_log_output_parsed_successfully_true_for_valid(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LOGS_DIR", str(tmp_path))
        with (
            patch("bola_sentinel.llm_reasoning.classifier.call_ollama", return_value=_VALID_LLM_JSON),
            patch("bola_sentinel.llm_reasoning.classifier.log_llm_input"),
            patch("bola_sentinel.llm_reasoning.classifier.log_llm_output") as mock_output,
        ):
            classify_route(_make_route())
        args = mock_output.call_args
        parsed_ok = args.kwargs.get("parsed_successfully") or args.args[2]
        assert parsed_ok is True

    def test_log_output_parsed_successfully_false_for_invalid(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LOGS_DIR", str(tmp_path))
        with (
            patch("bola_sentinel.llm_reasoning.classifier.call_ollama", return_value=_INVALID_LLM_RESPONSE),
            patch("bola_sentinel.llm_reasoning.classifier.log_llm_input"),
            patch("bola_sentinel.llm_reasoning.classifier.log_llm_output") as mock_output,
        ):
            classify_route(_make_route())
        args = mock_output.call_args
        # log_llm_output may be called with keyword-only args; fall back to
        # positional index only if kwargs is empty.
        if "parsed_successfully" in args.kwargs:
            parsed_ok = args.kwargs["parsed_successfully"]
        else:
            parsed_ok = args.args[2]
        assert parsed_ok is False


# ── Test: classify_all_routes filtering ───────────────────────────────────


class TestClassifyAllRoutes:
    """(d/e) PRESENT routes pass through; ABSENT/UNCERTAIN routes go to LLM."""

    def test_present_route_skipped_no_llm_call(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """(d) PRESENT route must have llm_classification=None and no LLM call."""
        monkeypatch.setenv("LOGS_DIR", str(tmp_path))
        route = _make_route(auth_check_status="PRESENT")
        with patch("bola_sentinel.llm_reasoning.classifier.call_ollama") as mock_ollama:
            results = classify_all_routes([route])
        assert mock_ollama.call_count == 0
        assert results[0].llm_classification is None

    def test_absent_route_sent_to_llm(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """(e) ABSENT route must trigger exactly one LLM call."""
        monkeypatch.setenv("LOGS_DIR", str(tmp_path))
        route = _make_route(auth_check_status="ABSENT")
        with (
            patch("bola_sentinel.llm_reasoning.classifier.call_ollama", return_value=_VALID_LLM_JSON),
            patch("bola_sentinel.llm_reasoning.classifier.log_llm_input"),
            patch("bola_sentinel.llm_reasoning.classifier.log_llm_output"),
        ):
            results = classify_all_routes([route])
        assert results[0].llm_classification is not None

    def test_uncertain_route_sent_to_llm(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """(e) UNCERTAIN route must also trigger an LLM call."""
        monkeypatch.setenv("LOGS_DIR", str(tmp_path))
        route = _make_route(auth_check_status="UNCERTAIN")
        with (
            patch("bola_sentinel.llm_reasoning.classifier.call_ollama", return_value=_VALID_LLM_JSON),
            patch("bola_sentinel.llm_reasoning.classifier.log_llm_input"),
            patch("bola_sentinel.llm_reasoning.classifier.log_llm_output"),
        ):
            results = classify_all_routes([route])
        assert results[0].llm_classification is not None

    def test_mixed_routes_correct_llm_call_count(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Only ABSENT + UNCERTAIN routes consume an LLM call each."""
        monkeypatch.setenv("LOGS_DIR", str(tmp_path))
        routes = [
            _make_route(auth_check_status="ABSENT",    route_id="r1"),
            _make_route(auth_check_status="PRESENT",   route_id="r2"),
            _make_route(auth_check_status="UNCERTAIN",  route_id="r3"),
            _make_route(auth_check_status="PRESENT",   route_id="r4"),
        ]
        with (
            patch("bola_sentinel.llm_reasoning.classifier.call_ollama", return_value=_VALID_LLM_JSON) as mock_ollama,
            patch("bola_sentinel.llm_reasoning.classifier.log_llm_input"),
            patch("bola_sentinel.llm_reasoning.classifier.log_llm_output"),
        ):
            results = classify_all_routes(routes)
        assert mock_ollama.call_count == 2  # r1 (ABSENT) + r3 (UNCERTAIN)
        assert results[1].llm_classification is None   # r2 PRESENT
        assert results[3].llm_classification is None   # r4 PRESENT

    def test_output_is_classified_route_instances(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LOGS_DIR", str(tmp_path))
        routes = [_make_route(auth_check_status="ABSENT")]
        with (
            patch("bola_sentinel.llm_reasoning.classifier.call_ollama", return_value=_VALID_LLM_JSON),
            patch("bola_sentinel.llm_reasoning.classifier.log_llm_input"),
            patch("bola_sentinel.llm_reasoning.classifier.log_llm_output"),
        ):
            results = classify_all_routes(routes)
        assert all(isinstance(r, ClassifiedRoute) for r in results)

    def test_result_preserves_static_fields(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ClassifiedRoute must carry all fields from StaticAnalysisResult unchanged."""
        monkeypatch.setenv("LOGS_DIR", str(tmp_path))
        route = _make_route(route_path="/orders/{orderId}/cancel", auth_check_status="ABSENT")
        with (
            patch("bola_sentinel.llm_reasoning.classifier.call_ollama", return_value=_VALID_LLM_JSON),
            patch("bola_sentinel.llm_reasoning.classifier.log_llm_input"),
            patch("bola_sentinel.llm_reasoning.classifier.log_llm_output"),
        ):
            results = classify_all_routes([route])
        assert results[0].route_path == "/orders/{orderId}/cancel"
        assert results[0].line_number == 42
        assert results[0].language == "javascript"

    def test_empty_input_returns_empty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LOGS_DIR", str(tmp_path))
        results = classify_all_routes([])
        assert results == []


# ── Test: logger writes files to disk ─────────────────────────────────────


class TestLoggerFileOutput:
    """Verify that logger.py actually writes files when called directly."""

    def test_log_llm_input_creates_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LOGS_DIR", str(tmp_path))
        from bola_sentinel.llm_reasoning.logger import log_llm_input

        path = log_llm_input(
            route_id="TEST_route_1",
            system_prompt="sys",
            user_prompt="user",
        )
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["route_id"] == "TEST_route_1"
        assert data["system_prompt"] == "sys"
        assert data["user_prompt"] == "user"
        assert "timestamp" in data

    def test_log_llm_output_creates_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LOGS_DIR", str(tmp_path))
        from bola_sentinel.llm_reasoning.logger import log_llm_output

        path = log_llm_output(
            route_id="TEST_route_2",
            raw_response=_VALID_LLM_JSON,
            parsed_successfully=True,
        )
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["route_id"] == "TEST_route_2"
        assert data["raw_response"] == _VALID_LLM_JSON
        assert data["parsed_successfully"] is True

    def test_log_input_file_in_llm_inputs_subdir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LOGS_DIR", str(tmp_path))
        from bola_sentinel.llm_reasoning.logger import log_llm_input

        path = log_llm_input("route_x", "s", "u")
        assert "llm_inputs" in str(path)

    def test_log_output_file_in_llm_outputs_subdir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LOGS_DIR", str(tmp_path))
        from bola_sentinel.llm_reasoning.logger import log_llm_output

        path = log_llm_output("route_y", "raw", False)
        assert "llm_outputs" in str(path)
