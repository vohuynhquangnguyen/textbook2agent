"""sin(x)/x is not in L^1(R), yet its improper integral over [0, oo) converges.

Render: uv run <skill>/visualize/scripts/render_scene.py scene.py SincImproperIntegral --quality preview
Every number shown comes from quantities.py; run it first to check the claims.
"""

from __future__ import annotations

import math

from manim import (
    DOWN,
    LEFT,
    PI,
    RIGHT,
    UL,
    UP,
    UR,
    Axes,
    Create,
    DashedLine,
    Dot,
    FadeIn,
    FadeOut,
    GrowFromEdge,
    LaggedStart,
    Line,
    MathTex,
    Polygon,
    Tex,
    ValueTracker,
    VGroup,
    Write,
    always_redraw,
)
import numpy as np

import quantities as q
from scene_kit import Palette, StudyScene, boxed

LABEL_SIZE = 30
SMALL_LABEL_SIZE = 26
FORMULA_SIZE = 36
STEP_SIZE = 32
AREA_OPACITY = 0.55
BAR_WIDTH = 0.36
PLOT_STEP = 0.01
X_LABEL_BUFFER = 0.6     # below the lowest dip of the curve, so labels never touch it
LONG_HOLD = 2.5


def pi_label(multiple: int) -> MathTex:
    text = r"\pi" if multiple == 1 else rf"{multiple}\pi"
    return MathTex(text, font_size=LABEL_SIZE, color=Palette.MUTED)


def muted_label(text: str) -> MathTex:
    return MathTex(text, font_size=SMALL_LABEL_SIZE, color=Palette.MUTED)


def plain_axes(x_range: list[float], y_range: list[float], x_length: float, y_length: float) -> Axes:
    return Axes(x_range=x_range, y_range=y_range, x_length=x_length, y_length=y_length, tips=False,
                axis_config={"color": Palette.MUTED})


def hump_axes(y_range: list[float], y_length: float) -> Axes:
    axes = plain_axes([0, q.HUMPS_SHOWN * PI, PI], y_range, 12, y_length)
    labels = {k * PI: pi_label(k) for k in range(2, q.HUMPS_SHOWN + 1, 2)}
    axes.get_x_axis().add_labels(labels, buff=X_LABEL_BUFFER)
    return axes


def add_y_labels(axes: Axes, values: list[float]) -> None:
    axes.get_y_axis().add_labels({value: muted_label(f"{value:g}") for value in values})


def sign_colour(k: int) -> str:
    return Palette.PRIMARY if k % 2 == 0 else Palette.SECONDARY


def bar(axes: Axes, left: float, width: float, height: float, colour: str) -> Polygon:
    corners = [axes.c2p(left, 0), axes.c2p(left + width, 0), axes.c2p(left + width, height), axes.c2p(left, height)]
    return Polygon(*corners, color=colour, fill_color=colour, fill_opacity=0.8, stroke_width=1)


def sinc_graph(axes: Axes, colour: str):
    return axes.plot(q.f, x_range=[0, q.HUMPS_SHOWN * PI, PLOT_STEP], color=colour)


