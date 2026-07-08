"""
Parser registry for bola-sentinel static analysis.

Design principle: adding support for a new language means adding ONE dict
entry to EXTENSION_TO_LANGUAGE, ONE import in _GRAMMAR_MODULES, and ONE
extractor function in route_extractor.py — no structural changes required.

Parser construction
-------------------
Modern tree-sitter (≥ 0.22) uses per-language pip packages
(``tree-sitter-python``, ``tree-sitter-javascript``, …) rather than the
monolithic ``tree-sitter-languages`` bundle.  This gives us:
  - Granular version control per grammar
  - No single-package Python-version ceiling
  - Same registry dict pattern — adding a language means one new pip
    package + one dict entry

Backward compatibility: if the user's environment has tree-sitter-languages
installed instead (older Python, or personal preference), the registry
falls back to it automatically.
"""

from __future__ import annotations

import importlib
import os
from pathlib import Path
from typing import TYPE_CHECKING

from tree_sitter import Language, Parser

if TYPE_CHECKING:
    pass

# ── Language registry ──────────────────────────────────────────────────────
# Maps file extension (lower-case, with dot) → language name.
# Adding a new language: add extension here + grammar module below.
EXTENSION_TO_LANGUAGE: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
}

# Maps language name → the pip-installed grammar module name.
# e.g. "python" → "tree_sitter_python" (provides a `language()` function).
_GRAMMAR_MODULES: dict[str, str] = {
    "python": "tree_sitter_python",
    "javascript": "tree_sitter_javascript",
}

# Directories to skip during source-file discovery.
_SKIP_DIRS: frozenset[str] = frozenset(
    {
        "node_modules",
        "venv",
        ".venv",
        ".git",
        "__pycache__",
        "dist",
        "build",
        ".eggs",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "coverage",
        ".tox",
    }
)


# ── Parser cache ───────────────────────────────────────────────────────────
_parser_cache: dict[str, Parser] = {}


def _build_parser(language_name: str) -> Parser:
    """
    Build a tree-sitter ``Parser`` for *language_name*.

    Strategy
    --------
    1. Try importing the per-language grammar package
       (e.g. ``tree_sitter_python``) and call its ``language()`` function.
    2. Fall back to ``tree_sitter_languages.get_parser()`` if the per-
       language package is unavailable (for older environments).
    """
    module_name = _GRAMMAR_MODULES.get(language_name)

    # ── Attempt 1: per-language package (preferred) ────────────────────
    if module_name:
        try:
            mod = importlib.import_module(module_name)
            lang_func = getattr(mod, "language", None)
            if lang_func is not None:
                lang_obj = Language(lang_func())
                parser = Parser(lang_obj)
                return parser
        except (ImportError, OSError):
            pass  # fall through to tree_sitter_languages fallback

    # ── Attempt 2: tree_sitter_languages bundle ────────────────────────
    try:
        from tree_sitter_languages import get_parser as _get_bundle_parser  # type: ignore[import]

        return _get_bundle_parser(language_name)
    except ImportError:
        pass

    raise ImportError(
        f"No tree-sitter grammar found for '{language_name}'.  "
        f"Install either: pip install tree-sitter-{language_name.replace('_', '-')}  "
        f"or: pip install tree-sitter-languages"
    )


def _get_cached_parser(language_name: str) -> Parser:
    """Return a cached tree-sitter Parser for *language_name*."""
    if language_name not in _parser_cache:
        _parser_cache[language_name] = _build_parser(language_name)
    return _parser_cache[language_name]


# ── Public API ─────────────────────────────────────────────────────────────


def get_parser_for_file(file_path: str) -> tuple[str | None, Parser | None]:
    """
    Return *(language_name, parser)* for *file_path* based on its extension.

    Returns *(None, None)* for unsupported extensions.

    Examples
    --------
    >>> lang, parser = get_parser_for_file("routes/users.py")
    >>> lang
    'python'
    >>> lang, parser = get_parser_for_file("lib/router.js")
    >>> lang
    'javascript'
    >>> get_parser_for_file("schema.graphql")
    (None, None)
    """
    ext = Path(file_path).suffix.lower()
    language_name = EXTENSION_TO_LANGUAGE.get(ext)
    if language_name is None:
        return None, None
    return language_name, _get_cached_parser(language_name)


def discover_source_files(root_path: str) -> list[str]:
    """
    Recursively walk *root_path* and return absolute paths to all source
    files whose extensions appear in EXTENSION_TO_LANGUAGE.

    Skips directories in _SKIP_DIRS automatically.

    Parameters
    ----------
    root_path:
        Absolute or relative path to the root of the target codebase.

    Returns
    -------
    list[str]
        Sorted list of absolute file paths.
    """
    root = Path(root_path).resolve()
    found: list[str] = []

    for dirpath, dirnames, filenames in os.walk(root):
        # Prune skip-dirs in-place so os.walk doesn't descend into them.
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]

        for filename in filenames:
            ext = Path(filename).suffix.lower()
            if ext in EXTENSION_TO_LANGUAGE:
                found.append(str(Path(dirpath) / filename))

    return sorted(found)
