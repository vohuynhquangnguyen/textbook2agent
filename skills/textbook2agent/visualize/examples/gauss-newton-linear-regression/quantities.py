# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy==2.5.3", "contourpy==1.4.0"]
# ///
"""Every number and curve in the Gauss-Newton animation, and a check of every claim the animation makes.

Linear model (simulated CVD oxide thickness y in nm after deposition time t in minutes):
    y ~ beta_0 + beta_1 t,  residual r(beta) = y - X beta,  X = [1  t],  Jacobian J = dr/dbeta = -X.
Gauss-Newton step from beta:  (J^T J) delta = -J^T r(beta),  beta <- beta + delta.
Nonlinear contrast (simulated wafer temperature above ambient after a rapid thermal anneal):
    y ~ a exp(-b t).
Run this file to check the claims: `uv run quantities.py` (exit code 1 if any claim fails).
"""

from __future__ import annotations

from dataclasses import dataclass

import contourpy
import numpy as np

# Simulated measurements (fixed so the animation is reproducible): 8 wafers, deposition time t (min), thickness (nm).
DEPOSITION_MINUTES = np.array([2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0])
THICKNESS_NM = np.array([28.0, 53.9, 77.2, 100.3, 126.6, 150.0, 178.2, 207.0])
LINEAR_START = np.array([60.0, 4.0])            # a poor first guess (beta_0, beta_1)
GRADIENT_STEPS_SHOWN = 50

# Simulated cooling curve: seconds after the anneal, temperature above ambient (degrees C).
COOLING_SECONDS = np.array([0.0, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0])
COOLING_DEGREES_ABOVE_AMBIENT = np.array([417.0, 226.8, 129.4, 71.6, 38.7, 15.3, 11.3, 10.5])
NONLINEAR_START = np.array([250.0, 0.12])       # (a, b)
NONLINEAR_ITERATIONS_SHOWN = 4

STEP_TOLERANCE = 1e-9
SETTLED_STEP = 1e-3   # "settled": the last step shown moves the parameters by less than this
SLICE_POINTS = 61
SLICE_RANGE = (0.0, 1.25)
CONTOUR_GRID = 240


@dataclass(frozen=True)
class ParameterWindow:
    """The rectangle of parameter space drawn in the animation."""

    first: tuple[float, float]
    second: tuple[float, float]


LINEAR_WINDOW = ParameterWindow((-20.0, 80.0), (0.0, 16.0))
NONLINEAR_WINDOW = ParameterWindow((200.0, 460.0), (0.05, 0.40))


# Linear model ---------------------------------------------------------------------------------------------------

def design_matrix() -> np.ndarray:
    return np.column_stack([np.ones_like(DEPOSITION_MINUTES), DEPOSITION_MINUTES])


def linear_residual(beta: np.ndarray) -> np.ndarray:
    return THICKNESS_NM - design_matrix() @ beta


def linear_jacobian(beta: np.ndarray) -> np.ndarray:
    """dr/dbeta = -X, the same for every beta: the residual is affine in beta."""
    return -design_matrix()


def objective(residual: np.ndarray) -> float:
    return 0.5 * float(residual @ residual)


def linear_objective(beta: np.ndarray) -> float:
    return objective(linear_residual(beta))


def gauss_newton_step(residual: np.ndarray, jacobian: np.ndarray) -> np.ndarray:
    """Solve (J^T J) delta = -J^T r."""
    return np.linalg.solve(jacobian.T @ jacobian, -jacobian.T @ residual)


def linear_step(beta: np.ndarray) -> np.ndarray:
    return gauss_newton_step(linear_residual(beta), linear_jacobian(beta))


def least_squares_solution() -> np.ndarray:
    """Reference solution by an independent route (QR-based least squares, no normal equations)."""
    return np.linalg.lstsq(design_matrix(), THICKNESS_NM, rcond=None)[0]


def normal_matrix() -> np.ndarray:
    return design_matrix().T @ design_matrix()


def condition_number(matrix: np.ndarray) -> float:
    eigenvalues = np.linalg.eigvalsh(matrix)
    return float(eigenvalues[-1] / eigenvalues[0])


