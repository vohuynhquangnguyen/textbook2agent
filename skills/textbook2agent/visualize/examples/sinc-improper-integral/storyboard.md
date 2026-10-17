# Storyboard — sin(x)/x is not in L¹(ℝ), yet its improper integral converges

- **Concept**: for $f(x)=\sin x/x$ ($x\ne0$), $f(0)=1$: $f\notin L^1(\mathbb R)$, but $\lim_{T\to\infty}\int_{[0,T]}f\,dm$
  exists.
- **Learner goal**: see why absolute areas diverge like the harmonic series while signed areas converge, and
  that $L^1$ is about $|f|$.
- **Source of numbers**: `quantities.py`.
- **Linked exercise**: works as a hint sequence. Beats 1–3 orientation, beats 4–5 key step for "not in $L^1$",
  beats 6–7 key step for the limit, beat 8 summary.
- **Length**: about 2.5 minutes.

## Beats

### 1. `the-function` — Is sin x / x integrable?
- **On screen**: definition by cases; graph of $f$ on $[0,12\pi]$.
- **Claims**: $f$ is continuous on $\mathbb R$, hence measurable; $f$ is even, so
  $\int_{\mathbb R}|f|\,dm=2\int_{[0,\infty)}|f|\,dm$ — elementary.

### 2. `two-questions` — Two different questions
- **Claims**: $f\in L^1(\mathbb R)\iff\int|f|\,dm<\infty$ (definition); on $[0,T]$, $f$ is bounded and continuous,
  so the Lebesgue integral equals the Riemann integral.

### 3. `humps` — Cut [0, ∞) into humps
- **On screen**: signed areas on $[k\pi,(k+1)\pi]$, blue positive, orange negative; first three signed areas.
- **Claims**: $f$ has sign $(-1)^k$ on hump $k$ — `check_signs_alternate`.
- **Numbers**: `signed_hump_areas(3)`.

### 4. `lower-bound` — How big is hump k?
- **On screen**: hump $k=2$ with $|f|$ above $|\sin x|/(3\pi)$; the chain of inequalities.
- **Claims**: $|f(x)|\ge|\sin x|/((k+1)\pi)$ on hump $k$ (written with $|f|$ so that $x=0$ is covered), hence
  $A_k\ge 2/((k+1)\pi)$ — proof on screen; `check_lower_bounds`.
- **Numbers**: $A_2$, $2/(3\pi)$.

### 5. `divergence` — Adding up the humps of |f|
- **On screen**: bars $A_k$ next to $2/((k+1)\pi)$ for $k<12$; then $\int_{[0,n\pi]}|f|$ and $\frac2\pi H_n$ against
  $\log_{10} n$ up to $10^6$.
- **Claims**: $\sum_{k<n}A_k\ge\frac2\pi\sum_{k\le n}\frac1k\to\infty$; growth about $\frac2\pi\ln10$ per decade
  (numerical observation) — `check_growth_exceeds_harmonic_bound`, `check_growth_per_decade`; the Monotone
  Convergence Theorem gives $\int_{[0,\infty)}|f|=\lim_n\int_{[0,n\pi]}|f|$.

### 6. `alternating-series` — Now let the signs cancel
- **Claims**: $A_{k+1}=\int_{k\pi}^{(k+1)\pi}\frac{|\sin y|}{y+\pi}dy<\int_{k\pi}^{(k+1)\pi}|f(y)|dy=A_k$ (substitution
  $x=y+\pi$) — `check_areas_decrease`; F(nπ) dots in one neutral colour; $A_k\le 2/(k\pi)$ for $k\ge1$ —
  `check_upper_bounds`; alternating series test gives convergence of $F(n\pi)$.
- **Numbers**: $F(n\pi)$ for $n\le12$.

### 7. `between-multiples` — What about T between multiples of π?
- **Claims**: $F$ is monotone on each hump, so $F(T)$ lies between $F(n\pi)$ and $F((n+1)\pi)$ —
  `check_running_integral_between_partial_sums`; squeeze shown on screen:
  $|F(T)-L|\le\max(|F(n\pi)-L|,|F((n+1)\pi)-L|)$ with $n=\lfloor T/\pi\rfloor\to\infty$, hence $F(T)\to L$.
- **Outside fact, labelled**: "In fact $L=\pi/2$ exactly (Dirichlet's integral, proved by other means)", not needed
  for existence — `check_tail_within_next_hump`.

### 8. `summary`
- **Claims**: $\sum_{k=0}^\infty A_k\ge\frac2\pi\sum_{k=0}^\infty\frac1{k+1}=\infty$ (indices explicit, matching beat 5);
  signed side lists both ingredients: alternating series with $A_k\downarrow0$, and $F$ monotone on each hump.

## Honesty notes

- Only 12 humps are drawn; the divergence argument is the harmonic bound, not the picture. The log-scale growth
  plot is labelled "log scale" so slow growth is not mistaken for convergence.
- The value $\pi/2$ is stated as a known result and marked as unnecessary for the proof.
