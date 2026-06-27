"""MCP-facing response helpers.

The first phase uses plain dictionaries to keep tool output simple. Pydantic
schemas can be introduced once the final JSON Schema is locked.
"""

from __future__ import annotations

from typing import Any


def not_implemented_response(tool: str) -> dict[str, Any]:
    """Return a consistent placeholder response for unfinished tools."""

    return {
        "accepted": False,
        "reason": f"{tool} is not implemented yet.",
        "risk": "not_implemented",
    }