def centred_normal_matrix() -> np.ndarray:
    """X^T X after centring the times (t - mean t): the columns become orthogonal."""
    centred = np.column_stack([np.ones_like(DEPOSITION_MINUTES), DEPOSITION_MINUTES - DEPOSITION_MINUTES.mean()])
    return centred.T @ centred


def gradient_descent_path(steps: int) -> np.ndarray:
    """Gradient descent on S with the fixed step 1/lambda_max(X^T X), from the same start."""
    step_size = 1.0 / np.linalg.eigvalsh(normal_matrix())[-1]
    path = [LINEAR_START]
    for _ in range(steps):
        gradient = -design_matrix().T @ linear_residual(path[-1])
        path.append(path[-1] - step_size * gradient)
    return np.array(path)


def model_and_actual_along_step(residual_function, jacobian_function, beta: np.ndarray):
    """S(beta + alpha delta) and the Gauss-Newton model (1/2)|r + alpha J delta|^2 for alpha in SLICE_RANGE."""
    residual, jacobian = residual_function(beta), jacobian_function(beta)
    delta = gauss_newton_step(residual, jacobian)
    alphas = np.linspace(*SLICE_RANGE, SLICE_POINTS)
    actual = np.array([objective(residual_function(beta + alpha * delta)) for alpha in alphas])
    model = np.array([objective(residual + alpha * jacobian @ delta) for alpha in alphas])
    return alphas, actual, model


# Nonlinear model ------------------------------------------------------------------------------------------------

def cooling_residual(parameters: np.ndarray) -> np.ndarray:
    amplitude, rate = parameters
    return COOLING_DEGREES_ABOVE_AMBIENT - amplitude * np.exp(-rate * COOLING_SECONDS)


def cooling_jacobian(parameters: np.ndarray) -> np.ndarray:
    """dr/d(a, b) = [-exp(-b t),  a t exp(-b t)]: it changes with the parameters."""
    amplitude, rate = parameters
    decay = np.exp(-rate * COOLING_SECONDS)
    return np.column_stack([-decay, amplitude * COOLING_SECONDS * decay])


def cooling_objective(parameters: np.ndarray) -> float:
    return objective(cooling_residual(parameters))


def nonlinear_iterates(count: int) -> np.ndarray:
    iterates = [NONLINEAR_START]
    for _ in range(count):
        current = iterates[-1]
        iterates.append(current + gauss_newton_step(cooling_residual(current), cooling_jacobian(current)))
    return np.array(iterates)


# Contours --------------------------------------------------------------------------------------------------------

def contour_lines(objective_function, window: ParameterWindow, levels: list[float]) -> list[list[np.ndarray]]:
    """For each level, the polylines (arrays of (p1, p2) points) where the objective equals that level."""
    first = np.linspace(*window.first, CONTOUR_GRID)
    second = np.linspace(*window.second, CONTOUR_GRID)
    grid_first, grid_second = np.meshgrid(first, second)
    values = np.vectorize(lambda p, s: objective_function(np.array([p, s])))(grid_first, grid_second)
    generator = contourpy.contour_generator(grid_first, grid_second, values)
    return [generator.lines(level) for level in levels]


def linear_levels() -> list[float]:
    minimum = linear_objective(least_squares_solution())
    return [minimum * factor for factor in (2, 8, 32, 128, 512, 2048)]


def nonlinear_levels() -> list[float]:
    minimum = cooling_objective(nonlinear_iterates(NONLINEAR_ITERATIONS_SHOWN)[-1])
    return [minimum * factor for factor in (2, 8, 32, 128, 512, 2048)]


# Checks: one function per claim made on screen ---------------------------------------------------------------

def check_one_step_reaches_least_squares() -> bool:
    after_one_step = LINEAR_START + linear_step(LINEAR_START)
    return bool(np.allclose(after_one_step, least_squares_solution(), atol=STEP_TOLERANCE))


def check_second_step_is_zero() -> bool:
    return bool(np.linalg.norm(linear_step(least_squares_solution())) < STEP_TOLERANCE)


def check_residual_orthogonal_to_columns() -> bool:
    return bool(np.allclose(design_matrix().T @ linear_residual(least_squares_solution()), 0, atol=1e-8))


