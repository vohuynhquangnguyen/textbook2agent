"""Caption text for study scenes: lines break only where the author writes \\\\ (no Manim needed)."""

from __future__ import annotations

LINE_BREAK = r"\\"


def unbreakable_lines(text: str) -> str:
    """Wrap each explicit line in an mbox, so LaTeX never adds line breaks of its own."""
    return f" {LINE_BREAK} ".join(rf"\mbox{{{line.strip()}}}" for line in text.split(LINE_BREAK))
