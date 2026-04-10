"""Helper functions for parsing environment variables."""

from __future__ import annotations

import os


def parse_bool_env(key: str, default: bool = False) -> bool:
    """Parse a boolean environment variable."""
    val = os.getenv(key, "").strip().lower()
    if not val:
        return default
    if val in {"true", "1", "yes", "y", "on"}:
        return True
    if val in {"false", "0", "no", "n", "off"}:
        return False
    raise ValueError(f"[CONFIG ERROR] Invalid boolean value for {key}: {val}")


def parse_int_env(key: str, default: int, min_val: int | None = None, max_val: int | None = None) -> int:
    """Parse an integer environment variable."""
    val = os.getenv(key, "").strip()
    if not val:
        return default
    try:
        parsed = int(val)
    except ValueError as err:
        raise ValueError(f"[CONFIG ERROR] Invalid integer value for {key}: {val}") from err

    if min_val is not None and parsed < min_val:
        raise ValueError(f"[CONFIG ERROR] {key} must be at least {min_val}")
    if max_val is not None and parsed > max_val:
        raise ValueError(f"[CONFIG ERROR] {key} must be at most {max_val}")
    return parsed


def parse_float_env(key: str, default: float, min_val: float | None = None, max_val: float | None = None) -> float:
    """Parse a float environment variable."""
    val = os.getenv(key, "").strip()
    if not val:
        return default
    try:
        parsed = float(val)
    except ValueError as err:
        raise ValueError(f"[CONFIG ERROR] Invalid float value for {key}: {val}") from err

    if min_val is not None and parsed < min_val:
        raise ValueError(f"[CONFIG ERROR] {key} must be at least {min_val}")
    if max_val is not None and parsed > max_val:
        raise ValueError(f"[CONFIG ERROR] {key} must be at most {max_val}")
    return parsed
