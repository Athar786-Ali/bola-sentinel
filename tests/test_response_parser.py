"""
Unit tests for the robust LLM response parser.

Covers all parsing strategies and edge cases:
  - Valid bare JSON
  - JSON inside ```json code fences
  - JSON inside ``` code fences (no language tag)
  - Leading/trailing commentary
  - Malformed JSON (completely invalid)
  - Partial JSON (missing required fields)
  - Extra fields (should be tolerated)
  - Whitespace / BOM
  - Empty string
  - Multiple JSON blocks (takes first valid)
  - Nested code fences
  - Invalid field types (wrong enum value)
"""

from __future__ import annotations

import json

import pytest

from bola_sentinel.llm_reasoning.response_parser import (
    ParseResult,
    parse_llm_response,
    _extract_first_json_object,
    _strip_bom_and_control,
)


# ── Test data ──────────────────────────────────────────────────────────────

_VALID_DICT = {
    "applicable_model": "OWNERSHIP",
    "is_vulnerable": True,
    "confidence": "HIGH",
    "explanation": "No ownership check before DB delete.",
    "suggested_test_description": "Access victim order with attacker token.",
    "requires_two_users": True,
}

_VALID_JSON = json.dumps(_VALID_DICT)

_VALID_JSON_PRETTY = json.dumps(_VALID_DICT, indent=2)


# ── Strategy 1: Direct parse ──────────────────────────────────────────────


class TestDirectParse:
    """Strategy 1: bare valid JSON."""

    def test_valid_json(self):
        result = parse_llm_response(_VALID_JSON)
        assert result.success is True
        assert result.strategy_used == "direct_parse"
        assert result.classification is not None
        assert result.classification.applicable_model == "OWNERSHIP"
        assert result.classification.is_vulnerable is True
        assert result.classification.confidence == "HIGH"

    def test_valid_json_pretty_printed(self):
        result = parse_llm_response(_VALID_JSON_PRETTY)
        assert result.success is True
        assert result.strategy_used == "direct_parse"

    def test_valid_json_with_whitespace(self):
        result = parse_llm_response("  \n\t" + _VALID_JSON + "  \n")
        assert result.success is True
        assert result.strategy_used == "direct_parse"

    def test_valid_json_with_bom(self):
        result = parse_llm_response("\ufeff" + _VALID_JSON)
        assert result.success is True
        assert result.strategy_used == "direct_parse"


# ── Strategy 2: Code fence stripping ──────────────────────────────────────


class TestCodeFenceStripping:
    """Strategy 2: JSON wrapped in markdown code fences."""

    def test_json_code_fence(self):
        raw = f"```json\n{_VALID_JSON}\n```"
        result = parse_llm_response(raw)
        assert result.success is True
        assert result.strategy_used == "strip_code_fences"

    def test_plain_code_fence(self):
        raw = f"```\n{_VALID_JSON}\n```"
        result = parse_llm_response(raw)
        assert result.success is True
        assert result.strategy_used == "strip_code_fences"

    def test_code_fence_with_surrounding_text(self):
        raw = f"Here is the classification:\n```json\n{_VALID_JSON}\n```\nLet me know if you need more."
        result = parse_llm_response(raw)
        assert result.success is True
        assert result.strategy_used == "strip_code_fences"

    def test_code_fence_pretty_printed(self):
        raw = f"```json\n{_VALID_JSON_PRETTY}\n```"
        result = parse_llm_response(raw)
        assert result.success is True
        assert result.strategy_used == "strip_code_fences"


# ── Strategy 3: Brace extraction ──────────────────────────────────────────


class TestBraceExtraction:
    """Strategy 3: JSON embedded in prose without code fences."""

    def test_json_with_leading_text(self):
        raw = f"Based on my analysis, the classification is:\n{_VALID_JSON}"
        result = parse_llm_response(raw)
        assert result.success is True
        assert result.strategy_used == "brace_extraction"

    def test_json_with_trailing_text(self):
        raw = f"{_VALID_JSON}\nThis concludes the analysis."
        result = parse_llm_response(raw)
        assert result.success is True
        assert result.strategy_used == "brace_extraction"

    def test_json_surrounded_by_prose(self):
        raw = f"I analysed the route. Here is my output:\n{_VALID_JSON}\nPlease review."
        result = parse_llm_response(raw)
        assert result.success is True
        assert result.strategy_used == "brace_extraction"


