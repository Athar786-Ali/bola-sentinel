"""
bola-sentinel global configuration.

Values can be overridden via environment variables or a .env file placed at
the project root (see .env.example).  Only Ollama-related settings are
expected — no paid API keys are used anywhere in this project.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Project-wide settings.

    All fields can be set via environment variables (uppercased) or a
    .env file at the project root.  Example::

        OLLAMA_HOST=http://localhost:11434
        OLLAMA_MODEL=qwen2.5:7b-instruct
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Ollama (local LLM) ─────────────────────────────────────────────────
    ollama_host: str = "http://localhost:11434"
    """Base URL of the local Ollama instance."""

    ollama_model: str = "qwen2.5:7b-instruct"
    """Ollama model tag to use for LLM reasoning."""

    # ── Project directory roots ────────────────────────────────────────────
    results_dir: str = "results"
    """Directory where final JSON reports are written."""

    logs_dir: str = "logs"
    """
    Root log directory.  Sub-directories used by the pipeline:
      logs/llm_inputs/       – every prompt sent to the LLM
      logs/llm_outputs/      – every raw LLM response
      logs/verification_logs/ – full HTTP evidence per verification attempt
      logs/evaluation_logs/  – evaluation run logs
    """

    datasets_dir: str = "datasets"
    """
    Root datasets directory.  Expected sub-directories:
      datasets/juice_shop/   – OWASP Juice Shop clone
      datasets/real_cves/    – one subfolder per CVE-affected repo
      datasets/ground_truth/ – curated ground-truth JSON files
    """


# Module-level singleton — import this from any submodule.
settings = Settings()
