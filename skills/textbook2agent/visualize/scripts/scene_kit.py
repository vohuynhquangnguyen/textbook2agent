"""Shared look and structure for study animations.

Scenes import this module (`from scene_kit import Palette, StudyScene`); render_scene.py puts this folder on the
Python path. A StudyScene is split into beats: each beat is one Manim section with a title card, so every beat
becomes its own video and key frame for review, and exercise-related beats can be released one at a time.
"""

from __future__ import annotations

from manim import (
    DOWN,
    UP,
    BackgroundRectangle,
    FadeIn,
    FadeOut,
    Mobject,
    Scene,
    SurroundingRectangle,
    Tex,
    VGroup,
    Write,
)

from caption_markup import unbreakable_lines


class Palette:
    """Okabe-Ito colours, distinguishable with common colour-vision deficiencies, on Manim's black background."""

    PRIMARY = "#56B4E9"    # sky blue: the main object (a curve, the data, the current iterate)
    SECONDARY = "#E69F00"  # orange: the contrasting object (negative parts, a competing method)
    BOUND = "#009E73"      # bluish green: bounds, targets, the answer
    HIGHLIGHT = "#F0E442"  # yellow: the thing to look at right now
    ACCENT = "#CC79A7"     # reddish purple: a third series
    WARNING = "#D55E00"    # vermillion: errors, residuals
    MUTED = "#8C8C8C"      # grey: axes labels and context
    TEXT = "#FFFFFF"


CAPTION_FONT_SIZE = 30
CAPTION_MAX_WIDTH = 12.5
CAPTION_EDGE_BUFFER = 0.35
TITLE_FONT_SIZE = 46
SUBTITLE_FONT_SIZE = 30
TITLE_HOLD_SECONDS = 1.2
BACKDROP_OPACITY = 0.85


def caption_mobject(text: str) -> VGroup:
    """A one- or two-line caption (LaTeX text mode; inline math in $...$) on a dark backdrop at the bottom.

    Lines break only at an explicit \\\\; a line too wide for the frame is scaled down, never wrapped.
    """
    words = Tex(unbreakable_lines(text), font_size=CAPTION_FONT_SIZE, color=Palette.TEXT)
    if words.width > CAPTION_MAX_WIDTH:
        words.scale_to_fit_width(CAPTION_MAX_WIDTH)
    words.to_edge(DOWN, buff=CAPTION_EDGE_BUFFER)
    backdrop = BackgroundRectangle(words, fill_opacity=BACKDROP_OPACITY, buff=0.12)
    return VGroup(backdrop, words)


def title_card(title: str, subtitle: str = "") -> VGroup:
    heading = Tex(title, font_size=TITLE_FONT_SIZE, color=Palette.TEXT)
    if not subtitle:
        return VGroup(heading)
    detail = Tex(subtitle, font_size=SUBTITLE_FONT_SIZE, color=Palette.MUTED).next_to(heading, DOWN, buff=0.35)
    return VGroup(heading, detail)


def boxed(mobject: Mobject, color: str = Palette.HIGHLIGHT) -> VGroup:
    return VGroup(mobject, SurroundingRectangle(mobject, color=color, buff=0.15))


class StudyScene(Scene):
    """A Scene organised in beats, with one caption line that is replaced as the explanation moves on."""

    def setup(self) -> None:
        self._caption: VGroup | None = None

    def beat(self, name: str, title: str, subtitle: str = "") -> None:
        """Start a storyboard beat on an empty stage: a new section that opens with a short title card."""
        self.next_section(name)
        self.clear_stage()
        card = title_card(title, subtitle)
        self.play(Write(card))
        self.wait(TITLE_HOLD_SECONDS)
        self.play(FadeOut(card))

    def continue_beat(self, name: str) -> None:
        """Start a storyboard beat that builds on what is already on screen (a new section, no title card)."""
        self.next_section(name)

    def say(self, text: str, hold: float = 1.5) -> None:
        """Show a caption, replacing the previous one, and hold it long enough to read."""
        new_caption = caption_mobject(text)
        if self._caption is None:
            self.play(FadeIn(new_caption, shift=0.2 * UP))
        else:
            self.play(FadeOut(self._caption), FadeIn(new_caption, shift=0.2 * UP))
        self._caption = new_caption
        self.wait(hold)

    def clear_caption(self) -> None:
        if self._caption is not None:
            self.play(FadeOut(self._caption))
            self._caption = None

    def clear_stage(self) -> None:
        """Fade out every object on screen, so the next beat starts on an empty frame."""
        if self.mobjects:
            self.play(*[FadeOut(mobject) for mobject in self.mobjects])
        self._caption = None
