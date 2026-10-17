# Third-party notices

Textbook2Agent includes material from the following project.

## Paper2Agent

- Source: https://github.com/jmiao24/Paper2Agent, commit `8c2d059165ef8cdcb70dbea76655b9c2b55b38e6`
- License: MIT, Copyright (c) 2025 Jiacheng Miao
- Included, unchanged:
  - `skills/textbook2agent/book2library/scripts/paper2skill/paper_bundle.py`
  - `skills/textbook2agent/book2library/scripts/paper2skill/pdf_to_skill.py`
  - `skills/textbook2agent/book2library/scripts/paper2skill/reading_package.py`
  - `skills/textbook2agent/book2library/scripts/paper2skill/test_paper_bundle.py`
  - `skills/textbook2agent/book2library/references/paper2skill/bundle-review.md`
  - `skills/textbook2agent/book2library/references/paper2skill/review-plan.md`
- The full license text is in `skills/textbook2agent/book2library/scripts/paper2skill/LICENSE`.

The design of Textbook2Agent (a library component adapted from paper2skill, a lab component adapted from paper2mcp,
independent verification by fresh agents) follows Paper2Agent. Please cite Paper2Agent as well when you cite this
project; see `CITATION.cff`.

## Runtime dependencies

Installed by `uv` from PyPI when the scripts run; not redistributed here:
PyMuPDF and pymupdf4llm (AGPL-3.0 or commercial license, Artifex), pypdf (BSD-3-Clause), Pillow (MIT-CMU);
for animations, Manim Community (MIT), PyAV (BSD-3-Clause), NumPy, SciPy and contourpy (BSD-3-Clause).
PyMuPDF's AGPL terms apply to anyone who distributes software that includes it, or offers a modified version of it
to users over a network (AGPL-3.0 section 13).
