"""
Test-user loader for the dynamic verification layer.

test_users.json is filled in manually once per target application before
running Phase 3.  This module validates the structure and raises descriptive
errors so the researcher knows exactly what is missing.

Expected format::

    {
      "user_a": {
        "auth_header": "Bearer <token>",
        "user_id": "1",
        "owned_object_ids": {
          "orders": ["20", "22"],
          "projects": ["30"],
          "posts": ["10", "11"]
        }
      },
      "user_b": {
        "auth_header": "Bearer <token>",
        "user_id": "2",
        "owned_object_ids": {
          "orders": ["21"],
          "projects": ["31"],
          "posts": ["12"]
        }
      }
    }

Convention
----------
• user_a = **attacker** — their ``auth_header`` is used in probe requests.
• user_b = **victim**  — their ``owned_object_ids`` supply target object IDs.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Required top-level user keys.
_REQUIRED_USERS: tuple[str, ...] = ("user_a", "user_b")

# Required fields inside each user entry.
_REQUIRED_USER_FIELDS: tuple[str, ...] = ("auth_header", "user_id", "owned_object_ids")


def _validate(data: dict) -> None:
    """
    Validate the structure of the loaded test-users dict.

    Raises
    ------
    ValueError
        With a human-readable message listing every missing / invalid field.
    """
    errors: list[str] = []

    for user_key in _REQUIRED_USERS:
        if user_key not in data:
            errors.append(f"Missing top-level key: '{user_key}'")
            continue
        entry = data[user_key]
        if not isinstance(entry, dict):
            errors.append(f"'{user_key}' must be a dict, got {type(entry).__name__}")
            continue
        for field in _REQUIRED_USER_FIELDS:
            if field not in entry:
                errors.append(f"'{user_key}' is missing required field '{field}'")
        if "owned_object_ids" in entry and not isinstance(entry["owned_object_ids"], dict):
            errors.append(
                f"'{user_key}.owned_object_ids' must be a dict mapping "
                f"resource type → list of ID strings"
            )

    if errors:
        raise ValueError(
            "test_users.json is invalid:\n"
            + "\n".join(f"  • {e}" for e in errors)
        )


def load_test_users(path: str = "test_users.json") -> dict:
    """
    Read and validate the test-users configuration file.

    Parameters
    ----------
    path:
        Path to ``test_users.json``.  Defaults to ``"test_users.json"``
        in the current working directory.

    Returns
    -------
    dict
        Validated test-users dict with at least ``user_a`` and ``user_b``
        entries.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    ValueError
        If the file exists but is malformed or missing required fields.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"test_users.json not found at {p.resolve()}.\n"
            "Please create it by copying .env.example → test_users.json "
            "and filling in credentials for the target application.\n"
            "See README.md for the required format."
        )

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"test_users.json is not valid JSON: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise ValueError(
            f"test_users.json must be a JSON object (dict), "
            f"got {type(data).__name__}"
        )

    _validate(data)
    logger.info(
        "Loaded test users from %s (%d resource types for user_b)",
        p,
        len(data.get("user_b", {}).get("owned_object_ids", {})),
    )
    return data
