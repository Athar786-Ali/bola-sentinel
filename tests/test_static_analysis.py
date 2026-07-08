"""
Pytest tests for the bola-sentinel static analysis engine.

Tests two hand-written fixtures:
  - tests/fixtures/flask_app/app.py  (Python / Flask)
  - tests/fixtures/express_app/routes.js  (JavaScript / Express)

Each fixture contains:
  - VULNERABLE routes (no ownership check, state-changing)
  - SAFE routes (ownership check present)
  - A GET route (must be excluded entirely)

The tests verify that the analyzer:
  1. Finds the expected number of state-changing routes
  2. Does NOT include GET routes
  3. Correctly classifies auth_check_status (ABSENT vs PRESENT)
  4. Detects path-parameter object-id params
  5. Preserves POST routes even when they have no obvious DB operations
  6. Produces valid StaticAnalysisResult objects
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bola_sentinel.models.schemas import StaticAnalysisResult
from bola_sentinel.static_analysis import analyze_codebase

# ── Fixture paths ──────────────────────────────────────────────────────────

_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
_FLASK_DIR = _FIXTURES_DIR / "flask_app"
_EXPRESS_DIR = _FIXTURES_DIR / "express_app"


# ── Flask tests ────────────────────────────────────────────────────────────


class TestFlaskApp:
    """Tests against tests/fixtures/flask_app/app.py."""

    @pytest.fixture(autouse=True)
    def _analyze(self) -> None:
        self.results = analyze_codebase(str(_FLASK_DIR))
        # Index by route_path substring for easier assertions.
        self.by_path: dict[str, list[StaticAnalysisResult]] = {}
        for r in self.results:
            self.by_path.setdefault(r.route_path, []).append(r)

    def test_returns_valid_schema_objects(self) -> None:
        """Every result must be a StaticAnalysisResult instance."""
        for r in self.results:
            assert isinstance(r, StaticAnalysisResult)

    def test_excludes_get_routes(self) -> None:
        """GET /projects must NOT appear (GET is not state-changing)."""
        methods = {r.http_method for r in self.results}
        assert "GET" not in methods, f"GET found in results: {methods}"

    def test_finds_all_state_changing_routes(self) -> None:
        """
        Expect exactly 4 state-changing routes:
          POST /projects/<project_id>/archive
          DELETE /projects/<project_id>
          PUT /projects/<project_id>
          PATCH /users/<user_id>/role
        """
        assert len(self.results) == 4, (
            f"Expected 4 routes, got {len(self.results)}: "
            f"{[(r.http_method, r.route_path) for r in self.results]}"
        )

    def test_vulnerable_post_route_has_absent_auth(self) -> None:
        """POST /projects/<project_id>/archive should have auth_check_status=ABSENT."""
        archive_routes = [
            r for r in self.results
            if "archive" in r.route_path and r.http_method == "POST"
        ]
        assert len(archive_routes) == 1, f"Expected 1 archive route, got {archive_routes}"
        assert archive_routes[0].auth_check_status == "ABSENT"

    def test_safe_delete_route_has_present_auth(self) -> None:
        """DELETE /projects/<project_id> should have auth_check_status=PRESENT."""
        delete_routes = [
            r for r in self.results
            if r.http_method == "DELETE" and "project" in r.route_path.lower()
        ]
        assert len(delete_routes) == 1
        assert delete_routes[0].auth_check_status == "PRESENT"

    def test_vulnerable_patch_has_absent_auth(self) -> None:
        """PATCH /users/<user_id>/role should have auth_check_status=ABSENT."""
        patch_routes = [
            r for r in self.results
            if r.http_method == "PATCH" and "role" in r.route_path
        ]
        assert len(patch_routes) == 1
        assert patch_routes[0].auth_check_status == "ABSENT"

    def test_safe_put_has_present_or_uncertain_auth(self) -> None:
        """PUT /projects/<project_id> uses filter_by — should be PRESENT or UNCERTAIN."""
        put_routes = [
            r for r in self.results
            if r.http_method == "PUT" and "project" in r.route_path.lower()
        ]
        assert len(put_routes) == 1
        assert put_routes[0].auth_check_status in ("PRESENT", "UNCERTAIN")

    def test_path_params_detected(self) -> None:
        """Archive route must detect 'project_id' as a path parameter."""
        archive = [r for r in self.results if "archive" in r.route_path][0]
        param_names = {p.name for p in archive.object_id_params}
        assert "project_id" in param_names

    def test_post_route_preserved_with_or_without_db_ops(self) -> None:
        """POST routes must never be silently dropped, even with empty db_operations."""
        post_routes = [r for r in self.results if r.http_method == "POST"]
        assert len(post_routes) >= 1, "POST routes were dropped"

    def test_route_id_format(self) -> None:
        """route_id must follow the f'{method}_{path}_{line}' pattern."""
        for r in self.results:
            assert r.route_id.startswith(r.http_method + "_")
            assert r.route_id.endswith(f"_{r.line_number}")

    def test_serialization_roundtrip(self) -> None:
        """Results must survive JSON serialisation and deserialisation."""
        for r in self.results:
            data = r.model_dump(mode="json")
            json_str = json.dumps(data)
            restored = StaticAnalysisResult.model_validate_json(json_str)
            assert restored.route_id == r.route_id
            assert restored.http_method == r.http_method


# ── Express tests ──────────────────────────────────────────────────────────


class TestExpressApp:
    """Tests against tests/fixtures/express_app/routes.js."""

    @pytest.fixture(autouse=True)
    def _analyze(self) -> None:
        self.results = analyze_codebase(str(_EXPRESS_DIR))

    def test_returns_valid_schema_objects(self) -> None:
        for r in self.results:
            assert isinstance(r, StaticAnalysisResult)

    def test_excludes_get_routes(self) -> None:
        methods = {r.http_method for r in self.results}
        assert "GET" not in methods

    def test_finds_all_state_changing_routes(self) -> None:
        """
        Expect exactly 4 state-changing routes:
          POST /orders/:orderId/cancel
          DELETE /orders/:orderId
          PUT /orders/:orderId
          PATCH /users/:userId/email
        """
        assert len(self.results) == 4, (
            f"Expected 4 routes, got {len(self.results)}: "
            f"{[(r.http_method, r.route_path) for r in self.results]}"
        )

    def test_vulnerable_post_route_has_absent_auth(self) -> None:
        """POST /orders/:orderId/cancel should have auth_check_status=ABSENT."""
        cancel_routes = [
            r for r in self.results
            if "cancel" in r.route_path and r.http_method == "POST"
        ]
        assert len(cancel_routes) == 1
        assert cancel_routes[0].auth_check_status == "ABSENT"

    def test_safe_delete_route_has_present_auth(self) -> None:
        """DELETE /orders/:orderId should have auth_check_status=PRESENT."""
        delete_routes = [
            r for r in self.results
            if r.http_method == "DELETE" and "order" in r.route_path.lower()
        ]
        assert len(delete_routes) == 1
        assert delete_routes[0].auth_check_status == "PRESENT"

    def test_vulnerable_patch_has_absent_auth(self) -> None:
        """PATCH /users/:userId/email should have auth_check_status=ABSENT."""
        patch_routes = [
            r for r in self.results
            if r.http_method == "PATCH" and "email" in r.route_path
        ]
        assert len(patch_routes) == 1
        assert patch_routes[0].auth_check_status == "ABSENT"

    def test_safe_put_has_present_or_uncertain_auth(self) -> None:
        """PUT /orders/:orderId uses findOne with userId — should be PRESENT or UNCERTAIN."""
        put_routes = [
            r for r in self.results
            if r.http_method == "PUT" and "order" in r.route_path.lower()
        ]
        assert len(put_routes) == 1
        assert put_routes[0].auth_check_status in ("PRESENT", "UNCERTAIN")

    def test_path_params_detected(self) -> None:
        """Cancel route must detect 'orderId' as a path parameter."""
        cancel = [r for r in self.results if "cancel" in r.route_path][0]
        param_names = {p.name for p in cancel.object_id_params}
        assert "orderId" in param_names

    def test_language_is_javascript(self) -> None:
        """All results from the Express fixture must have language='javascript'."""
        for r in self.results:
            assert r.language == "javascript"

    def test_db_operations_detected_for_delete(self) -> None:
        """DELETE route should have at least one DB operation (destroy)."""
        delete = [
            r for r in self.results
            if r.http_method == "DELETE" and "order" in r.route_path.lower()
        ][0]
        assert len(delete.db_operations) >= 1
        op_types = {op.operation_type for op in delete.db_operations}
        assert "DELETE" in op_types or "READ" in op_types


# ── Cross-cutting tests ───────────────────────────────────────────────────


class TestAnalyzerEdgeCases:
    """Tests for edge cases and invariants across both fixtures."""

    def test_empty_directory_returns_empty(self, tmp_path: Path) -> None:
        """An empty directory should produce zero results without errors."""
        results = analyze_codebase(str(tmp_path))
        assert results == []

    def test_unsupported_files_are_skipped(self, tmp_path: Path) -> None:
        """Files with unsupported extensions should be silently skipped."""
        (tmp_path / "schema.graphql").write_text("type Query { hello: String }")
        (tmp_path / "notes.txt").write_text("some notes")
        results = analyze_codebase(str(tmp_path))
        assert results == []

    def test_node_modules_skipped(self, tmp_path: Path) -> None:
        """Files inside node_modules should never be scanned."""
        nm = tmp_path / "node_modules" / "express" / "lib"
        nm.mkdir(parents=True)
        (nm / "router.js").write_text("""
const router = require('express').Router();
router.post('/internal/:id', (req, res) => { res.json({}); });
module.exports = router;
""")
        results = analyze_codebase(str(tmp_path))
        assert results == []