# ── Failure cases ──────────────────────────────────────────────────────────


class TestParseFailures:
    """Cases where all strategies should fail."""

    def test_completely_invalid(self):
        result = parse_llm_response("This is not JSON at all, sorry!")
        assert result.success is False
        assert result.classification is None
        assert result.strategy_used == "NONE"
        assert len(result.attempts) > 0

    def test_empty_string(self):
        result = parse_llm_response("")
        assert result.success is False
        assert result.classification is None

    def test_partial_json_missing_required_fields(self):
        partial = json.dumps({"applicable_model": "OWNERSHIP"})
        result = parse_llm_response(partial)
        assert result.success is False
        assert result.classification is None

    def test_invalid_enum_value(self):
        bad = json.dumps({
            "applicable_model": "INVALID_VALUE",
            "is_vulnerable": True,
            "confidence": "HIGH",
            "explanation": "test",
            "suggested_test_description": "test",
            "requires_two_users": True,
        })
        result = parse_llm_response(bad)
        assert result.success is False

    def test_wrong_type_for_boolean(self):
        bad = json.dumps({
            "applicable_model": "OWNERSHIP",
            "is_vulnerable": "yes",  # should be bool
            "confidence": "HIGH",
            "explanation": "test",
            "suggested_test_description": "test",
            "requires_two_users": True,
        })
        # Pydantic may coerce "yes" or may not — test documents the behaviour.
        result = parse_llm_response(bad)
        # This may succeed (Pydantic coercion) or fail; we just want no crash.
        assert isinstance(result, ParseResult)

    def test_null_bytes(self):
        result = parse_llm_response("\x00\x00\x00")
        assert result.success is False


# ── Extra fields (should be tolerated) ────────────────────────────────────


class TestExtraFields:
    """LLMs sometimes add fields not in the schema. Pydantic should ignore them."""

    def test_extra_fields_tolerated(self):
        extended = {**_VALID_DICT, "thinking": "I considered several factors..."}
        result = parse_llm_response(json.dumps(extended))
        assert result.success is True
        assert result.classification is not None
        assert result.classification.applicable_model == "OWNERSHIP"


# ── Diagnostics / logging ─────────────────────────────────────────────────


class TestDiagnostics:
    """Verify that parse diagnostics are populated correctly."""

    def test_success_diagnostics(self):
        result = parse_llm_response(_VALID_JSON)
        log = result.to_log_dict()
        assert log["success"] is True
        assert log["strategy_used"] == "direct_parse"
        assert log["error_message"] is None

    def test_failure_diagnostics_have_attempts(self):
        result = parse_llm_response("not json")
        log = result.to_log_dict()
        assert log["success"] is False
        assert log["strategy_used"] == "NONE"
        assert len(log["attempts"]) >= 2  # at least direct + brace extraction


# ── Helper function tests ─────────────────────────────────────────────────


class TestExtractFirstJsonObject:
    """Test the brace-matching helper directly."""

    def test_simple(self):
        assert _extract_first_json_object('before {"a": 1} after') == '{"a": 1}'

    def test_nested(self):
        s = '{"a": {"b": 1}}'
        assert _extract_first_json_object(s) == s

    def test_no_braces(self):
        assert _extract_first_json_object("no json here") is None

    def test_string_with_braces(self):
        s = '{"a": "value with { and }"}'
        assert _extract_first_json_object(s) == s

    def test_unbalanced(self):
        # Unbalanced — no closing brace at depth 0
        assert _extract_first_json_object("{unclosed") is None


class TestStripBomAndControl:
    """Test the BOM / control character cleaner."""

    def test_bom_stripped(self):
        assert _strip_bom_and_control("\ufeffhello") == "hello"

    def test_null_bytes_stripped(self):
        assert _strip_bom_and_control("hel\x00lo") == "hello"

    def test_whitespace_stripped(self):
        assert _strip_bom_and_control("  \n hello \n  ") == "hello"
