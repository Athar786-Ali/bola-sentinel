"""
Route extractor — tree-sitter AST walkers for Python and JavaScript.

Each public function receives a parsed tree-sitter Tree plus the raw source
bytes and returns a list of raw dicts (one per qualifying route).  The dicts
are deliberately un-typed here; the analyzer assembles them into
StaticAnalysisResult objects after running the other detectors.

Supported route styles
----------------------
Python (extract_routes_python):
  • Flask decorator:  @app.route('/path', methods=['POST', 'DELETE'])
  • Flask shorthand:  @app.post('/path'), @bp.delete('/path')
  • FastAPI:          @router.post('/path'), @app.put('/path/{id}')

JavaScript (extract_routes_js):
  • Express on `app` or `router`:
      app.post('/path', handler)
      router.put('/path/:id', async (req, res) => { … })
  • Express chained routes:
      router.route('/path').post(handler).delete(handler)
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tree_sitter import Node, Tree

# HTTP methods that indicate state-changing operations (BOLA-relevant).
_STATE_CHANGING: frozenset[str] = frozenset({"POST", "PUT", "PATCH", "DELETE"})

# ── Tree-walking helpers ───────────────────────────────────────────────────


def _node_text(node: "Node", source_bytes: bytes) -> str:
    """Return the UTF-8 source text for *node*."""
    return source_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def _find_nodes(node: "Node", node_type: str) -> list["Node"]:
    """
    Return all descendant nodes (including *node* itself) with the given
    tree-sitter node type.  Performs a depth-first pre-order traversal.
    """
    results: list["Node"] = []
    stack = [node]
    while stack:
        current = stack.pop()
        if current.type == node_type:
            results.append(current)
        # tree-sitter nodes store children in left-to-right order; reverse so
        # the stack processes them left-to-right after popping.
        stack.extend(reversed(current.children))
    return results


def _direct_children_by_type(node: "Node", type_name: str) -> list["Node"]:
    """Return direct children of *node* with the given type."""
    return [c for c in node.children if c.type == type_name]


def _is_valid_route_path(path: str) -> bool:
    """
    Return True if *path* looks like a genuine URL route path.

    A valid route path must start with '/' (absolute path).  This rejects
    garbage matches like 'origin', '//content', class names, etc.
    """
    if not path:
        return False
    if not path.startswith("/"):
        return False
    return True


# ── Python route extraction ────────────────────────────────────────────────

# FastAPI / Flask-shorthand: @<obj>.<method>('/<path>')
# Captures: group 1 = method name, group 2 = path string
_PY_SHORTHAND_RE = re.compile(
    r"""@\s*\w+\.(post|put|patch|delete)\s*\(\s*['"]([^'"]+)['"]""",
    re.IGNORECASE,
)

# Flask-style: @<obj>.route('/<path>', methods=[...])
# Captures: group 1 = path string
_PY_ROUTE_PATH_RE = re.compile(
    r"""@\s*\w+\.route\s*\(\s*['"]([^'"]+)['"]""",
    re.IGNORECASE,
)

# methods=[…] inside a Flask @route decorator
# Captures: group 1 = the bracketed list contents
_PY_METHODS_RE = re.compile(
    r"""methods\s*=\s*\[([^\]]+)\]""",
    re.IGNORECASE,
)

# Individual method strings inside the methods list
_PY_METHOD_STR_RE = re.compile(r"""['"](\\w+)['"]""")


def extract_routes_python(
    tree: "Tree",
    source_bytes: bytes,
    file_path: str,
) -> list[dict[str, Any]]:
    """
    Walk the Python AST and return raw route dicts for every state-changing
    route found (POST, PUT, PATCH, DELETE).

    Supports Flask @route, Flask shorthand @app.post/put/…, and FastAPI
    @router.post/put/… decorators.

    Parameters
    ----------
    tree:
        Parsed tree-sitter Tree for the Python source file.
    source_bytes:
        Original source code as bytes (used for text slicing).
    file_path:
        Path to the source file (carried through to the output dict).

    Returns
    -------
    list[dict]
        Each dict has keys: http_method, route_path, line_number,
        handler_code_raw, file_path, language.
    """
    routes: list[dict[str, Any]] = []
    source_str = source_bytes.decode("utf-8", errors="replace")

    # tree-sitter Python grammar: decorated functions appear as
    # `decorated_definition` nodes with one or more `decorator` children
    # followed by a `function_definition` (or `async_function_definition`).
    for dec_def in _find_nodes(tree.root_node, "decorated_definition"):
        decorators = _direct_children_by_type(dec_def, "decorator")
        func_nodes = [
            c
            for c in dec_def.children
            if c.type in ("function_definition", "async_function_definition")
        ]
        if not func_nodes:
            continue
        func_node = func_nodes[0]
        handler_code = _node_text(func_node, source_bytes)
        # Include the decorated_definition for handler_code so the full
        # decorated function (decorators + body) is available to detectors.
        full_handler_code = _node_text(dec_def, source_bytes)

        for dec in decorators:
            dec_text = _node_text(dec, source_bytes)

            # ── FastAPI / Flask shorthand (@app.post, @router.delete …) ──
            m = _PY_SHORTHAND_RE.search(dec_text)
            if m:
                method = m.group(1).upper()
                path = m.group(2)
                if _is_valid_route_path(path):
                    routes.append(
                        {
                            "http_method": method,
                            "route_path": path,
                            "line_number": dec.start_point[0] + 1,
                            "handler_code_raw": full_handler_code,
                            "file_path": file_path,
                            "language": "python",
                        }
                    )
                # Only one qualifying decorator per decorated_definition.
                break

            # ── Flask @route with explicit methods=[…] ──────────────────
            path_m = _PY_ROUTE_PATH_RE.search(dec_text)
            methods_m = _PY_METHODS_RE.search(dec_text)
            if path_m and methods_m:
                path = path_m.group(1)
                if not _is_valid_route_path(path):
                    continue
                methods_in_decorator = [
                    s.upper()
                    for s in _PY_METHOD_STR_RE.findall(methods_m.group(1))
                ]
                for method in methods_in_decorator:
                    if method in _STATE_CHANGING:
                        routes.append(
                            {
                                "http_method": method,
                                "route_path": path,
                                "line_number": dec.start_point[0] + 1,
                                "handler_code_raw": full_handler_code,
                                "file_path": file_path,
                                "language": "python",
                            }
                        )
                if any(m in _STATE_CHANGING for m in methods_in_decorator):
                    break

    return routes


# ── JavaScript route extraction ────────────────────────────────────────────

# Match the property name of Express member calls:
# app.post, router.put, api.delete …
# STRICTLY state-changing methods only — no .get()
_JS_METHOD_RE = re.compile(
    r"\.(post|put|patch|delete)$",
    re.IGNORECASE,
)

# Strip surrounding JS string delimiters (", ', `)
_JS_STRIP_QUOTES_RE = re.compile(r"""^['"`]|['"`]$""")


def _extract_js_string(node: "Node", source_bytes: bytes) -> str | None:
    """
    Return the unquoted string value of a tree-sitter string / template_string
    node, or None if the node is not a string type.
    """
    if node.type not in ("string", "template_string"):
        return None
    raw = _node_text(node, source_bytes).strip()
    # Remove wrapping quotes/backticks
    return _JS_STRIP_QUOTES_RE.sub("", raw)


def extract_routes_js(
    tree: "Tree",
    source_bytes: bytes,
    file_path: str,
) -> list[dict[str, Any]]:
    """
    Walk the JavaScript AST and return raw route dicts for every
    state-changing Express route found (POST, PUT, PATCH, DELETE).

    Handles both `app.<method>` and `router.<method>` call patterns with
    inline function expressions and arrow functions.

    Parameters
    ----------
    tree:
        Parsed tree-sitter Tree for the JavaScript source file.
    source_bytes:
        Original source code as bytes.
    file_path:
        Path to the source file.

    Returns
    -------
    list[dict]
        Each dict has keys: http_method, route_path, line_number,
        handler_code_raw, file_path, language.
    """
    routes: list[dict[str, Any]] = []
    # Track already-seen (path, method, line) tuples to prevent duplicates
    # from the chained-route walker re-matching direct calls.
    seen: set[tuple[str, str, int]] = set()

    # ── Pass 1: Direct app.post('/path', handler) calls ──────────────────
    for call_node in _find_nodes(tree.root_node, "call_expression"):
        children = call_node.children
        if not children:
            continue

        func_node = children[0]
        if func_node.type != "member_expression":
            continue

        func_text = _node_text(func_node, source_bytes)
        method_m = _JS_METHOD_RE.search(func_text)
        if not method_m:
            continue

        http_method = method_m.group(1).upper()

        # Find the arguments node
        args_nodes = _direct_children_by_type(call_node, "arguments")
        if not args_nodes:
            continue
        args_node = args_nodes[0]

        # Collect non-punctuation argument children
        arg_children = [
            c for c in args_node.children if c.type not in ("(", ")", ",")
        ]
        if not arg_children:
            continue

        # First argument must be a string (the route path).
        route_path = _extract_js_string(arg_children[0], source_bytes)
        if route_path is None:
            continue

        # Validate that the path looks like a real route
        if not _is_valid_route_path(route_path):
            continue

        # Handler code: the last function-like argument, or the full call text
        # if we can't isolate the handler.
        handler_code: str
        if len(arg_children) >= 2:
            last_arg = arg_children[-1]
            if last_arg.type in (
                "arrow_function",
                "function_expression",
                "function",
            ):
                handler_code = _node_text(last_arg, source_bytes)
            else:
                handler_code = _node_text(call_node, source_bytes)
        else:
            handler_code = _node_text(call_node, source_bytes)

        line = call_node.start_point[0] + 1
        key = (route_path, http_method, line)
        if key not in seen:
            seen.add(key)
            routes.append(
                {
                    "http_method": http_method,
                    "route_path": route_path,
                    "line_number": line,
                    "handler_code_raw": handler_code,
                    "file_path": file_path,
                    "language": "javascript",
                }
            )

    # ── Pass 2: Chained router.route('/path').post(...).delete(...) ───────
    # Express supports: router.route('/users/:id').post(handler).delete(handler)
    # The path is passed to .route(), and HTTP methods are chained on the result.
    for call_node in _find_nodes(tree.root_node, "call_expression"):
        children = call_node.children
        if not children:
            continue

        func_node = children[0]
        if func_node.type != "member_expression":
            continue

        func_text = _node_text(func_node, source_bytes)

        # Must end with exactly ".route" — not ".somethingRoute"
        if not re.search(r"\brouter\.route$|\.route$", func_text):
            continue

        # Extract the path argument from .route('/path')
        args_nodes = _direct_children_by_type(call_node, "arguments")
        if not args_nodes:
            continue
        arg_children = [
            c for c in args_nodes[0].children if c.type not in ("(", ")", ",")
        ]
        if not arg_children:
            continue

        route_path = _extract_js_string(arg_children[0], source_bytes)
        if route_path is None:
            continue
        if not _is_valid_route_path(route_path):
            continue

        # Walk upward to find chained .post()/.put()/.patch()/.delete() calls.
        _find_chained_methods(
            call_node, route_path, source_bytes, file_path, routes, seen
        )

    return routes


def _find_chained_methods(
    route_call_node: "Node",
    route_path: str,
    source_bytes: bytes,
    file_path: str,
    routes: list[dict[str, Any]],
    seen: set[tuple[str, str, int]],
) -> None:
    """
    Given a .route('/path') call node, find all chained .post()/.put()/
    .patch()/.delete() calls on it and add them to routes.

    Explicitly skips .get() — GET routes are out of scope for this version.
    """
    parent = route_call_node.parent
    while parent is not None:
        if parent.type == "call_expression":
            children = parent.children
            if children and children[0].type == "member_expression":
                member_text = _node_text(children[0], source_bytes)
                # Only match state-changing methods (no GET)
                method_m = _JS_METHOD_RE.search(member_text)
                if method_m:
                    http_method = method_m.group(1).upper()
                    line = parent.start_point[0] + 1
                    key = (route_path, http_method, line)

                    if key not in seen:
                        seen.add(key)

                        # Extract handler code from the arguments
                        args_nodes = _direct_children_by_type(parent, "arguments")
                        handler_code = _node_text(parent, source_bytes)
                        if args_nodes:
                            arg_children = [
                                c for c in args_nodes[0].children
                                if c.type not in ("(", ")", ",")
                            ]
                            if arg_children:
                                last_arg = arg_children[-1]
                                if last_arg.type in (
                                    "arrow_function", "function_expression", "function",
                                ):
                                    handler_code = _node_text(last_arg, source_bytes)

                        routes.append(
                            {
                                "http_method": http_method,
                                "route_path": route_path,
                                "line_number": line,
                                "handler_code_raw": handler_code,
                                "file_path": file_path,
                                "language": "javascript",
                            }
                        )
        # In chained calls like .route('/path').post(h).delete(h),
        # each .method() call wraps the previous, so walk upward.
        parent = parent.parent
        # Stop if we've gone too far up the tree
        if parent and parent.type in ("program", "statement_block", "expression_statement"):
            break