def check_linear_model_is_exact() -> bool:
    _, actual, model = model_and_actual_along_step(linear_residual, linear_jacobian, LINEAR_START)
    return bool(np.allclose(actual, model, rtol=1e-12, atol=1e-8))


def check_nonlinear_model_is_not_exact() -> bool:
    _, actual, model = model_and_actual_along_step(cooling_residual, cooling_jacobian, NONLINEAR_START)
    return bool(np.max(np.abs(actual - model)) > 0.1 * np.max(actual))


def check_gradient_descent_is_slow() -> bool:
    path = gradient_descent_path(GRADIENT_STEPS_SHOWN)
    values = [linear_objective(beta) for beta in path]
    decreasing = all(later <= earlier for earlier, later in zip(values, values[1:], strict=False))
    return decreasing and values[-1] > 100 * linear_objective(least_squares_solution())


def check_nonlinear_converges_monotonically() -> bool:
    iterates = nonlinear_iterates(NONLINEAR_ITERATIONS_SHOWN)
    values = [cooling_objective(p) for p in iterates]
    decreasing = all(later < earlier for earlier, later in zip(values, values[1:], strict=False))
    last_step = np.linalg.norm(iterates[-1] - iterates[-2])
    return decreasing and last_step < SETTLED_STEP


def check_nonlinear_needs_more_than_one_step() -> bool:
    iterates = nonlinear_iterates(NONLINEAR_ITERATIONS_SHOWN)
    return bool(np.linalg.norm(iterates[1] - iterates[-1]) > 1.0)


def check_condition_numbers_shown() -> bool:
    """Shown on screen: kappa(X^T X) is about 503, and exactly 21 after centring the times."""
    shown_raw, shown_centred = 503, 21
    return (abs(condition_number(normal_matrix()) - shown_raw) < 0.5
            and abs(condition_number(centred_normal_matrix()) - shown_centred) < 1e-9)


def check_first_guess_above_data_for_early_times() -> bool:
    """Shown on screen: the first-guess residuals are negative exactly for t <= 6."""
    negative = linear_residual(LINEAR_START) < 0
    return bool(np.array_equal(negative, DEPOSITION_MINUTES <= 6))


def check_hessian_positive_definite() -> bool:
    return bool(np.all(np.linalg.eigvalsh(normal_matrix()) > 0))


def check_iterates_inside_windows() -> bool:
    def inside(point: np.ndarray, window: ParameterWindow) -> bool:
        return window.first[0] <= point[0] <= window.first[1] and window.second[0] <= point[1] <= window.second[1]
    linear_points = [*gradient_descent_path(GRADIENT_STEPS_SHOWN), least_squares_solution()]
    return all(inside(p, LINEAR_WINDOW) for p in linear_points) and all(
        inside(p, NONLINEAR_WINDOW) for p in nonlinear_iterates(NONLINEAR_ITERATIONS_SHOWN))


CHECKS = {
    "one Gauss-Newton step from the start lands on the least-squares solution": check_one_step_reaches_least_squares,
    "the next Gauss-Newton step is zero": check_second_step_is_zero,
    "X^T r = 0 at the solution": check_residual_orthogonal_to_columns,
    "linear model: Gauss-Newton model equals S along the step": check_linear_model_is_exact,
    "nonlinear model: Gauss-Newton model differs from S along the step": check_nonlinear_model_is_not_exact,
    "gradient descent decreases S but is far from the minimum after 50 steps": check_gradient_descent_is_slow,
    "nonlinear Gauss-Newton decreases S every step and settles in 4 steps": check_nonlinear_converges_monotonically,
    "nonlinear Gauss-Newton needs more than one step": check_nonlinear_needs_more_than_one_step,
    "every plotted iterate lies inside the plotted window": check_iterates_inside_windows,
    "kappa(X^T X) is about 503, and 21 with centred times": check_condition_numbers_shown,
    "first-guess residuals are negative exactly for t <= 6": check_first_guess_above_data_for_early_times,
    "the Hessian X^T X is positive definite": check_hessian_positive_definite,
}


def main() -> int:
    failed = [claim for claim, check in CHECKS.items() if not check()]
    for claim in CHECKS:
        print(f"{'FAIL' if claim in failed else 'ok  '}  {claim}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
