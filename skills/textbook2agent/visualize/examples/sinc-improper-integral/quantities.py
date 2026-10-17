# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy==2.5.3", "scipy==1.18.1"]
# ///
"""Every number and curve in the sin(x)/x animation, and a check of every claim the animation makes.

f(x) = sin(x)/x for x != 0 and f(0) = 1. On the hump [k*pi, (k+1)*pi] the sine keeps one sign, so f does too.
  A_k            = integral of |f| over hump k                 (hump_area)
  F(T)           = integral of f over [0, T] = Si(T)           (running_integral)
  G(n)           = integral of |f| over [0, n*pi] = sum A_k    (absolute_integral_to)
Run this file to check the claims: `uv run quantities.py` (exit code 1 if any claim fails).
"""

from __future__ import annotations

import math

import numpy as np
from scipy.integrate import quad
from scipy.special import sici

HUMPS_SHOWN = 12                  # humps drawn in the animation: k = 0, ..., 11
HUMPS_CHECKED = 100_000           # claims about every hump are checked this far
DECADES_SHOWN = 6                 # the growth plot runs to n = 10**6 humps
LIMIT = math.pi / 2               # value of the improper integral (shown, but not needed for existence)
GRID_POINTS_PER_HUMP = 64
QUADRATURE_HUMPS = 8              # humps cross-checked against direct numerical integration
ABSOLUTE_TOLERANCE = 1e-12
GROWTH_PER_DECADE = 2 / math.pi * math.log(10)   # about 1.466
GROWTH_TOLERANCE = 0.02


def f(x: np.ndarray | float) -> np.ndarray | float:
    """sin(x)/x with the value 1 at 0 (numpy's sinc is sin(pi t)/(pi t))."""
    return np.sinc(np.asarray(x) / math.pi)


def running_integral(t: np.ndarray | float) -> np.ndarray | float:
    """F(T): the integral of f over [0, T], i.e. the sine integral Si(T)."""
    return sici(t)[0]


def hump_edges(count: int) -> np.ndarray:
    return np.arange(count + 1) * math.pi


def signed_hump_areas(count: int) -> np.ndarray:
    """a_k = integral of f over [k pi, (k+1) pi] for k = 0, ..., count - 1."""
    return np.diff(running_integral(hump_edges(count)))


def hump_areas(count: int) -> np.ndarray:
    """A_k = |a_k| = integral of |f| over hump k (f has one sign on each hump)."""
    return np.abs(signed_hump_areas(count))


def hump_lower_bounds(count: int) -> np.ndarray:
    """2 / ((k+1) pi): from 1/x >= 1/((k+1) pi) on hump k and the integral of |sin| over a hump being 2."""
    return 2.0 / ((np.arange(count) + 1) * math.pi)


def hump_upper_bounds(count: int) -> np.ndarray:
    """2 / (k pi) for k >= 1 (from 1/x <= 1/(k pi)); hump 0 is bounded by pi because |f| <= 1."""
    k = np.arange(count, dtype=float)
    bounds = np.full(count, math.pi)
    bounds[1:] = 2.0 / (k[1:] * math.pi)
    return bounds


def absolute_integral_to(n: np.ndarray) -> np.ndarray:
    """G(n) = integral of |f| over [0, n pi], for an array of positive integers n."""
    cumulative = np.concatenate([[0.0], np.cumsum(hump_areas(int(np.max(n))))])
    return cumulative[np.asarray(n)]


def harmonic_bound_to(n: np.ndarray) -> np.ndarray:
    """(2/pi)(1 + 1/2 + ... + 1/n), the sum of the hump lower bounds."""
    cumulative = np.concatenate([[0.0], np.cumsum(hump_lower_bounds(int(np.max(n))))])
    return cumulative[np.asarray(n)]


def growth_grid() -> np.ndarray:
    """Integers n from 1 to 10**DECADES_SHOWN, spaced evenly in log10(n), for the growth plot."""
    return np.unique(np.round(np.logspace(0, DECADES_SHOWN, 400)).astype(int))


# Checks: one function per claim made on screen ---------------------------------------------------------------

def check_signs_alternate() -> bool:
    k = np.arange(HUMPS_CHECKED)
    return bool(np.all(np.sign(signed_hump_areas(HUMPS_CHECKED)) == (-1.0) ** k))


def check_lower_bounds() -> bool:
    return bool(np.all(hump_areas(HUMPS_CHECKED) >= hump_lower_bounds(HUMPS_CHECKED)))


def check_upper_bounds() -> bool:
    return bool(np.all(hump_areas(HUMPS_CHECKED) <= hump_upper_bounds(HUMPS_CHECKED)))


def check_areas_decrease() -> bool:
    return bool(np.all(np.diff(hump_areas(HUMPS_CHECKED)) < 0))


def check_growth_exceeds_harmonic_bound() -> bool:
    n = growth_grid()
    return bool(np.all(absolute_integral_to(n) >= harmonic_bound_to(n)))


def check_running_integral_between_partial_sums() -> bool:
    """On hump n, F is monotone, so F(T) lies between F(n pi) and F((n+1) pi)."""
    for n in range(HUMPS_SHOWN):
        t = np.linspace(n * math.pi, (n + 1) * math.pi, GRID_POINTS_PER_HUMP)
        low, high = sorted(running_integral(np.array([n * math.pi, (n + 1) * math.pi])))
        values = running_integral(t)
        if np.any(values < low - ABSOLUTE_TOLERANCE) or np.any(values > high + ABSOLUTE_TOLERANCE):
            return False
    return True


def check_tail_within_next_hump() -> bool:
    """Alternating-series remainder: |pi/2 - F(n pi)| <= A_n."""
    n = np.arange(1, HUMPS_CHECKED)
    return bool(np.all(np.abs(LIMIT - running_integral(n * math.pi)) <= hump_areas(HUMPS_CHECKED)[1:]))


def check_growth_per_decade() -> bool:
    """Shown on screen: each tenfold increase in n adds about (2/pi) ln 10 = 1.47 to G(n)."""
    n = 10 ** np.arange(1, DECADES_SHOWN + 1)
    increments = absolute_integral_to(n) - absolute_integral_to(n // 10)
    return bool(np.all(np.abs(increments - GROWTH_PER_DECADE) < GROWTH_TOLERANCE))


def check_sine_integral_against_quadrature() -> bool:
    direct = [quad(lambda x: abs(f(x)), k * math.pi, (k + 1) * math.pi)[0] for k in range(QUADRATURE_HUMPS)]
    return bool(np.allclose(direct, hump_areas(QUADRATURE_HUMPS), rtol=0, atol=1e-10))


CHECKS = {
    "f has sign (-1)^k on hump k": check_signs_alternate,
    "A_k >= 2/((k+1) pi)": check_lower_bounds,
    "A_k <= 2/(k pi) for k >= 1, A_0 <= pi": check_upper_bounds,
    "A_k strictly decreasing": check_areas_decrease,
    "G(n) >= (2/pi) H_n on the plotted grid": check_growth_exceeds_harmonic_bound,
    "F(T) between consecutive partial sums": check_running_integral_between_partial_sums,
    "|pi/2 - F(n pi)| <= A_n": check_tail_within_next_hump,
    "G(10n) - G(n) is about (2/pi) ln 10 for n >= 1": check_growth_per_decade,
    "Si-based areas agree with direct quadrature": check_sine_integral_against_quadrature,
}


def main() -> int:
    failed = [claim for claim, check in CHECKS.items() if not check()]
    for claim in CHECKS:
        print(f"{'FAIL' if claim in failed else 'ok  '}  {claim}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
