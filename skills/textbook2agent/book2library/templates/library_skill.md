---
name: $name
description: $description
---

# Textbook library

Books in this library:

$book_list

Each book is split into units (front matter, chapters, appendices, solutions, back matter). Every unit is a
self-contained paper2skill reading package under `units/<book>/<unit>/`; its text is `references/paper.md`
and its figures and formula images are under `assets/`.

## Find material

1. Open [the catalog](references/catalog.md) to choose a book and unit: it lists PDF and printed page ranges,
   sections with pages, each unit's tier, the link to its text, and possible gaps in the statement index.
2. Look up numbered statements across all books in [statements.csv](references/statements.csv) (columns: book,
   unit, section, kind, number, printed_page, pdf_page, tier, text), for example
   `rg -i ',definition,2\.7,' references/statements.csv` or `rg -i 'outer measure' references/statements.csv`.
   Exercises printed as bare numbers are indexed only under a heading such as "Exercises"; the same number can
   also be a section, Definition or Example, so check the `kind` and `section` columns.
3. Search inside a unit with bounded output, then read 30–60 lines around the hit:
   `rg -n -i -m 8 --max-columns 240 'outer measure' units/<book>/<unit>/references/paper.md`.
   Read the whole statement, its proof and nearby definitions before using it.
4. When the index has no row for a statement (see the catalog's gaps), find its page with the `locate` command
   below (3–5 words from a single printed line work best), then read the page image.

## Trust and citation

- **reviewed** units were checked page by page and strictly verified. **draft** units are automatic extractions:
  displayed formulas are images, inline mathematics can be garbled, and margin notes can interrupt sentences.
  Before quoting a definition, theorem or formula from a draft unit, render the page and read it from the image,
  using the textbook2agent skill's `book2library/scripts/textbook_library.py`:
  `render --root <study-root> --book <book> --label <printed page>` (or `--page <PDF page>`), and
  `locate --root <study-root> --book <book> [--unit <unit>] '<phrase>'` to find pages.
- Page numbers inside a unit's `paper.md` and its asset names ("PDF page 48", `formula-p0048-…`) count pages
  **within the unit**: book PDF page = the unit's first PDF page + n − 1. Cite book pages only, as
  `[book] Definition 2.7, p. <printed> (PDF <n>)`.
- Units of kind `solutions` contain worked answers: open them only after the learner has attempted the exercise.
- Book text is the learner's own copy for private study. Do not publish or redistribute it.