class SincImproperIntegral(StudyScene):
    def construct(self) -> None:
        self.the_function()
        self.two_questions()
        self.humps()
        self.lower_bound()
        self.divergence()
        self.alternating_series()
        self.between_multiples_of_pi()
        self.summary()

    # Beat 1 ---------------------------------------------------------------------------------------------------
    def the_function(self) -> None:
        self.beat("the-function", r"Is $\dfrac{\sin x}{x}$ integrable?")
        definition = MathTex(r"f(x)=\begin{cases}\dfrac{\sin x}{x}, & x\neq 0,\\[4pt] 1, & x=0\end{cases}",
                             font_size=FORMULA_SIZE).to_corner(UL)
        axes = hump_axes([-0.4, 1.1, 0.5], 3.6).to_edge(DOWN, buff=1.5)
        self.play(Write(definition))
        self.play(Create(axes), Create(sinc_graph(axes, Palette.PRIMARY), run_time=3))
        self.say(r"$f$ is continuous on $\mathbb{R}$ (the value $1$ at $0$ fills the hole), so it is measurable.")
        self.say(r"$f$ is even, so $\int_{\mathbb{R}}|f|\,dm = 2\int_{[0,\infty)}|f|\,dm$: \\ "
                 r"we can work on $[0,\infty)$.")

    # Beat 2 ---------------------------------------------------------------------------------------------------
    def two_questions(self) -> None:
        self.beat("two-questions", "Two different questions")
        integrable = boxed(MathTex(r"f\in L^1(\mathbb{R}) \iff \int_{\mathbb{R}} |f|\,dm < \infty",
                                   font_size=FORMULA_SIZE))
        improper = boxed(MathTex(r"\lim_{T\to\infty}\ \int_{[0,T]} f\,dm \ \text{ exists?}",
                                 font_size=FORMULA_SIZE), color=Palette.BOUND)
        VGroup(integrable, improper).arrange(DOWN, buff=0.8).shift(0.4 * UP)
        self.play(FadeIn(integrable))
        self.say(r"Question 1 is about $|f|$: positive and negative parts cannot cancel.")
        self.play(FadeIn(improper))
        self.say(r"Question 2 is about $f$ itself: positive and negative areas may cancel as $T$ grows.")
        self.say(r"On $[0,T]$, $f$ is bounded and continuous, \\ "
                 r"so $\int_{[0,T]} f\,dm$ is the Riemann integral $\int_0^T f(x)\,dx$.")

    # Beat 3 ---------------------------------------------------------------------------------------------------
    def humps(self) -> None:
        self.beat("humps", r"Cut $[0,\infty)$ into humps", r"$[k\pi,(k+1)\pi]$, $k=0,1,2,\dots$")
        axes = hump_axes([-0.4, 1.1, 0.5], 3.6).to_edge(DOWN, buff=1.5)
        graph = sinc_graph(axes, Palette.TEXT)
        areas = VGroup(*[
            axes.get_area(graph, x_range=(k * PI, (k + 1) * PI), color=sign_colour(k), opacity=AREA_OPACITY)
            for k in range(q.HUMPS_SHOWN)
        ])
        definition = MathTex(r"A_k=\int_{[k\pi,(k+1)\pi]} |f|\,dm", font_size=FORMULA_SIZE).to_corner(UL)
        self.play(Create(axes), Create(graph))
        self.play(LaggedStart(*[FadeIn(area) for area in areas], lag_ratio=0.15))
        self.say(r"On each hump $\sin x$ keeps one sign, so $f$ does too: \\ "
                 r"hump $k$ has signed area $(-1)^k A_k$.")
        self.play(Write(definition))
        first = q.signed_hump_areas(3)
        values = MathTex(rf"(-1)^kA_k:\quad {first[0]:+.3f},\ \ {first[1]:+.3f},\ \ {first[2]:+.3f},\ \dots",
                         font_size=STEP_SIZE).to_corner(UR)
        self.play(FadeIn(values))
        self.say(r"Blue humps count positively, orange humps negatively.")

    # Beat 4 ---------------------------------------------------------------------------------------------------
    def lower_bound(self) -> None:
        self.beat("lower-bound", r"How big is hump $k$?", r"a lower bound that does not shrink too fast")
        k = 2
        start, end = k * PI, (k + 1) * PI
        axes = plain_axes([start, end, PI / 4], [0, 0.16, 0.05], 5.6, 4).to_edge(LEFT, buff=0.6).shift(0.4 * UP)
        axes.get_x_axis().add_labels({start: pi_label(k), end: pi_label(k + 1)})
        absolute = axes.plot(lambda x: abs(q.f(x)), x_range=[start, end, PLOT_STEP / 4], color=Palette.PRIMARY)
        bound = axes.plot(lambda x: abs(math.sin(x)) / end, x_range=[start, end, PLOT_STEP / 4], color=Palette.BOUND)
        absolute_area = axes.get_area(absolute, x_range=(start, end), color=Palette.PRIMARY, opacity=0.35)
        bound_area = axes.get_area(bound, x_range=(start, end), color=Palette.BOUND, opacity=0.6)
        steps = VGroup(
            MathTex(r"x\in[k\pi,(k+1)\pi]\ \Rightarrow\ |f(x)|\ \ge\ \frac{|\sin x|}{(k+1)\pi}",
                    font_size=STEP_SIZE),
            MathTex(r"A_k\ \ge\ \frac{1}{(k+1)\pi}\int_{k\pi}^{(k+1)\pi}|\sin x|\,dx", font_size=STEP_SIZE),
            MathTex(r"=\ \frac{2}{(k+1)\pi}", font_size=STEP_SIZE, color=Palette.BOUND),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.35).to_edge(RIGHT, buff=0.5).shift(0.9 * UP)
        self.play(Create(axes), Create(absolute), FadeIn(absolute_area))
        self.say(r"Hump $k=2$: the blue area is $A_2$.")
        self.play(Write(steps[0]), Create(bound), FadeIn(bound_area))
        self.say(r"On the hump $x\le (k+1)\pi$, so $|f|$ lies above $|\sin x|/((k+1)\pi)$ (green).")
        self.play(Write(steps[1]))
        self.play(Write(steps[2]))
        self.say(r"Each hump of $|\sin x|$ has area $2$, so $A_k \ge \dfrac{2}{(k+1)\pi}$.")
        area, lower = q.hump_areas(k + 1)[k], q.hump_lower_bounds(k + 1)[k]
        example = MathTex(rf"k=2:\quad A_2\approx {area:.4f}\ \ge\ \frac{{2}}{{3\pi}}\approx {lower:.4f}",
                          font_size=STEP_SIZE, color=Palette.HIGHLIGHT)
        example.next_to(steps, DOWN, buff=0.6, aligned_edge=LEFT)
        self.play(Write(example))
        self.wait(2)

    # Beat 5 ---------------------------------------------------------------------------------------------------
    def divergence(self) -> None:
        self.beat("divergence", r"Adding up the humps of $|f|$")
        axes = plain_axes([0, q.HUMPS_SHOWN, 1], [0, 2, 0.5], 9, 3.8).to_edge(LEFT, buff=0.7).shift(0.1 * DOWN)
        axes.get_x_axis().add_labels({k + 0.5: muted_label(str(k)) for k in range(0, q.HUMPS_SHOWN, 2)})
        add_y_labels(axes, [0.5, 1, 1.5, 2])
        k_label = muted_label("k").next_to(axes.get_x_axis(), RIGHT, buff=0.2)
        areas, bounds = q.hump_areas(q.HUMPS_SHOWN), q.hump_lower_bounds(q.HUMPS_SHOWN)
        area_bars = VGroup(*[bar(axes, k + 0.12, BAR_WIDTH, a, Palette.PRIMARY) for k, a in enumerate(areas)])
        bound_bars = VGroup(*[bar(axes, k + 0.52, BAR_WIDTH, b, Palette.BOUND) for k, b in enumerate(bounds)])
        legend = VGroup(
            MathTex(r"A_k", font_size=FORMULA_SIZE, color=Palette.PRIMARY),
            MathTex(r"\frac{2}{(k+1)\pi}", font_size=FORMULA_SIZE, color=Palette.BOUND),
        ).arrange(DOWN, buff=0.4).next_to(axes, RIGHT, buff=0.7)
        self.play(Create(axes), FadeIn(k_label), FadeIn(legend))
        self.play(LaggedStart(*[GrowFromEdge(b, DOWN) for b in area_bars], lag_ratio=0.1))
        self.play(LaggedStart(*[GrowFromEdge(b, DOWN) for b in bound_bars], lag_ratio=0.1))
        self.say(r"Every blue bar is at least as tall as the green bar next to it.")
        total = MathTex(r"\int_{[0,n\pi]}|f|\,dm=\sum_{k=0}^{n-1}A_k\ \ge\ \frac{2}{\pi}\sum_{k=1}^{n}\frac{1}{k}",
                        r"\ \xrightarrow[n\to\infty]{}\ \infty", font_size=34).to_edge(UP, buff=0.3)
        self.play(Write(total))
        self.say(r"The green bars are $\tfrac{2}{\pi}$ times the harmonic series, which diverges.")
        self.play(FadeOut(VGroup(axes, k_label, legend, area_bars, bound_bars)))
        self.growth_plot(total)

    def growth_plot(self, total: MathTex) -> None:
        axes = plain_axes([0, q.DECADES_SHOWN, 1], [0, 12, 2], 8.5, 3.6).shift(0.15 * DOWN + 1.2 * LEFT)
        axes.get_x_axis().add_labels({d: muted_label(f"10^{d}") for d in range(q.DECADES_SHOWN + 1)})
        add_y_labels(axes, list(range(2, 13, 2)))
        x_label = muted_label(r"n\ \text{(log scale)}").next_to(axes.get_x_axis(), RIGHT, buff=0.25)
        n = q.growth_grid()
        decades = np.log10(n)
        growth = axes.plot_line_graph(decades, q.absolute_integral_to(n), add_vertex_dots=False,
                                      line_color=Palette.PRIMARY, stroke_width=4)["line_graph"]
        harmonic = axes.plot_line_graph(decades, q.harmonic_bound_to(n), add_vertex_dots=False,
                                        line_color=Palette.BOUND, stroke_width=4)["line_graph"]
        labels = VGroup(
            MathTex(r"\int_{[0,n\pi]}|f|\,dm", font_size=FORMULA_SIZE, color=Palette.PRIMARY),
            MathTex(r"\frac{2}{\pi}\sum_{k=1}^{n}\frac1k", font_size=FORMULA_SIZE, color=Palette.BOUND),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.5).next_to(axes, RIGHT, buff=1.2).shift(0.5 * UP)
        self.play(Create(axes), FadeIn(x_label))
        self.play(Create(growth, run_time=2), Create(harmonic, run_time=2), FadeIn(labels))
        self.say(r"Each tenfold increase of $n$ adds about $\tfrac{2}{\pi}\ln 10\approx 1.47$: \\ "
                 r"slow, but without bound.")
        conclusion = boxed(MathTex(r"\int_{[0,\infty)}|f|\,dm=\lim_{n\to\infty}\int_{[0,n\pi]}|f|\,dm=\infty",
                                   r"\ \Rightarrow\ f\notin L^1(\mathbb{R})", font_size=34))
        conclusion.move_to(total)
        self.play(FadeOut(total), FadeIn(conclusion))
        self.say(r"The first equality is the Monotone Convergence Theorem: \\ "
                 r"$|f|\,\chi_{[0,n\pi]}$ increases to $|f|\,\chi_{[0,\infty)}$.", hold=LONG_HOLD)

    # Beat 6 ---------------------------------------------------------------------------------------------------
    def alternating_series(self) -> None:
        self.beat("alternating-series", "Now let the signs cancel",
                  r"$\int_{[0,n\pi]} f\,dm=\sum_{k=0}^{n-1}(-1)^k A_k$")
        facts = VGroup(
            MathTex(r"A_{k+1}=\int_{k\pi}^{(k+1)\pi}\frac{|\sin y|}{y+\pi}\,dy"
                    r"\ <\ \int_{k\pi}^{(k+1)\pi}|f(y)|\,dy=A_k", font_size=34),
            MathTex(r"A_k\ \le\ \frac{2}{k\pi}\ \to\ 0\quad(k\ge1)", font_size=34),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.45).to_edge(UP, buff=0.4)
        self.play(Write(facts[0]))
        self.say(r"Substitute $x=y+\pi$: the next hump has the same $|\sin|$ \\ "
                 r"but a larger denominator, so $A_{k+1}<A_k$.")
        self.play(Write(facts[1]))
        self.say(r"On hump $k\ge1$, $x\ge k\pi$, so $A_k\le\dfrac{2}{k\pi}$: the humps shrink to $0$.")
        axes = plain_axes([0, q.HUMPS_SHOWN + 1, 1], [1.3, 1.9, 0.1], 10, 2.6).to_edge(DOWN, buff=1.7)
        axes.get_x_axis().add_labels({n: muted_label(str(n)) for n in range(2, 13, 2)})
        add_y_labels(axes, [1.4, 1.6, 1.8])
        n_label = muted_label("n").next_to(axes.get_x_axis(), RIGHT, buff=0.2)
        partial_sums = q.running_integral(np.arange(1, q.HUMPS_SHOWN + 1) * math.pi)
        dots = VGroup(*[Dot(axes.c2p(n, s), color=Palette.HIGHLIGHT, radius=0.07)
                        for n, s in enumerate(partial_sums, start=1)])
        steps = VGroup(*[Line(axes.c2p(n, partial_sums[n - 1]), axes.c2p(n + 1, partial_sums[n]),
                              color=Palette.MUTED, stroke_width=2) for n in range(1, q.HUMPS_SHOWN)])
        label = MathTex(r"F(n\pi)=\int_{[0,n\pi]}f\,dm", font_size=30).next_to(axes, UP, buff=0.05).to_edge(RIGHT)
        self.play(Create(axes), FadeIn(n_label), FadeIn(label))
        self.play(LaggedStart(*[FadeIn(dot) for dot in dots], lag_ratio=0.2), Create(steps, run_time=3))
        self.say(r"Alternating signs, sizes decreasing to $0$: \\ "
                 r"by the alternating series test, $F(n\pi)$ converges to some $L$.")

    # Beat 7 ---------------------------------------------------------------------------------------------------
    def between_multiples_of_pi(self) -> None:
        self.beat("between-multiples", r"What about $T$ between multiples of $\pi$?")
        axes = hump_axes([0, 2, 0.5], 4.2).to_edge(DOWN, buff=1.5)
        add_y_labels(axes, [0.5, 1, 1.5, 2])
        right_end = q.HUMPS_SHOWN * PI
        running = axes.plot(q.running_integral, x_range=[0, right_end, PLOT_STEP], color=Palette.PRIMARY)
        limit_line = DashedLine(axes.c2p(0, q.LIMIT), axes.c2p(right_end, q.LIMIT), color=Palette.BOUND)
        limit_label = MathTex(r"L=\tfrac{\pi}{2}", font_size=FORMULA_SIZE, color=Palette.BOUND)
        limit_label.next_to(axes.c2p(10.5 * PI, q.LIMIT), UP, buff=0.3)
        dots = VGroup(*[Dot(axes.c2p(n * PI, float(q.running_integral(n * PI))), radius=0.06,
                            color=Palette.HIGHLIGHT) for n in range(1, q.HUMPS_SHOWN + 1)])
        title = MathTex(r"F(T)=\int_{[0,T]} f\,dm", font_size=FORMULA_SIZE).to_corner(UL)
        self.play(Write(title), Create(axes))
        tracker = ValueTracker(0.01)
        moving = always_redraw(lambda: Dot(
            axes.c2p(tracker.get_value(), float(q.running_integral(tracker.get_value()))),
            color=Palette.TEXT, radius=0.08))
        self.add(moving)
        self.play(Create(running), tracker.animate.set_value(right_end), run_time=5)
        self.play(FadeIn(dots))
        self.say(r"On hump $n$, $f$ has one sign, so $F$ is monotone there: \\ "
                 r"$F(T)$ lies between $F(n\pi)$ and $F((n+1)\pi)$.", hold=LONG_HOLD)
        squeeze = MathTex(r"|F(T)-L|\le\max\big(|F(n\pi)-L|,\,|F((n+1)\pi)-L|\big),\quad n=\lfloor T/\pi\rfloor",
                          font_size=30).to_corner(UR)
        self.play(Write(squeeze))
        self.say(r"As $T\to\infty$, $n=\lfloor T/\pi\rfloor\to\infty$ and both ends tend to $L$, \\ "
                 r"so $F(T)\to L$ through all real $T$, not only multiples of $\pi$.", hold=LONG_HOLD)
        self.play(Create(limit_line), FadeIn(limit_label))
        self.say(r"In fact $L=\pi/2$ exactly (Dirichlet's integral, proved by other means). \\ "
                 r"Existence did not need this value.", hold=LONG_HOLD)

    # Beat 8 ---------------------------------------------------------------------------------------------------
    def summary(self) -> None:
        self.beat("summary", "Summary")
        absolute = VGroup(
            Tex("Absolute areas", font_size=36, color=Palette.PRIMARY),
            MathTex(r"\sum_{k=0}^{\infty} A_k\ \ge\ \frac{2}{\pi}\sum_{k=0}^{\infty}\frac{1}{k+1}=\infty",
                    font_size=34),
            MathTex(r"\Rightarrow\ f\notin L^1(\mathbb{R})", font_size=36),
        ).arrange(DOWN, buff=0.45)
        signed = VGroup(
            Tex("Signed areas", font_size=36, color=Palette.BOUND),
            MathTex(r"\sum_{k=0}^{\infty} (-1)^k A_k,\quad A_k\downarrow 0", font_size=34),
            MathTex(r"+\ F\ \text{monotone on each hump}", font_size=34),
            MathTex(r"\Rightarrow\ \lim_{T\to\infty}\int_{[0,T]}f\,dm\ \text{exists}", font_size=36),
        ).arrange(DOWN, buff=0.45)
        VGroup(absolute, signed).arrange(RIGHT, buff=1.4, aligned_edge=UP).shift(0.5 * UP)
        self.play(FadeIn(absolute, shift=RIGHT * 0.3))
        self.play(FadeIn(signed, shift=LEFT * 0.3))
        self.say(r"The Lebesgue integral is absolute: $f\in L^1$ needs $\int|f|\,dm<\infty$.")
        self.say(r"Cancellation can rescue an improper integral, but never Lebesgue integrability.", hold=3)
