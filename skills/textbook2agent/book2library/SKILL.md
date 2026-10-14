---
name: book2library
description: Turn textbook PDFs into one searchable, chapter-level study library with printed-page citations, a cross-book statement index, and page-by-page review for the chapters being studied.
---

# Book2Library

Each book is split into **units** (front matter, chapters, appendices, solutions, back matter). Each unit goes
through the vendored paper2skill engine (`scripts/paper2skill/`, unchanged from Paper2Agent) and becomes a
reading package under `library/units/<book>/<unit>/`. The library adds a catalog and a cross-book index of the
numbered Definitions, Theorems, Examples and Exercises the extraction finds, with a list of likely gaps.

Review is proportional. A textbook can run to hundreds of pages, so every unit gets a fast **draft** build, and
only units on the study path get the full **reviewed** treatment. This replaces paper2skill's rule that every page
is reviewed before delivery.

| Tier | Meaning | How a unit gets there |
| --- | --- | --- |
| planned | In the plan, not extracted | `add` |
| draft | Automatic extraction; searchable; formulas are images | `ingest` |
| reviewed | Page-by-page reviewed, formulas transcribed, strictly verified | review, then `finalize` |

## Commands

Run the script with `uv run`, which installs its pinned dependencies. Without uv, install
`pymupdf==1.28.2 pymupdf4llm==1.28.2 pypdf==6.18.1 pillow==12.2.0` and use `python`. Every command takes
`--root <study-root>` and prints one JSON object; exit code 2 means issues remain or review is pending.

```bash
LIB="<this-skill>/book2library/scripts/textbook_library.py"
uv run "$LIB" add '/path/Axler MIRA.pdf' --id axler-mira --root "$ROOT"   # snapshot the PDF, propose units
uv run "$LIB" check --root "$ROOT"                                        # validate the plan and freshness
uv run "$LIB" ingest --root "$ROOT"                                       # draft-build every unit (resumable)
uv run "$LIB" ingest --root "$ROOT" --book axler-mira --unit ch02         # or selected units
uv run "$LIB" status --root "$ROOT"                                       # tier, freshness, paths of units
uv run "$LIB" locate --root "$ROOT" --book axler-mira 'outer measure'     # phrase -> printed and PDF pages
uv run "$LIB" locate --root "$ROOT" --book axler-mira --unit ch02 'is a σ-algebra'   # within one unit
uv run "$LIB" render --root "$ROOT" --book axler-mira --label 37          # page image for visual checks
uv run "$LIB" review-aid --root "$ROOT" --book axler-mira --unit ch02     # contact sheets and review queue
uv run "$LIB" finalize --root "$ROOT" --book axler-mira --unit ch02       # reviewed build + strict verify
uv run "$LIB" adjudicate --root "$ROOT" --book axler-mira --unit ch02     # clear warnings LaTeX itself causes
uv run "$LIB" catalog --root "$ROOT"                                      # regenerate navigation files
```

Draft extraction takes roughly 30 seconds per 50 pages; a 400-page book takes about four minutes and needs
about 0.7 MB of working space per page under `.work/`. Scanned books need Tesseract for `--ocr auto`. On Windows,
keep the workspace path short (for example `C:\study\analysis`): the engine's evidence paths are deep.

`locate` matches 3–5 words from a single printed line best; hyphenated line breaks are handled, but a margin
note interrupting the sentence is not. Use `--unit` to skip the contents pages.

## 1. Add books and fix the split

1. `add` each PDF with a short, stable `--id` (lowercase and hyphens, e.g. `axler-mira`). The PDF is copied to
   `.work/originals/`; units are proposed from the PDF outline.
2. Check the proposal in `library-plan.json` against the printed contents pages (`render --label` on them).
   Edit freely: unit `id`, `kind` (`front`, `chapter`, `appendix`, `solutions`, `back`), `title`, `first_page`
   and `last_page` (one-based PDF pages). Units must cover every page once, in order. Also fill `authors` and
   `edition` when the PDF metadata is wrong — check the copyright page or page footer, since printed page
   numbers differ between editions and drafts — and read every entry in `warnings`.
3. If a book numbers statements in an unusual way, add `statement_patterns` to that book: regular expressions
   with named groups `kind` and `number`, matched case-insensitively at the start of a paragraph. The defaults
   cover "Definition 2.7 …" and "2.7 Definition …".
4. Run `check` until it reports no issues.

A book without an outline becomes a single `whole` unit; split it by hand from the printed contents.

## 2. Draft the whole library

Run `ingest`. It writes each unit's PDF, runs paper2skill `prepare` and `extract`, builds a draft package at a
stable path, and regenerates the navigation files:

- `library/SKILL.md`: how an agent reads this library.
- `library/references/catalog.md`: books, units, PDF and printed page ranges, sections with pages, tiers.
- `library/references/statements.csv`: numbered statements from all books with their section, printed and PDF
  pages. Bare-numbered paragraphs ("2.12 Consider …") count as exercises only under an "Exercises" or
  "Problems" heading. The catalog lists numbers missing from otherwise complete sequences.

`ingest` is resumable and never overwrites review work. When unit pages change in the plan, `check` reports
every affected unit. The next `ingest` moves their old review directories and packages to `.work/replaced/` and
rebuilds them as drafts, together with the units you name; a reviewed unit whose pages changed must be reviewed
again. Units removed from the plan are moved aside the same way.

Spot-check the draft: open one unit's `references/paper.md`, compare a page with its rendered image, and look at
the catalog's gap list. Adjust `statement_patterns` when whole kinds of statements are missing.

## 3. Review the units being studied

Review a unit before or while it is studied — the next one or two syllabus modules, not the whole library.
The tutor's statement bank already guarantees that quoted statements were read from page images; a reviewed
unit additionally makes the unit's full text trustworthy for search and reading.

1. `review-aid`, then follow paper2skill's [review-plan.md](references/paper2skill/review-plan.md) and
   [bundle-review.md](references/paper2skill/bundle-review.md) inside the unit's review directory
   (`status` prints it). Edit only `plan.json`, `pages/*.json`, `adjudications.json` and `bundle.json`.
2. Apply these textbook rules on top of paper2skill's:
   - **Displayed formulas**: when every symbol is certain, change the item's `kind` from `formula` to `text`
     and write the LaTeX as `$$ … \tag{2.11}$$` in `markdown`, keeping the printed equation number as a tag.
     Recompute any worked numbers (a matrix product, a determinant) while transcribing. Keep the image when
     a symbol is uncertain.
   - **Inline mathematics**: keep the extracted text and fix only wrong characters (a garbled `m̸ = n` becomes
     `m ≠ n`). Do not rewrite inline mathematics as LaTeX: it breaks the line-by-line text verification for
     every line it touches. When an inline expression is unreadable, write it in LaTeX and expect to adjudicate
     that page by hand.
   - **Numbered statements**: start each Definition, Theorem, Lemma, Example and Exercise as its own item
     beginning with its label, so the statement index finds it. Make labels such as `**Example 2.3**` text, not
     headings, so headings stay the book's sections. Keep exercise numbering exactly as printed.
   - **Margin notes and running heads**: omit running heads, page numbers, footers and copyright lines with a
     reason. Omit margin keywords only as whole items, and only when the same term appears in the adjacent body;
     if keywords share an item with a caption, split the item (separate `bbox` values) rather than deleting words.
     Move margin notes and floating figures after the paragraph they belong to.
   - **Figures**: keep each figure with all its panels, and its caption as a separate item.
3. For long units, give parallel reviewers contiguous page ranges of 10–15 pages. The coordinator owns
   `plan.json` and `bundle.json` and merges proposed shared changes. Then a fresh verifier, distinct from the
   reviewers, compares the assembled unit with the page images, checking every transcribed formula symbol by
   symbol.
4. Mark each page and the source `reviewed: true` with specific `review_notes` (in `bundle.json` for the
   source), then run `finalize`.
5. Exit code 2 means strict verification found unresolved diagnostics. Transcribed formulas always cause some:
   their native text no longer matches line by line, and LaTeX writes `-` where the PDF has a Unicode minus.
   Run `adjudicate`. It clears a missing-line warning only when the line lies in a region the extractor marked as
   a formula and its letters, digits and comparison or operator symbols (= < > ≤ ≥ ≠ ∈ ∉ ⊂ ⊆ ∪ ∩ + − ± × ∞ ∀ ∃)
   appear in the same order in the page's LaTeX; and a number warning only when the minus sign is the sole
   difference. It cannot see subscript and superscript placement, fonts, dots, arrows or brackets: those rely
   on the symbol-by-symbol check in steps 2 and 3. It lists everything else; inspect those against the page
   images, fix them or adjudicate them by hand as paper2skill describes, and run `finalize` again. A unit with
   transcribed formulas ends as `reviewed_with_limitations`, which counts as reviewed.

## Completion

Report the books and their unit counts, the tier of each unit, the statement count, and any warnings or
limitations (scanned pages, image-only content, units split by hand). The library is the learner's private copy
of their books: do not publish it.

## Maintenance

```bash
uv run scripts/test_textbook_library.py      # outline planning and the full pipeline on a synthetic book
uv run scripts/paper2skill/test_paper_bundle.py
```
