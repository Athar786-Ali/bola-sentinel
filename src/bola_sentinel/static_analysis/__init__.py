"""
Static Analysis layer.

Responsibility: Parse source code (Python, JavaScript, …) via tree-sitter
to extract route definitions, object-id parameters, DB operations, and the
presence/absence of authorization checks — producing StaticAnalysisResult
objects.

Public API
----------
analyze_codebase(root_path) -> list[StaticAnalysisResult]
"""

from .analyzer import analyze_codebase

__all__ = ["analyze_codebase"]
