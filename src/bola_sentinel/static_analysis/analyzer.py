"""
Top-level static analysis orchestrator.

Ties together the parser registry, route extractors, object-id detector,
DB operation extractor, and auth-check detector into a single
``analyze_codebase`` entry point.

Output: list[StaticAnalysisResult] — the canonical schema consumed by
the LLM reasoning layer (Phase 2).
"""

from __future__ import annotations

import logging
from typing import Any

from bola_sentinel.models.schemas import StaticAnalysisResult

from .auth_check_detector import detect_auth_check
from .db_operation_extractor import extract_db_operations
from .object_id_detector import detect_object_id_params
from .parser_registry import discover_source_files, get_parser_for_file
from .route_extractor import extract_routes_js, extract_routes_python

logger = logging.getLogger(__name__)

# Dispatch table: language name → extraction function.
# Adding a language = adding one entry here + one function in route_extractor.
_EXTRACTORS: dict[str, Any] = {
    "python": extract_routes_python,
    "javascript": extract_routes_js,
}


def analyze_codebase(root_path: str) -> list[StaticAnalysisResult]:
    """
    Run the full static-analysis pipeline on the codebase rooted at
    *root_path*.

    Steps
    -----
    1. Discover source files (Python + JavaScript).
    2. Parse each file with the appropriate tree-sitter parser.
    3. Extract state-changing routes (POST, PUT, PATCH, DELETE).
    4. For each route: detect object-id params, DB operations, and
       auth-check status.
    5. Assemble and return ``StaticAnalysisResult`` objects.

    POST routes with empty ``db_operations`` are preserved — they may
    delegate state changes to queues or micro-services and are still
    BOLA-relevant.

    Parameters
    ----------
    root_path:
        Absolute or relative path to the target codebase root.

    Returns
    -------
    list[StaticAnalysisResult]
        One entry per qualifying route, sorted by file path then line number.
    """
    files = discover_source_files(root_path)
    logger.info("Discovered %d source files in %s", len(files), root_path)

    results: list[StaticAnalysisResult] = []

    for file_path in files:
        language, parser = get_parser_for_file(file_path)
        if language is None or parser is None:
            continue

        extractor = _EXTRACTORS.get(language)
        if extractor is None:
            logger.warning(
                "No route extractor registered for language %r — skipping %s",
                language,
                file_path,
            )
            continue

        try:
            with open(file_path, "rb") as fh:
                source_bytes = fh.read()
        except OSError:
            logger.warning("Could not read %s — skipping", file_path)
            continue

        tree = parser.parse(source_bytes)
        raw_routes: list[dict[str, Any]] = extractor(tree, source_bytes, file_path)

        for raw in raw_routes:
            route_path: str = raw["route_path"]
            handler_code: str = raw["handler_code_raw"]
            lang: str = raw["language"]

            # ── Detect object-id parameters ────────────────────────────
            object_id_params = detect_object_id_params(route_path, handler_code, lang)

            # ── Detect DB operations ───────────────────────────────────
            db_operations = extract_db_operations(handler_code, lang)

            # ── Detect auth check ──────────────────────────────────────
            auth_check_status = detect_auth_check(handler_code, object_id_params, lang)

            # ── Build route_id ─────────────────────────────────────────
            route_id = f"{raw['http_method']}_{route_path}_{raw['line_number']}"

            results.append(
                StaticAnalysisResult(
                    route_id=route_id,
                    http_method=raw["http_method"],
                    route_path=route_path,
                    file_path=file_path,
                    line_number=raw["line_number"],
                    language=lang,
                    object_id_params=object_id_params,
                    db_operations=db_operations,
                    auth_check_status=auth_check_status,
                    handler_code_raw=handler_code,
                )
            )

    # Deterministic ordering: by route_id (which includes method, path, and line number).
    results.sort(key=lambda r: r.route_id)
    logger.info("Extracted %d state-changing routes", len(results))
    return results
