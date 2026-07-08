"""
LLM Reasoning layer.

Responsibility: Send StaticAnalysisResult objects to a local Ollama model,
receive structured LlmClassification responses, and persist every prompt /
raw response to logs/llm_inputs/ and logs/llm_outputs/ for reproducibility.

Public API
----------
classify_all_routes(routes) -> list[ClassifiedRoute]
classify_route(route)       -> LlmClassification
"""

from .classifier import classify_all_routes, classify_route

__all__ = ["classify_all_routes", "classify_route"]
