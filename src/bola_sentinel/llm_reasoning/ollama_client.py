"""
Ollama HTTP client for bola-sentinel LLM reasoning.

Uses httpx (already a project dependency) to call the local Ollama
generate API.  No paid API keys, no external network calls.

Expected Ollama setup
---------------------
    ollama serve                         # start the daemon
    ollama pull qwen2.5:7b-instruct     # pull the model
"""

from __future__ import annotations

import httpx

from bola_sentinel.config import settings

# Ollama generate endpoint path
_GENERATE_PATH = "/api/generate"

# Connection and read timeouts (seconds).
# Local inference on a 7B model typically takes 5–60 s depending on hardware.
_TIMEOUT = httpx.Timeout(connect=10.0, read=300.0, write=30.0, pool=10.0)


def call_ollama(prompt: str, system_prompt: str) -> str:
    """
    Send *prompt* + *system_prompt* to the local Ollama instance and return
    the raw model response text.

    Parameters
    ----------
    prompt:
        The user-facing prompt containing route context.
    system_prompt:
        The system-role instruction that sets the model's persona and output
        format.

    Returns
    -------
    str
        The ``"response"`` field from the Ollama JSON payload — this is the
        raw text the model produced (ideally valid JSON as instructed).

    Raises
    ------
    RuntimeError
        If Ollama is unreachable, the model is missing, or the response
        structure is unexpected.
    """
    url = settings.ollama_host.rstrip("/") + _GENERATE_PATH
    payload: dict = {
        "model": settings.ollama_model,
        "system": system_prompt,
        "prompt": prompt,
        "stream": False,
        "format": "json",
    }

    try:
        resp = httpx.post(url, json=payload, timeout=_TIMEOUT)
        resp.raise_for_status()
    except httpx.ConnectError as exc:
        raise RuntimeError(
            f"Cannot connect to Ollama at {settings.ollama_host!r}.\n"
            "Please run:\n"
            "  ollama serve\n"
            f"  ollama pull {settings.ollama_model}\n"
            f"Original error: {exc}"
        ) from exc
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise RuntimeError(
                f"Ollama model {settings.ollama_model!r} not found.\n"
                "Please run:\n"
                f"  ollama pull {settings.ollama_model}\n"
                f"Original error: {exc}"
            ) from exc
        raise RuntimeError(
            f"Ollama returned HTTP {exc.response.status_code}: {exc.response.text[:500]}"
        ) from exc
    except httpx.TimeoutException as exc:
        raise RuntimeError(
            f"Ollama request timed out after {_TIMEOUT.read}s.\n"
            "Consider using a smaller model or increasing the timeout.\n"
            f"Original error: {exc}"
        ) from exc

    try:
        data = resp.json()
    except Exception as exc:
        raise RuntimeError(
            f"Ollama response was not valid JSON: {resp.text[:500]}"
        ) from exc

    if "response" not in data:
        raise RuntimeError(
            f"Ollama response missing 'response' field. Got keys: {list(data.keys())}\n"
            f"Body: {resp.text[:500]}"
        )

    return str(data["response"])
