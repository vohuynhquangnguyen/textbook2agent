# Manim guide for study animations

Practical conventions for Manim Community 0.21 as used by `scripts/render_scene.py` and `scripts/scene_kit.py`.
The two examples in `../examples/` use every pattern below.

## Install

`render_scene.py` declares its Python dependencies (Manim, NumPy, SciPy, contourpy), so `uv run` installs them.
The system pieces differ by platform:

| Platform | LaTeX (with `dvisvgm`) | Graphics libraries |
| --- | --- | --- |
| Windows | MiKTeX (`winget install MiKTeX.MiKTeX`; allow installing missing packages on the fly) or TeX Live | none: Cairo and Pango come as prebuilt wheels |
| macOS | MacTeX or BasicTeX (`brew install --cask mactex-no-gui`) | `brew install cairo pkg-config` (pycairo builds from source) |
| Debian/Ubuntu | `sudo apt install texlive texlive-latex-extra dvisvgm` | `sudo apt install libcairo2-dev libpango1.0-dev pkg-config python3-dev` |

Check with `latex --version` and `dvisvgm --version`. Manim encodes video through PyAV, so no ffmpeg install is
needed. The first render in a new environment takes a minute while uv builds the environment.

## Render

```bash
uv run visualize/scripts/render_scene.py visuals/<slug>/scene.py <SceneClass> --quality preview   # 480p15, fast
uv run visualize/scripts/render_scene.py visuals/<slug>/scene.py <SceneClass> --quality final     # 1080p60
```

`draft` is 720p30 and `4k` is 2160p60. A 3-minute scene takes about 1.5 minutes at preview quality and roughly ten
times that at final quality. The script puts `scene_kit` and the scene's own folder on the Python path, so the
scene can `import quantities`. Never name a module after a standard-library module (`numbers.py`, `math.py`):
NumPy would import it by mistake.

Outputs go to `render/<quality>/`: the full video, `sections/NN-<beat>.mp4`, `frames/NN-<beat>.png` (last frame),
`frames/NN-<beat>-sheet.png` (a frame every 2 s) and `contact-sheet.png`. Review the sheets, not just the last
frames: overlaps often happen mid-beat.

## Scene skeleton

```python
from manim import DOWN, Axes, Create, MathTex, Write
import quantities as q
from scene_kit import Palette, StudyScene

class MyConcept(StudyScene):
    def construct(self) -> None:
        self.definition()
        self.key_idea()

    def definition(self) -> None:
        self.beat("definition", "What is being asked")        # new section, empty stage, title card
        formula = MathTex(r"A_k=\int_{[k\pi,(k+1)\pi]}|f|\,dm", font_size=36)
        self.play(Write(formula))
        self.say(r"Each hump of $|f|$ has area $A_k$.")         # caption at the bottom, replaces the last one

    def key_idea(self) -> None:
        self.continue_beat("key-idea")                         # new section, keeps what is on screen
        ...
```

One method per beat keeps `construct` readable and matches the storyboard. Pass beat names in kebab case; they
name the section videos.

## Layout

- The frame is about 14.2 × 8 units with the origin at the centre. Keep the bottom 1.3 units for captions:
  place plots with `.to_edge(DOWN, buff=1.4)` or higher.
- Two panels side by side: about 4.6–6.6 units wide each, `.to_edge(LEFT, buff=0.5)` and
  `.to_edge(RIGHT, buff=0.5)`. Check the gap between the left panel's last tick label and the right panel.
- Formulas: 30–36 pt; labels 24–30 pt; title cards 46 pt (scene_kit). Arrange stacks with
  `VGroup(...).arrange(DOWN, aligned_edge=LEFT, buff=0.4)`.
- Captions break only at an explicit `\\`: `say()` never lets LaTeX wrap a line, and a line wider than the frame
  is scaled down instead. Break long captions by hand at a natural pause.

## Plots

- `Axes(x_range=[a, b, step], y_range=[c, d, step], x_length=..., y_length=..., tips=False,
  axis_config={"color": Palette.MUTED})`. Add `"include_numbers": True, "font_size": 24` for numeric ticks, or
  custom labels: `axes.get_x_axis().add_labels({2*PI: MathTex(r"2\pi")}, buff=0.6)`. Raise `buff` when the curve
  dips below the axis, so labels never touch it.
- Axes cross at the coordinate origin when it is inside both ranges; choose ranges so the crossing does not hide
  the point of interest.
- `axes.plot(f, x_range=[a, b, step])`: for oscillating functions use a step of 0.01 or finer and define removable
  singularities explicitly (`np.sinc(x / np.pi)` for sin x / x).
- Data you already computed: `axes.plot_line_graph(xs, ys, add_vertex_dots=False)["line_graph"]`.
- Shaded areas: `axes.get_area(graph, x_range=(a, b), color=..., opacity=0.55)`; bars: a `Polygon` through four
  `axes.c2p` corners.
- Log scales: plot `log10(n)` on a linear axis, label ticks `10^d`, and say "log scale" on screen.
- Contours of a function of two parameters: compute polylines with `contourpy` in `quantities.py`, then draw each
  with `VMobject().set_points_as_corners([axes.c2p(*p) for p in line])`.

## Motion

- Move along a path: `t = ValueTracker(0)`, objects built with `always_redraw(lambda: ...)` from `t.get_value()`,
  then `self.play(t.animate.set_value(1), run_time=3)`.
- Replace a curve with a new one: `self.play(curve.animate.become(new_curve))`.
- Several objects in sequence: `LaggedStart(*[FadeIn(m) for m in group], lag_ratio=0.15)`.
- Keep each motion 1–3 s; follow a claim with a held caption rather than more motion.

## LaTeX

- Use raw strings: `MathTex(r"\frac{2}{(k+1)\pi}")`. In f-strings double the braces: `rf"\frac{{2}}{{{n}\pi}}"`.
- The default template loads amsmath and amssymb (`\mathbb`, `\begin{cases}`, `\begin{bmatrix}`, `\xrightarrow`).
- `Tex` is text mode with inline `$...$`; `MathTex` is display math. Format numbers in Python
  (`f"{value:.3f}"`) with the precision `quantities.py` justifies.

## Troubleshooting

- "LaTeX error converting to dvi" or "dvisvgm not found": install the missing LaTeX package or `dvisvgm`; on
  MiKTeX, open the console once and allow package installation.
- `pangocairo >= 1.30.0 is required` while installing: the Pango headers are missing (Linux) — see Install.
- Nothing renders but no error: the class name passed to `render_scene.py` must match the scene class.
- To iterate on one beat, temporarily call only that beat's method from `construct`.
