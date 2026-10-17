# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `visualize` component: Manim animations for concepts, proof ideas and algorithms. A storyboard template, a
  shared scene kit (colour-blind-safe palette, beats as sections, captions that break only where the author
  writes `\\`), a render script that saves one video
  and one frame sheet per beat, a Manim guide with per-platform install steps, and verification rules for
  on-screen claims and misleading visuals.
- Two worked animations with checked numbers: sin(x)/x is not in L¹ but its improper integral converges, and
  Gauss–Newton for linear regression.
- The tutor, book2lab, learner profile and router now point to visualize.

## [0.1.0] - 2026-10-14

### Added

- `textbook2agent` skill with four components: book2library, syllabus, tutor and book2lab.
- book2library command line (`textbook_library.py`): add books, propose chapter units from the PDF outline,
  draft-build every unit, review and strictly verify selected units, clear the verification warnings that LaTeX
  transcription of displayed formulas causes by itself, and generate the catalog and a cross-book statement
  index with printed page numbers (including section-prefixed exercise numbers such as `2A.4`).
- Paper2Agent's paper2skill engine (commit `8c2d059`), included unchanged.
- Templates for the learner profile, concept map, syllabus, statement bank, session notes, progress and the
  verifier brief.
- CI on Ubuntu and Windows, and a release workflow that publishes the skill as a ZIP.

[Unreleased]: https://github.com/vohuynhquangnguyen/textbook2agent/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/vohuynhquangnguyen/textbook2agent/releases/tag/v0.1.0
