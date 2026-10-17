# Storyboard — Gauss–Newton for linear regression

- **Concept**: the Gauss–Newton iteration $J^\top J\,\Delta=-J^\top r(\beta)$, $\beta\leftarrow\beta+\Delta$, applied to a
  straight-line least-squares fit, and why it converges in one step.
- **Learner goal**: derive the step from linearizing the residual; see in parameter space that one step reaches
  the minimizer for a linear model; contrast with gradient descent and with a nonlinear model.
- **Source of numbers**: `quantities.py` (simulated data, fixed values).
- **Linked exercise**: none.
- **Length**: about 3 minutes.

## Beats

### 1. `problem` — Fitting a line by least squares
- **On screen**: 8 simulated wafers (deposition time, oxide thickness); first guess $\beta^{(0)}=(60,4)$ with residuals.
- **Claims**: definitions of $r_i$ and $S$.

### 2. `residual-vector` — Stack the residuals into a vector
- **Claims**: $r(\beta)=y-X\beta$ is affine; $J=-X$ for every $\beta$ — `linear_jacobian`.

### 3. `gauss-newton-step` — The Gauss–Newton step
- **Claims**: $\Delta$ minimizes $\tfrac12\lVert r+J\Delta\rVert^2$ iff $J^\top J\Delta=-J^\top r$ (gradient of a convex
  quadratic), unique when $J$ has full column rank; for the line, $X^\top X\Delta=X^\top r$.

### 4. `worked-step` — One step, in numbers
- **Numbers**: $r^{(0)}$, $X^\top X$, $X^\top r^{(0)}$, $\Delta$, $\beta^{(1)}$ from `linear_residual`, `normal_matrix`,
  `linear_step`.
- **Claims**: the first-guess residuals are negative exactly for $t\le6$ — `check_first_guess_above_data_for_early_times`.

### 5. `one-step` — Watch the step
- **Claims**: contours of $S$ are ellipses ($S$ quadratic with positive-definite Hessian $X^\top X$ —
  `check_hessian_positive_definite`); "axes not to equal scale" shown; one step lands on the least-squares solution —
  `check_one_step_reaches_least_squares`; next step zero and $X^\top r(\hat\beta)=0$ — `check_second_step_is_zero`,
  `check_residual_orthogonal_to_columns`.

### 6. `why-one-step` — Why exactly one step?
- **Claims**: along the step the Gauss–Newton model equals $S$ — `check_linear_model_is_exact`; $\nabla^2S=J^\top J+
  \sum r_i\nabla^2 r_i=X^\top X$, positive definite because the $t_i$ are not all equal; Newton's method minimizes a
  strictly convex quadratic in one step.

### 7. `gradient-descent` — Compared with gradient descent
- **Claims**: gradient descent with step $1/\lambda_{\max}$ after 50 steps has $S\approx2341$ versus $16.3$ —
  `check_gradient_descent_is_slow`; $\kappa(X^\top X)\approx503$, exactly 21 after centring the times —
  `check_condition_numbers_shown`; "in exact arithmetic" qualifies "costs it nothing".

### 8. `nonlinear` — When the model is not linear
- **On screen**: simulated cooling data, $y\approx a e^{-bt}$; iterates in the $(a,b)$ plane.
- **Claims**: row $i$ of $J(a,b)$ is $[-e^{-bt_i},\ a t_i e^{-bt_i}]$, so $J$ depends on $(a,b)$; $S$ decreases each step and settles in 4 steps —
  `check_nonlinear_converges_monotonically`, `check_nonlinear_needs_more_than_one_step`. Damping
  (Levenberg–Marquardt) as the usual safeguard is general background, labelled as such by wording.

### 9. `summary`

## Honesty notes

- The data are simulated and labelled so; the gradient-descent comparison uses one fixed step size, stated on
  screen.
- Undamped Gauss–Newton converging on the nonlinear example is a property of this start and data, not a general
  guarantee; the caption says damping is the usual safeguard.
