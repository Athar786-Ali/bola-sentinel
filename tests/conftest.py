"""
Shared pytest fixtures for bola-sentinel tests.

Provides an autouse fixture that patches settings.logs_dir and
settings.results_dir to use pytest's tmp_path-equivalent directories
so tests never write logs to the real project directories.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _patch_settings_dirs(tmp_path: Path) -> None:
    """
    Redirect all log/result file writes to tmp_path for every test.

    Pydantic-Settings creates a singleton at import time, so
    monkeypatch.setenv() is ineffective after the first import.
    Patching the already-instantiated object's attributes is the
    only reliable approach.
    """
    logs_dir = str(tmp_path / "logs")
    results_dir = str(tmp_path / "results")

    with (
        patch(
            "bola_sentinel.dynamic_verification.evidence_logger.settings"
        ) as mock_ev_settings,
        patch(
            "bola_sentinel.llm_reasoning.logger.settings"
        ) as mock_llm_settings,
        patch(
            "bola_sentinel.evaluation.evaluation_logger.settings"
        ) as mock_eval_settings,
    ):
        for s in (mock_ev_settings, mock_llm_settings, mock_eval_settings):
            s.logs_dir = logs_dir
            s.results_dir = results_dir
        mock_llm_settings.ollama_model = "qwen2.5:7b-instruct"
        yield

