---
name: visualize
description: Animate a math concept with Manim - a storyboard tied to proof steps, numbers checked in code, a rendered video with frames for review, and independent verification.
---

# Visualize

Turn a definition, a proof idea or an algorithm into a short animation (1–4 minutes) the learner can watch, pause
and replay. Use it when the mechanism is easier to see than to read: convergence and divergence, areas and
integrals, the geometry of linear algebra, iterative algorithms, distributions. A picture shows finitely many
cases, so it illustrates a proof and never replaces one.

Two worked examples show every convention below:
[sin(x)/x and L¹](examples/sinc-improper-integral/) (analysis) and
[Gauss–Newton for linear regression](examples/gauss-newton-linear-regression/) (optimization). Each has
`storyboard.md`, `quantities.py` and `scene.py`.

## Requirements

Manim Community 0.21 (installed by `uv run`), a LaTeX distribution with `dvisvgm` (TeX Live or MiKTeX), and on
Linux the Pango and Cairo development headers. No separate ffmpeg is needed. Details and per-OS install steps are
in [the Manim guide](references/manim-guide.md).

## Workspace

Each animation gets its own folder in the study workspace:

```text
visuals/<slug>/
├── storyboard.md   beats, captions and the claim behind each one (template: templates/storyboard.md)
├── quantities.py   every number and curve the scene shows, plus a check for every claim
├── scene.py        the Manim scene (a StudyScene from scripts/scene_kit.py)
└── render/<quality>/   video, one video per beat, frame sheets, manifest.json
```

## Steps

1. **Ground the concept.** State it exactly as the learner's book does and take any statement you quote from the
   statement bank (tutor rules). Use the book's notation.
2. **Storyboard.** Fill [the template](templates/storyboard.md). One beat carries one idea and becomes one Manim
   section. Order the beats from foundations upward, include one worked numerical beat, and write every claim
   the screen makes next to what justifies it. If the animation belongs to an exercise, give each beat a hint
   level.
3. **Compute and check.** Write `quantities.py`: pure functions for every value and curve, and one check per
   claim, evaluated well beyond what is drawn (for example every hump up to 10⁵, not only the 12 shown). Cross-check
   at least one quantity by an independent route. Give the file a `# /// script` dependency header (see the
   examples) and run it with `uv run quantities.py`; all checks must pass. The scene never types a number by hand.
4. **Write the scene.** Subclass `StudyScene`; open each beat with `self.beat(name, title)` (or
   `self.continue_beat(name)` to keep the stage), and explain with `self.say(caption)`. Follow the
   [Manim guide](references/manim-guide.md) for layout, plotting and LaTeX.
5. **Preview and look.** Render at preview quality, then open every frame sheet and fix overlaps, text off screen,
   labels touching curves, captions that wrap badly and numbers that disagree with `quantities.py`:

   ```bash
   uv run <this-skill>/visualize/scripts/render_scene.py visuals/<slug>/scene.py <SceneClass> --quality preview
   ```

6. **Verify independently.** A fresh agent that did not write the scene gets the storyboard, `quantities.py`, the
   scene's text and the frame sheets, and checks: each on-screen claim (as in the tutor's
   [verification](../tutor/references/verification.md)), each number recomputed by its own code, and whether any
   picture misleads — truncated or unlabelled axes, a log scale passed off as linear, slow growth that looks
   bounded, sampling artefacts, colour without a legend, finitely many cases presented as proof. Repair and
   re-render until it accepts.
7. **Render and deliver.** Render with `--quality final` (1080p) and give the learner the video and the contact
   sheet. For an exercise, release only the section videos (`render/final/sections/`) at or below the learner's
   current hint level. Record the animation in the session note and link it from the lesson.

## Rules

- Numbers come from code; notation comes from the book; outside facts are labelled as such on screen.
- Captions are at most two lines; put a line break (`\\`) where a caption is long. Hold each caption long enough
  to read (`say` holds 1.5 s by default; use 2.5 s for two lines).
- Colours follow `Palette` (colour-blind safe) and never carry meaning alone: a caption or legend names them.
- Label simulated data and illustrative choices (a start point, a step size) as such.
- Do not put book page images or long verbatim book text in a video; videos are easy to share.
- Split anything longer than about 4 minutes into separate scenes.
