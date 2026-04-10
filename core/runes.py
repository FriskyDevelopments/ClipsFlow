"""Runic language primitives for the ClipsFlow STIX MΛGIC pipeline.

The rune set is intentionally minimal and semantic:
- every glyph maps to a state, action, or flow condition
- each shape is geometric and reproducible in SVG
- symbols are reused in logs, UX copy, and mini-app rendering
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Rune:
    """Semantic rune definition with a code glyph and an SVG path."""

    key: str
    glyph: str
    meaning: str
    shape_logic: str
    svg: str


RUNES: dict[str, Rune] = {
    "input": Rune(
        key="input",
        glyph="⟪",
        meaning="Incoming signal detected from a source boundary.",
        shape_logic="Split-entry chevron that opens toward the pipeline.",
        svg=(
            '<svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" '
            'fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="square">'
            '<path d="M34 10 16 32 34 54"/><path d="M50 10 32 32 50 54"/></svg>'
        ),
    ),
    "flow": Rune(
        key="flow",
        glyph="→",
        meaning="Active movement through the processing line.",
        shape_logic="Forward shaft with hard directional head.",
        svg=(
            '<svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" '
            'fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="square">'
            '<path d="M10 32h36"/><path d="M34 18 50 32 34 46"/></svg>'
        ),
    ),
    "transform": Rune(
        key="transform",
        glyph="Λ",
        meaning="Core conversion and alchemy stage.",
        shape_logic="Triangular apex representing controlled transformation.",
        svg=(
            '<svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" '
            'fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="square">'
            '<path d="M14 50 32 14 50 50"/></svg>'
        ),
    ),
    "split": Rune(
        key="split",
        glyph="⫶",
        meaning="Branching path / multiplex routing.",
        shape_logic="Single trunk diverging into dual processing paths.",
        svg=(
            '<svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" '
            'fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="square">'
            '<path d="M12 32h22"/><path d="M34 32 52 16"/><path d="M34 32 52 48"/></svg>'
        ),
    ),
    "output": Rune(
        key="output",
        glyph="◫",
        meaning="Stable result materialized for delivery.",
        shape_logic="Closed capsule/rectilinear enclosure indicating finalization.",
        svg=(
            '<svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" '
            'fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="square">'
            '<rect x="12" y="18" width="40" height="28"/></svg>'
        ),
    ),
    "error": Rune(
        key="error",
        glyph="✕",
        meaning="Disruption, fracture, or unstable execution.",
        shape_logic="Broken crossing diagonals for hard fault signaling.",
        svg=(
            '<svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" '
            'fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="square">'
            '<path d="M14 14 28 28"/><path d="M36 36 50 50"/><path d="M50 14 36 28"/><path d="M28 36 14 50"/></svg>'
        ),
    ),
    "lock": Rune(
        key="lock",
        glyph="⟐",
        meaning="Validated and cryptographically trusted condition.",
        shape_logic="Enclosed diamond node with center point (sealed state).",
        svg=(
            '<svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" '
            'fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="square">'
            '<path d="M32 10 52 32 32 54 12 32Z"/><path d="M32 32h.1"/></svg>'
        ),
    ),
}


STATUS_TO_RUNE: dict[str, str] = {
    "SUCCESS": "output",
    "VALIDATION_ERROR": "lock",
    "PROVIDER_ERROR": "error",
    "PROCESSING_ERROR": "error",
}


def rune_for_status(status: str) -> Rune:
    """Return the best rune for a ClipStatus-style status string."""
    return RUNES[STATUS_TO_RUNE.get(status, "flow")]


def rune_log(rune_key: str, message: str) -> str:
    """Render consistent CLI/log symbols like: ``[Λ] TRANSFORM ACTIVE``."""
    rune = RUNES[rune_key]
    return f"[{rune.glyph}] {message}"
