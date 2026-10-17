"""How Gauss-Newton fits a linear regression model, and why it needs exactly one step.

Render: uv run <skill>/visualize/scripts/render_scene.py scene.py GaussNewtonLinearRegression --quality preview
Every number shown comes from quantities.py; run it first to check the claims.
"""

from __future__ import annotations

import math

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    Arrow,
    Axes,
    Create,
    DashedVMobject,
    Dot,
    FadeIn,
    LaggedStart,
    Line,
    MathTex,
    Star,
    Tex,
    ValueTracker,
    VGroup,
    VMobject,
    Write,
    always_redraw,
)
import numpy as np

import quantities as q
from scene_kit import Palette, StudyScene

FORMULA_SIZE = 36
STEP_SIZE = 32
LABEL_SIZE = 24
NUMBER_SIZE = 30
SCORE_SIZE = 26
STAR_CLEARANCE = 0.22   # arrows stop short of the solution star instead of covering it
LONG_HOLD = 2.5
DATA_DOT_RADIUS = 0.07
DATA_T_RANGE = [0, 18, 2]
DATA_Y_RANGE = [0, 240, 50]


def muted(text: str, size: int = LABEL_SIZE) -> MathTex:
    return MathTex(text, font_size=size, color=Palette.MUTED)


def axes_with_labels(x_range, y_range, x_length, y_length, x_title: str, y_title: str) -> VGroup:
    axes = Axes(x_range=x_range, y_range=y_range, x_length=x_length, y_length=y_length, tips=False,
                axis_config={"color": Palette.MUTED, "include_numbers": True, "font_size": LABEL_SIZE})
    titles = VGroup(muted(x_title).next_to(axes.get_x_axis(), DOWN, buff=0.45),
                    muted(y_title).next_to(axes.get_y_axis(), UP, buff=0.15))
    return VGroup(axes, titles)


def data_panel(x_length: float = 6.0, y_length: float = 4.2) -> tuple[Axes, VGroup]:
    group = axes_with_labels(DATA_T_RANGE, DATA_Y_RANGE, x_length, y_length, r"t\ \text{(min)}",
                             r"\text{thickness (nm)}")
    axes = group[0]
    dots = VGroup(*[Dot(axes.c2p(t, y), radius=DATA_DOT_RADIUS, color=Palette.PRIMARY)
                    for t, y in zip(q.DEPOSITION_MINUTES, q.THICKNESS_NM, strict=True)])
    return axes, VGroup(group, dots)


def model_line(axes: Axes, beta: np.ndarray, colour: str) -> Line:
    end = DATA_T_RANGE[1]
    return Line(axes.c2p(0, beta[0]), axes.c2p(end, beta[0] + beta[1] * end), color=colour, stroke_width=4)


def residual_segments(axes: Axes, beta: np.ndarray) -> VGroup:
    return VGroup(*[Line(axes.c2p(t, y), axes.c2p(t, beta[0] + beta[1] * t), color=Palette.ACCENT, stroke_width=3)
                    for t, y in zip(q.DEPOSITION_MINUTES, q.THICKNESS_NM, strict=True)])


def parameter_panel(window: q.ParameterWindow, x_length: float, y_length: float, step: tuple[float, float],
                    titles: tuple[str, str]) -> VGroup:
    return axes_with_labels([*window.first, step[0]], [*window.second, step[1]], x_length, y_length, *titles)


def scale_note(plane: Axes) -> MathTex:
    """Parameter axes have different units; say so, because unequal scales distort angles and shapes."""
    return muted(r"\text{axes not to equal scale}").next_to(plane, DOWN, buff=0.05).align_to(plane, RIGHT)


def contour_mobjects(axes: Axes, lines_per_level: list[list[np.ndarray]]) -> VGroup:
    """Contour polylines; inner levels drawn brighter so the valley floor reads first."""
    group = VGroup()
    for level_index, lines in enumerate(lines_per_level):
        opacity = 0.9 - 0.12 * level_index
        for line in lines:
            if len(line) < 2:
                continue
            path = VMobject(stroke_color=Palette.MUTED, stroke_width=2, stroke_opacity=opacity)
            path.set_points_as_corners([axes.c2p(*point) for point in line])
            group.add(path)
    return group


