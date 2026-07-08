"""
Pytest tests for the bola-sentinel dynamic verification layer.

Uses httpx's built-in mock transport (no real network calls).
settings.logs_dir is patched globally by tests/conftest.py autouse fixture.

Coverage
--------
(a) 200 response + differing before/after state → CONFIRMED_VULNERABLE
(b) 200 response + identical before/after state → NOT_VULNERABLE
(c) 403 response → NOT_VULNERABLE
(d) 200 + no state baseline + no denial language → CONFIRMED_VULNERABLE (weak)
(e) 200 + denial in body → NOT_VULNERABLE
(f) Connection error → INCONCLUSIVE
(g) No matching object type → INCONCLUSIVE
(h) evidence_logger writes a complete JSON log file for every case
(i) test_user_loader validates structure and raises on missing fields
(j) states_differ unit tests (True / False / None tri-state)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from bola_sentinel.dynamic_verification.executor import execute_verification
from bola_sentinel.dynamic_verification.state_checker import states_differ
from bola_sentinel.dynamic_verification.test_user_loader import load_test_users
from bola_sentinel.models.schemas import (
    ClassifiedRoute,
    DbOperation,
    LlmClassification,
    ObjectIdParam,
)

# ── Shared test data ───────────────────────────────────────────────────────

_BASE_URL = "http://localhost:3000"

_TEST_USERS: dict = {
    "user_a": {
        "auth_header": "Bearer token_a",
        "user_id": "1",
        "owned_object_ids": {
            "orders": ["10"],
            "projects": ["20"],
        },
    },
    "user_b": {
        "auth_header": "Bearer token_b",
        "user_id": "2",
        "owned_object_ids": {
            "orders": ["12"],
            "projects": ["21"],
        },
    },
}


def _make_classified_route(
    route_path: str = "/orders/{orderId}/cancel",
    http_method: str = "POST",
    route_id: str | None = None,
) -> ClassifiedRoute:
    """Build a minimal ClassifiedRoute fixture with is_vulnerable=True."""
    if route_id is None:
        route_id = f"{http_method}_{route_path}_42"
    return ClassifiedRoute(
        route_id=route_id,
        http_method=http_method,  # type: ignore[arg-type]
        route_path=route_path,
        file_path="routes.js",
        line_number=42,
        language="javascript",
        object_id_params=[ObjectIdParam(name="orderId", location="path")],
        db_operations=[DbOperation(operation_type="UPDATE", snippet="order.update()")],
        auth_check_status="ABSENT",
        handler_code_raw="async (req, res) => { ... }",
        llm_classification=LlmClassification(
            applicable_model="OWNERSHIP",
            is_vulnerable=True,
            confidence="HIGH",
            explanation="No ownership check found.",
            suggested_test_description="Access victim order with attacker token.",
            requires_two_users=True,
        ),
    )


# ── Helper: sequential mock httpx.Client ──────────────────────────────────

def _make_mock_client(responses: list[tuple[int, Any]]) -> MagicMock:
    """
    Build a MagicMock httpx.Client whose .get() and .request() methods
    return httpx.Response objects drawn sequentially from *responses*.
    """
    client = MagicMock(spec=httpx.Client)
    call_count = [0]

    def _make_response(status_code: int, body: Any) -> httpx.Response:
        if isinstance(body, dict):
            content = json.dumps(body).encode()
            headers = {"content-type": "application/json"}
        else:
            content = str(body).encode()
            headers = {"content-type": "text/plain"}
        return httpx.Response(status_code, content=content, headers=headers)

    def _next_response(*args, **kwargs) -> httpx.Response:
        idx = call_count[0]
        if idx >= len(responses):
            raise RuntimeError(f"Unexpected call #{idx + 1}: args={args}")
        call_count[0] += 1
        sc, body = responses[idx]
        return _make_response(sc, body)

    client.get.side_effect = _next_response
    client.request.side_effect = _next_response
    return client


# ── (a) 200 + state changed → CONFIRMED_VULNERABLE ───────────────────────


class TestConfirmedVulnerableWithStateChange:
    """(a) 200 + before≠after → CONFIRMED_VULNERABLE (strong evidence)."""

    def _make_client(self) -> MagicMock:
        return _make_mock_client([
            (200, {"status": "active"}),      # GET before-state
            (200, {"status": "cancelled"}),   # POST attack
            (200, {"status": "cancelled"}),   # GET after-state
        ])

    def test_verdict(self, tmp_path: Path) -> None:
        result = execute_verification(
            _make_classified_route(), _TEST_USERS, _BASE_URL, client=self._make_client()
        )
        assert result.verification_status == "CONFIRMED_VULNERABLE"

    def test_object_state_changed_true(self, tmp_path: Path) -> None:
        result = execute_verification(
            _make_classified_route(), _TEST_USERS, _BASE_URL, client=self._make_client()
        )
        assert result.object_state_changed is True

    def test_http_status_recorded(self, tmp_path: Path) -> None:
        result = execute_verification(
            _make_classified_route(), _TEST_USERS, _BASE_URL, client=self._make_client()
        )
        assert result.http_status_received == 200

    def test_victim_object_id_recorded(self, tmp_path: Path) -> None:
        result = execute_verification(
            _make_classified_route(), _TEST_USERS, _BASE_URL, client=self._make_client()
        )
        assert result.victim_object_id == "12"  # user_b's first order id


# ── (b) 200 + state unchanged → NOT_VULNERABLE ───────────────────────────


class TestNotVulnerableStateUnchanged:
    """(b) 200 + before==after → NOT_VULNERABLE (accepted but no-op)."""

    def _make_client(self) -> MagicMock:
        same = {"status": "active", "id": "12"}
        return _make_mock_client([(200, same), (200, same), (200, same)])

    def test_verdict(self, tmp_path: Path) -> None:
        result = execute_verification(
            _make_classified_route(), _TEST_USERS, _BASE_URL, client=self._make_client()
        )
        assert result.verification_status == "NOT_VULNERABLE"

    def test_object_state_changed_false(self, tmp_path: Path) -> None:
        result = execute_verification(
            _make_classified_route(), _TEST_USERS, _BASE_URL, client=self._make_client()
        )
        assert result.object_state_changed is False


# ── (c) 403 response → NOT_VULNERABLE ────────────────────────────────────


class TestNotVulnerable403:
    """(c) 403 → NOT_VULNERABLE regardless of state."""

    def test_verdict(self, tmp_path: Path) -> None:
        client = _make_mock_client([
            (200, {"status": "active"}),
            (403, {"error": "Forbidden"}),
        ])
        result = execute_verification(
            _make_classified_route(), _TEST_USERS, _BASE_URL, client=client
        )
        assert result.verification_status == "NOT_VULNERABLE"

    def test_http_status_recorded(self, tmp_path: Path) -> None:
        client = _make_mock_client([
            (200, {"status": "active"}),
            (403, {"error": "Forbidden"}),
        ])
        result = execute_verification(
            _make_classified_route(), _TEST_USERS, _BASE_URL, client=client
        )
        assert result.http_status_received == 403

    def test_401_also_not_vulnerable(self, tmp_path: Path) -> None:
        client = _make_mock_client([
            (200, {"status": "active"}),
            (401, {"error": "Unauthorized"}),
        ])
        result = execute_verification(
            _make_classified_route(), _TEST_USERS, _BASE_URL, client=client
        )
        assert result.verification_status == "NOT_VULNERABLE"


# ── (d) 200 + no baseline → CONFIRMED_VULNERABLE (weak) ──────────────────


class TestConfirmedVulnerableWeakEvidence:
    """(d) 200 + no state-check baseline + no denial language → weak CONFIRMED."""

    def _make_client(self) -> MagicMock:
        return _make_mock_client([
            (500, "Internal error"),     # GET before fails → no baseline
            (200, {"cancelled": True}),  # POST attack accepted cleanly
        ])

    def test_verdict(self, tmp_path: Path) -> None:
        result = execute_verification(
            _make_classified_route(), _TEST_USERS, _BASE_URL, client=self._make_client()
        )
        assert result.verification_status == "CONFIRMED_VULNERABLE"

    def test_object_state_changed_none(self, tmp_path: Path) -> None:
        result = execute_verification(
            _make_classified_route(), _TEST_USERS, _BASE_URL, client=self._make_client()
        )
        assert result.object_state_changed is None

    def test_notes_mention_weak_evidence(self, tmp_path: Path) -> None:
        result = execute_verification(
            _make_classified_route(), _TEST_USERS, _BASE_URL, client=self._make_client()
        )
        assert "WEAK" in result.notes or "state" in result.notes.lower()


# ── (e) 200 + denial body → NOT_VULNERABLE ────────────────────────────────


class TestNotVulnerableDenialBody:
    """(e) 200 but body contains denial language → NOT_VULNERABLE."""

    def test_verdict(self, tmp_path: Path) -> None:
        client = _make_mock_client([
            (500, "error"),                                      # before fails
            (200, "access denied: you do not have permission"),  # 200 with denial
        ])
        result = execute_verification(
            _make_classified_route(), _TEST_USERS, _BASE_URL, client=client
        )
        assert result.verification_status == "NOT_VULNERABLE"


# ── (f) Connection error → INCONCLUSIVE ───────────────────────────────────


class TestInconclusiveConnectionError:
    """(f) ConnectError during attack probe → INCONCLUSIVE."""

    def _make_client(self, *, connect_error: bool = True) -> MagicMock:
        client = MagicMock(spec=httpx.Client)
        client.get.return_value = httpx.Response(
            200,
            content=b'{"status":"active"}',
            headers={"content-type": "application/json"},
        )
        if connect_error:
            client.request.side_effect = httpx.ConnectError("Connection refused")
        return client

    def test_verdict(self, tmp_path: Path) -> None:
        result = execute_verification(
            _make_classified_route(), _TEST_USERS, _BASE_URL, client=self._make_client()
        )
        assert result.verification_status == "INCONCLUSIVE"

    def test_notes_mention_unreachable(self, tmp_path: Path) -> None:
        result = execute_verification(
            _make_classified_route(), _TEST_USERS, _BASE_URL, client=self._make_client()
        )
        assert "unreachable" in result.notes.lower()


# ── (g) No matching object type → INCONCLUSIVE ────────────────────────────


class TestInconclusiveNoMatchingObjectType:
    """(g) Route path has no matching resource in user_b.owned_object_ids."""

    def test_verdict(self, tmp_path: Path) -> None:
        route = _make_classified_route(route_path="/invoices/{invoiceId}/void")
        result = execute_verification(route, _TEST_USERS, _BASE_URL)
        assert result.verification_status == "INCONCLUSIVE"

    def test_notes_describe_issue(self, tmp_path: Path) -> None:
        route = _make_classified_route(route_path="/invoices/{invoiceId}/void")
        result = execute_verification(route, _TEST_USERS, _BASE_URL)
        assert "object" in result.notes.lower() or "matching" in result.notes.lower()


# ── (h) Evidence logger writes a complete log file for every case ──────────


class TestEvidenceLoggerCompleteness:
    """(h) Every execute_verification call produces a complete JSON evidence file."""

    def _get_log(self, tmp_path: Path) -> dict:
        logs = list((tmp_path / "logs" / "verification_logs").glob("*.json"))
        assert len(logs) == 1, f"Expected 1 log file, found {len(logs)}: {logs}"
        return json.loads(logs[0].read_text())

    def test_log_file_created_for_confirmed_vulnerable(self, tmp_path: Path) -> None:
        client = _make_mock_client([
            (200, {"s": "a"}), (200, {"s": "b"}), (200, {"s": "b"})
        ])
        execute_verification(_make_classified_route(), _TEST_USERS, _BASE_URL, client=client)
        data = self._get_log(tmp_path)
        assert data["final_verdict"] == "CONFIRMED_VULNERABLE"

    def test_log_file_created_for_not_vulnerable(self, tmp_path: Path) -> None:
        client = _make_mock_client([
            (200, {"s": "a"}), (403, "Forbidden")
        ])
        execute_verification(_make_classified_route(), _TEST_USERS, _BASE_URL, client=client)
        data = self._get_log(tmp_path)
        assert data["final_verdict"] == "NOT_VULNERABLE"

    def test_log_file_created_for_inconclusive(self, tmp_path: Path) -> None:
        route = _make_classified_route(route_path="/invoices/{invoiceId}/void")
        execute_verification(route, _TEST_USERS, _BASE_URL)
        data = self._get_log(tmp_path)
        assert data["final_verdict"] == "INCONCLUSIVE"

    def test_log_contains_required_fields(self, tmp_path: Path) -> None:
        client = _make_mock_client([
            (200, {"s": "active"}), (200, {"s": "cancelled"}), (200, {"s": "cancelled"})
        ])
        execute_verification(_make_classified_route(), _TEST_USERS, _BASE_URL, client=client)
        data = self._get_log(tmp_path)
        for field in ("route_id", "timestamp", "final_verdict", "attack_request", "response", "state_check"):
            assert field in data, f"Missing required field: {field}"

    def test_log_attack_request_has_url(self, tmp_path: Path) -> None:
        client = _make_mock_client([
            (200, {"s": "a"}), (200, {"s": "b"}), (200, {"s": "b"})
        ])
        execute_verification(_make_classified_route(), _TEST_USERS, _BASE_URL, client=client)
        data = self._get_log(tmp_path)
        assert "url" in data["attack_request"]

    def test_log_redacts_auth_header(self, tmp_path: Path) -> None:
        client = _make_mock_client([
            (200, {"s": "a"}), (200, {"s": "b"}), (200, {"s": "b"})
        ])
        execute_verification(_make_classified_route(), _TEST_USERS, _BASE_URL, client=client)
        data = self._get_log(tmp_path)
        auth_val = data["attack_request"]["headers"].get("Authorization", "")
        assert auth_val == "<redacted>", f"Auth header not redacted: {auth_val!r}"

    def test_log_contains_response_status(self, tmp_path: Path) -> None:
        client = _make_mock_client([
            (200, {"s": "a"}), (200, {"s": "b"}), (200, {"s": "b"})
        ])
        execute_verification(_make_classified_route(), _TEST_USERS, _BASE_URL, client=client)
        data = self._get_log(tmp_path)
        assert data["response"]["status_code"] == 200

    def test_log_state_check_has_before_and_after(self, tmp_path: Path) -> None:
        client = _make_mock_client([
            (200, {"s": "active"}), (200, {"s": "cancel"}), (200, {"s": "cancel"})
        ])
        execute_verification(_make_classified_route(), _TEST_USERS, _BASE_URL, client=client)
        data = self._get_log(tmp_path)
        assert "before" in data["state_check"]
        assert "after" in data["state_check"]


# ── (i) test_user_loader validates structure ───────────────────────────────


class TestUserLoaderValidation:
    """(i) load_test_users raises descriptive errors on malformed input."""

    def test_missing_file_raises_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="test_users.json"):
            load_test_users(str(tmp_path / "nonexistent.json"))

    def test_invalid_json_raises_value_error(self, tmp_path: Path) -> None:
        bad = tmp_path / "test_users.json"
        bad.write_text("not valid json!!!")
        with pytest.raises(ValueError, match="not valid JSON"):
            load_test_users(str(bad))

    def test_missing_user_a_raises(self, tmp_path: Path) -> None:
        incomplete = {"user_b": _TEST_USERS["user_b"]}
        (tmp_path / "test_users.json").write_text(json.dumps(incomplete))
        with pytest.raises(ValueError, match="user_a"):
            load_test_users(str(tmp_path / "test_users.json"))

    def test_missing_auth_header_raises(self, tmp_path: Path) -> None:
        bad = {
            "user_a": {"user_id": "1", "owned_object_ids": {}},
            "user_b": _TEST_USERS["user_b"],
        }
        (tmp_path / "test_users.json").write_text(json.dumps(bad))
        with pytest.raises(ValueError, match="auth_header"):
            load_test_users(str(tmp_path / "test_users.json"))

    def test_valid_file_returns_dict(self, tmp_path: Path) -> None:
        (tmp_path / "test_users.json").write_text(json.dumps(_TEST_USERS))
        result = load_test_users(str(tmp_path / "test_users.json"))
        assert result["user_a"]["user_id"] == "1"


# ── (j) states_differ unit tests ──────────────────────────────────────────


class TestStatesDiffer:
    """(j) Tri-state semantics of the states_differ function."""

    def test_both_none_returns_none(self) -> None:
        assert states_differ(None, None) is None

    def test_before_none_returns_none(self) -> None:
        assert states_differ(None, {"x": 1}) is None

    def test_after_none_returns_none(self) -> None:
        assert states_differ({"x": 1}, None) is None

    def test_identical_dicts_returns_false(self) -> None:
        assert states_differ({"status": "active"}, {"status": "active"}) is False

    def test_different_dicts_returns_true(self) -> None:
        assert states_differ({"status": "active"}, {"status": "cancelled"}) is True

    def test_after_gone_returns_true(self) -> None:
        assert states_differ(
            {"status": "active"},
            {"_gone": True, "_bola_sentinel_status": 404}
        ) is True

    def test_timestamp_noise_ignored(self) -> None:
        before = {"status": "active", "updatedAt": "2024-01-01"}
        after = {"status": "active", "updatedAt": "2024-01-02"}
        assert states_differ(before, after) is False

    def test_nested_change_detected(self) -> None:
        before = {"data": {"role": "user"}}
        after = {"data": {"role": "admin"}}
        assert states_differ(before, after) is True