def column(values: np.ndarray, digits: int) -> str:
    entries = r"\\".join(f"{value:.{digits}f}" for value in values)
    return rf"\begin{{bmatrix}}{entries}\end{{bmatrix}}"


def iterate_label(index: int) -> MathTex:
    return MathTex(rf"\beta^{{({index})}}", font_size=NUMBER_SIZE)


class GaussNewtonLinearRegression(StudyScene):
    def construct(self) -> None:
        self.least_squares_problem()
        self.residual_vector()
        self.gauss_newton_recipe()
        self.worked_step()
        self.watch_the_step()
        self.why_one_step()
        self.compare_gradient_descent()
        self.nonlinear_contrast()
        self.summary()

    # Beat 1 ---------------------------------------------------------------------------------------------------
    def least_squares_problem(self) -> None:
        self.beat("problem", "Fitting a line by least squares", r"Gauss--Newton, from the ground up")
        axes, panel = data_panel()
        panel.to_edge(LEFT, buff=0.8).shift(0.3 * UP)
        self.play(Create(panel[0]), LaggedStart(*[FadeIn(dot) for dot in panel[1]], lag_ratio=0.1))
        self.say(r"Simulated data: oxide thickness on 8 wafers after 2--16 minutes of deposition.")
        formulas = VGroup(
            MathTex(r"y_i\ \approx\ \beta_0+\beta_1 t_i", font_size=FORMULA_SIZE),
            MathTex(r"r_i(\beta)=y_i-(\beta_0+\beta_1 t_i)", font_size=FORMULA_SIZE),
            MathTex(r"S(\beta)=\tfrac12\sum_{i=1}^{8} r_i(\beta)^2", font_size=FORMULA_SIZE),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.45).to_edge(RIGHT, buff=0.7).shift(0.5 * UP)
        self.play(Write(formulas[0]))
        guess = model_line(axes, q.LINEAR_START, Palette.SECONDARY)
        residuals = residual_segments(axes, q.LINEAR_START)
        start = q.LINEAR_START
        self.play(Create(guess), Write(formulas[1]))
        self.play(Create(residuals))
        self.say(rf"A first guess $\beta^{{(0)}}=({start[0]:g},\,{start[1]:g})$ (orange) "
                 r"leaves residuals $r_i$ (pink).")
        self.play(Write(formulas[2]))
        self.say(r"Least squares: choose $\beta=(\beta_0,\beta_1)$ to make $S(\beta)$ as small as possible.")

    # Beat 2 ---------------------------------------------------------------------------------------------------
    def residual_vector(self) -> None:
        self.beat("residual-vector", "Stack the residuals into a vector")
        times = q.DEPOSITION_MINUTES
        design = (rf"X=\begin{{bmatrix}}1&{times[0]:g}\\1&{times[1]:g}\\ \vdots&\vdots\\1&{times[-1]:g}"
                  r"\end{bmatrix}")
        lines = VGroup(
            MathTex(r"r(\beta)=y-X\beta,\qquad", design, r",\qquad \beta=\begin{bmatrix}\beta_0\\ \beta_1\end{bmatrix}",
                    font_size=FORMULA_SIZE),
            MathTex(r"S(\beta)=\tfrac12\,\lVert r(\beta)\rVert^2", font_size=FORMULA_SIZE),
            MathTex(r"J=\frac{\partial r}{\partial \beta}=-X", font_size=FORMULA_SIZE, color=Palette.HIGHLIGHT),
        ).arrange(DOWN, buff=0.55).shift(0.3 * UP)
        self.play(Write(lines[0]))
        self.say(r"Row $i$ of $X$ is $(1, t_i)$, so the residual vector $r(\beta)\in\mathbb{R}^8$ "
                 r"is affine in $\beta$.")
        self.play(Write(lines[1]))
        self.play(Write(lines[2]))
        self.say(r"Its Jacobian $J=\partial r/\partial\beta$ is $-X$ at every $\beta$. Remember this.", hold=LONG_HOLD)

    # Beat 3 ---------------------------------------------------------------------------------------------------
    def gauss_newton_recipe(self) -> None:
        self.beat("gauss-newton-step", "The Gauss--Newton step", "linearize, solve, update")
        steps = VGroup(
            VGroup(Tex("1. Linearize", font_size=STEP_SIZE, color=Palette.MUTED),
                   MathTex(r"r(\beta+\Delta)\ \approx\ r(\beta)+J\Delta", font_size=FORMULA_SIZE)),
            VGroup(Tex("2. Solve", font_size=STEP_SIZE, color=Palette.MUTED),
                   MathTex(r"\Delta\ \text{minimizes}\ \tfrac12\lVert r(\beta)+J\Delta\rVert^2"
                           r"\iff J^{\top}J\,\Delta=-J^{\top}r(\beta)", font_size=FORMULA_SIZE)),
            VGroup(Tex("3. Update", font_size=STEP_SIZE, color=Palette.MUTED),
                   MathTex(r"\beta\ \leftarrow\ \beta+\Delta", font_size=FORMULA_SIZE)),
        )
        for step in steps:
            step.arrange(RIGHT, buff=0.5)
        steps.arrange(DOWN, aligned_edge=LEFT, buff=0.6).shift(0.4 * UP)
        self.play(FadeIn(steps[0]))
        self.say(r"Replace the residual by its first-order Taylor model around the current $\beta$.")
        self.play(FadeIn(steps[1]))
        self.say(r"The model is a linear least-squares problem in $\Delta$: \\ "
                 r"its minimizers solve the normal equations, unique when $J$ has full column rank.", hold=LONG_HOLD)
        self.play(FadeIn(steps[2]))
        self.say(r"For a line, $J=-X$: the equations read $X^{\top}X\,\Delta=X^{\top}r(\beta)$.", hold=LONG_HOLD)

    # Beat 4 ---------------------------------------------------------------------------------------------------
    def worked_step(self) -> None:
        start = q.LINEAR_START
        self.beat("worked-step", "One step, in numbers", rf"from $\beta^{{(0)}}=({start[0]:g},\,{start[1]:g})$")
        residual = q.linear_residual(start)
        normal = q.normal_matrix()
        right_side = q.design_matrix().T @ residual
        delta = q.linear_step(start)
        after = start + delta
        rows = VGroup(
            MathTex(r"r^{(0)}=y-X\beta^{(0)}=(" + ",\\ ".join(f"{v:.1f}" for v in residual) + r")^{\top}",
                    font_size=STEP_SIZE),
            MathTex(rf"X^{{\top}}X=\begin{{bmatrix}}{normal[0, 0]:g}&{normal[0, 1]:g}\\{normal[1, 0]:g}&"
                    rf"{normal[1, 1]:g}\end{{bmatrix}},\qquad X^{{\top}}r^{{(0)}}=" + column(right_side, 1),
                    font_size=STEP_SIZE),
            MathTex(r"\Delta=(X^{\top}X)^{-1}X^{\top}r^{(0)}=" + column(delta, 3), font_size=STEP_SIZE),
            MathTex(r"\beta^{(1)}=\beta^{(0)}+\Delta=" + column(after, 3), font_size=STEP_SIZE,
                    color=Palette.BOUND),
        ).arrange(DOWN, buff=0.4).shift(0.35 * UP)
        self.play(Write(rows[0]))
        self.say(r"Residuals of the first guess: negative where that line lies above the data ($t\le 6$).")
        self.play(Write(rows[1]))
        self.say(r"$X^{\top}X$ holds $n=8$, $\sum t_i$ and $\sum t_i^2$; "
                 r"$X^{\top}r$ holds $\sum r_i$ and $\sum t_i r_i$.")
        self.play(Write(rows[2]))
        self.play(Write(rows[3]))
        self.say(rf"New fit: intercept {after[0]:.2f} nm, deposition rate {after[1]:.2f} nm/min.", hold=LONG_HOLD)

    # Beat 5 ---------------------------------------------------------------------------------------------------
    def watch_the_step(self) -> None:
        self.beat("one-step", "Watch the step", r"data space and parameter space")
        data_axes, data = data_panel(4.6, 3.6)
        data.to_edge(LEFT, buff=0.5).shift(0.5 * UP)
        window = q.LINEAR_WINDOW
        parameters = parameter_panel(window, 6.6, 4.2, (20, 4), (r"\beta_0", r"\beta_1"))
        parameters.to_edge(RIGHT, buff=0.5).shift(0.5 * UP)
        plane = parameters[0]
        contours = contour_mobjects(plane, q.contour_lines(q.linear_objective, window, q.linear_levels()))
        start, delta = q.LINEAR_START, q.linear_step(q.LINEAR_START)
        solution = start + delta
        self.play(Create(data), Create(parameters))
        self.play(Create(contours, run_time=2))
        self.play(FadeIn(scale_note(plane)))
        self.say(r"Contours of $S$ are ellipses: $S$ is a quadratic with positive-definite Hessian $X^{\top}X$.")
        alpha = ValueTracker(0)

        def current() -> np.ndarray:
            return start + alpha.get_value() * delta

        line = always_redraw(lambda: model_line(data_axes, current(), Palette.SECONDARY))
        residuals = always_redraw(lambda: residual_segments(data_axes, current()))
        point = always_redraw(lambda: Dot(plane.c2p(*current()), color=Palette.SECONDARY, radius=0.09))
        start_label = iterate_label(0).next_to(plane.c2p(*start), UP, buff=0.15)
        self.play(FadeIn(line), FadeIn(residuals), FadeIn(point), FadeIn(start_label))
        arrow = Arrow(plane.c2p(*start), plane.c2p(*solution), buff=STAR_CLEARANCE, color=Palette.BOUND,
                      stroke_width=5, max_tip_length_to_length_ratio=0.08)
        self.play(Create(arrow))
        self.play(alpha.animate.set_value(1), run_time=3)
        star = Star(n=5, outer_radius=0.16, color=Palette.BOUND, fill_opacity=1).move_to(plane.c2p(*solution))
        solution_label = iterate_label(1).next_to(star, UP + LEFT, buff=0.1)
        self.play(FadeIn(star), FadeIn(solution_label))
        self.say(r"One Gauss--Newton step lands exactly on the minimizer $\hat\beta$.")
        self.say(r"The next step is $\Delta=0$: at $\hat\beta$, $X^{\top}r(\hat\beta)=0$, \\ "
                 r"the residual vector is orthogonal to both columns of $X$.", hold=LONG_HOLD)

    # Beat 6 ---------------------------------------------------------------------------------------------------
    def why_one_step(self) -> None:
        self.beat("why-one-step", "Why exactly one step?")
        alphas, actual, model = q.model_and_actual_along_step(q.linear_residual, q.linear_jacobian, q.LINEAR_START)
        group = axes_with_labels([0, 1.25, 0.25], [0, 8000, 2000], 6.0, 3.8, r"\alpha",
                                 r"S(\beta^{(0)}+\alpha\Delta)")
        axes = group[0]
        group.to_edge(LEFT, buff=0.8).shift(0.4 * UP)
        actual_curve = axes.plot_line_graph(alphas, actual, add_vertex_dots=False, line_color=Palette.PRIMARY,
                                            stroke_width=6)["line_graph"]
        model_curve = DashedVMobject(axes.plot_line_graph(alphas, model, add_vertex_dots=False,
                                                          line_color=Palette.HIGHLIGHT, stroke_width=3)["line_graph"],
                                     num_dashes=40)
        legend = VGroup(MathTex(r"S\ \text{along the step}", font_size=28, color=Palette.PRIMARY),
                        MathTex(r"\tfrac12\lVert r+\alpha J\Delta\rVert^2\ \text{(model)}", font_size=28,
                                color=Palette.HIGHLIGHT)).arrange(DOWN, aligned_edge=LEFT).next_to(axes, UP, buff=0.2)
        reasons = VGroup(
            MathTex(r"r(\beta+\Delta)=y-X\beta-X\Delta", font_size=STEP_SIZE),
            MathTex(r"=r(\beta)+J\Delta\quad\text{exactly}", font_size=STEP_SIZE, color=Palette.HIGHLIGHT),
            MathTex(r"\nabla^2 S=J^{\top}J+\sum_i r_i\nabla^2 r_i", font_size=STEP_SIZE),
            MathTex(r"=X^{\top}X\quad(\nabla^2 r_i=0)", font_size=STEP_SIZE, color=Palette.HIGHLIGHT),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.35).to_edge(RIGHT, buff=0.6).shift(0.5 * UP)
        self.play(Create(group))
        self.play(Create(actual_curve), FadeIn(legend[0]))
        self.play(Create(model_curve), FadeIn(legend[1]))
        self.say(r"Along the step, the Gauss--Newton model (dashed) and $S$ itself (solid) coincide.")
        self.play(Write(reasons[0]), Write(reasons[1]))
        self.say(r"For a line the linearization is not an approximation: it is exact.")
        self.play(Write(reasons[2]), Write(reasons[3]))
        self.say(r"So $S$ is a quadratic with Hessian $X^{\top}X$, \\ "
                 r"positive definite because the $t_i$ are not all equal.", hold=LONG_HOLD)
        self.say(r"Gauss--Newton is Newton's method here, and Newton's method minimizes \\ "
                 r"a strictly convex quadratic in one step.", hold=LONG_HOLD)

    # Beat 7 ---------------------------------------------------------------------------------------------------
    def compare_gradient_descent(self) -> None:
        self.beat("gradient-descent", "Compared with gradient descent", r"same start, same contours")
        window = q.LINEAR_WINDOW
        parameters = parameter_panel(window, 7.0, 4.4, (20, 4), (r"\beta_0", r"\beta_1"))
        parameters.to_edge(LEFT, buff=0.7).shift(0.6 * UP)
        plane = parameters[0]
        contours = contour_mobjects(plane, q.contour_lines(q.linear_objective, window, q.linear_levels()))
        path = q.gradient_descent_path(q.GRADIENT_STEPS_SHOWN)
        descent = VMobject(stroke_color=Palette.SECONDARY, stroke_width=3)
        descent.set_points_as_corners([plane.c2p(*beta) for beta in path])
        descent_dots = VGroup(*[Dot(plane.c2p(*beta), radius=0.035, color=Palette.SECONDARY) for beta in path])
        solution = q.least_squares_solution()
        jump = Arrow(plane.c2p(*q.LINEAR_START), plane.c2p(*solution), buff=STAR_CLEARANCE, color=Palette.BOUND,
                     stroke_width=5, max_tip_length_to_length_ratio=0.06)
        condition_number = q.condition_number(q.normal_matrix())
        scores = VGroup(
            MathTex(rf"\text{{gradient descent, {q.GRADIENT_STEPS_SHOWN} steps: }} S\approx "
                    rf"{q.linear_objective(path[-1]):.0f}", font_size=SCORE_SIZE, color=Palette.SECONDARY),
            MathTex(rf"\text{{Gauss--Newton, 1 step: }} S\approx {q.linear_objective(solution):.1f}",
                    font_size=SCORE_SIZE, color=Palette.BOUND),
            MathTex(r"\kappa(X^{\top}X)=\lambda_{\max}/\lambda_{\min}\approx " + f"{condition_number:.0f}",
                    font_size=SCORE_SIZE),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.35).next_to(parameters, RIGHT, buff=0.4).shift(0.3 * UP)
        self.play(Create(parameters), Create(contours), FadeIn(scale_note(plane)))
        self.play(Create(descent, run_time=4), FadeIn(descent_dots, run_time=4))
        self.say(r"Gradient descent with step $1/\lambda_{\max}(X^{\top}X)$ drops into the valley, \\ "
                 r"then crawls along its floor.", hold=LONG_HOLD)
        self.play(Create(jump))
        self.play(FadeIn(scores))
        centred = q.condition_number(q.centred_normal_matrix())
        self.say(rf"The valley is long and narrow because $X^{{\top}}X$ is badly conditioned; \\ "
                 rf"centring the times would bring $\kappa$ down to {centred:.0f}.", hold=LONG_HOLD)
        self.say(r"Gauss--Newton uses the curvature $J^{\top}J$: \\ "
                 r"in exact arithmetic the valley's shape costs it nothing.", hold=LONG_HOLD)

    # Beat 8 ---------------------------------------------------------------------------------------------------
    def nonlinear_contrast(self) -> None:
        self.beat("nonlinear", "When the model is not linear",
                  r"$y\approx a\,e^{-bt}$: wafer cooling after an anneal (simulated)")
        data_group = axes_with_labels([0, 15, 3], [0, 450, 100], 4.6, 3.6, r"t\ \text{(s)}",
                                      r"\text{degrees above ambient}")
        data_axes = data_group[0]
        data_group.to_edge(LEFT, buff=0.5).shift(0.5 * UP)
        dots = VGroup(*[Dot(data_axes.c2p(t, y), radius=DATA_DOT_RADIUS, color=Palette.PRIMARY)
                        for t, y in zip(q.COOLING_SECONDS, q.COOLING_DEGREES_ABOVE_AMBIENT, strict=True)])
        window = q.NONLINEAR_WINDOW
        parameters = parameter_panel(window, 6.0, 4.0, (50, 0.05), ("a", "b"))
        parameters.to_edge(RIGHT, buff=0.5).shift(0.5 * UP)
        plane = parameters[0]
        contours = contour_mobjects(plane, q.contour_lines(q.cooling_objective, window, q.nonlinear_levels()))
        jacobian = MathTex(r"\text{row } i \text{ of } J(a,b):\ \big[\,-e^{-bt_i}\ \ \ a\,t_i\,e^{-bt_i}\,\big]",
                           font_size=30)
        jacobian.to_edge(UP, buff=0.2)
        iterates = q.nonlinear_iterates(q.NONLINEAR_ITERATIONS_SHOWN)
        self.play(Create(data_group), FadeIn(dots), Create(parameters), Create(contours, run_time=2),
                  FadeIn(scale_note(plane)))
        self.play(Write(jacobian))
        self.say(r"Now $J$ depends on $(a,b)$: the linear model of $r$ is only an approximation.")
        curve = data_axes.plot(lambda t: iterates[0][0] * math.exp(-iterates[0][1] * t), x_range=[0, 15],
                               color=Palette.SECONDARY)
        point = Dot(plane.c2p(*iterates[0]), color=Palette.SECONDARY, radius=0.08)
        self.play(Create(curve), FadeIn(point))
        for index in range(1, len(iterates)):
            target = iterates[index]
            arrow = Arrow(plane.c2p(*iterates[index - 1]), plane.c2p(*target), buff=0.05, color=Palette.BOUND,
                          stroke_width=4, max_tip_length_to_length_ratio=0.12)
            new_curve = data_axes.plot(lambda t, p=target: p[0] * math.exp(-p[1] * t), x_range=[0, 15],
                                       color=Palette.SECONDARY)
            self.play(Create(arrow), point.animate.move_to(plane.c2p(*target)), curve.animate.become(new_curve),
                      run_time=1.2)
        values = r"\ \to\ ".join(f"{q.cooling_objective(p):.1f}" for p in iterates)
        self.say(rf"Each step re-linearizes. $S$: ${values}$.", hold=LONG_HOLD)
        self.say(r"Near the solution the steps shrink very fast. \\ "
                 r"From a poor start, damping (Levenberg--Marquardt) is the usual safeguard.", hold=LONG_HOLD)

    # Beat 9 ---------------------------------------------------------------------------------------------------
    def summary(self) -> None:
        self.beat("summary", "Summary")
        lines = VGroup(
            MathTex(r"\text{Gauss--Newton:}\quad J^{\top}J\,\Delta=-J^{\top}r(\beta),\quad \beta\leftarrow\beta+\Delta",
                    font_size=FORMULA_SIZE),
            MathTex(r"\text{linear model: } J=-X \text{ is constant} \Rightarrow \text{one step gives }"
                    r"X^{\top}X\hat\beta=X^{\top}y", font_size=FORMULA_SIZE, color=Palette.BOUND),
            MathTex(r"\text{nonlinear model: re-linearize and repeat until } \Delta\approx 0",
                    font_size=FORMULA_SIZE, color=Palette.SECONDARY),
        ).arrange(DOWN, buff=0.6).shift(0.4 * UP)
        for line in lines:
            self.play(FadeIn(line, shift=0.2 * UP))
        self.say(r"For a straight line, Gauss--Newton is ordinary least squares, solved in one step.", hold=3)
