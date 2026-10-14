# Contributing

Thank you for helping. Bug reports, fixes and new adaptations (for example a different textbook layout) are
welcome.

## Never share book content

Do not add textbook PDFs, extracted text, page images or study workspaces to the repository, an issue or a pull
request. Tests use synthetic PDFs built in the test itself. When reporting a problem with a real book, describe
the layout (for example "exercises are numbered `2.12` under an *Exercises* heading") instead of quoting it.

## Set up and check

You need Python 3.11+ and [uv](https://docs.astral.sh/uv/). From the repository root:

```bash
uv run tests/test_skill_package.py                                           # SKILL.md metadata and links
uv run skills/textbook2agent/book2library/scripts/test_textbook_library.py   # library scripts
uv run skills/textbook2agent/book2library/scripts/paper2skill/test_paper_bundle.py   # vendored engine
uvx ruff@0.16.10 check                                                       # lint
```

CI runs these checks for every push and pull request: lint, packaging and the engine's own tests on Ubuntu, and
the package and library tests on both Ubuntu and Windows (the library tests drive the engine end to end).

## Where things go

- Skill instructions are Markdown under `skills/textbook2agent/`. Keep each `SKILL.md` short and move detail into
  `references/` or `templates/`. Use relative links; the package test checks that they resolve.
- Library scripts live in `skills/textbook2agent/book2library/scripts/`. `textbook_library.py` is the command
  line; each other module has one job (outline planning, the plan file, PDF access, the engine runner, the
  catalog, the adjudicator).
- `scripts/paper2skill/` and `references/paper2skill/` are Paper2Agent files kept unchanged. Call the engine only
  through `bundle_runner.py`. To update them, copy the newer upstream files, record the commit in
  `scripts/paper2skill/README.md` and `THIRD_PARTY_NOTICES.md`, and run every test.

## Code conventions

- Code any teammate can read and extend: small functions that do one thing, descriptive names, named constants
  instead of magic numbers, no flag arguments, no commented-out code, comments for intent only.
- Expected failures raise `LibraryError` and reach the user as one clear message with exit code 1, not a traceback.
- Read and write text as UTF-8 explicitly; the scripts must work on Windows.
- Tests: one assertion per test, independent, repeatable, using only synthetic inputs.
- Anything that clears a verification warning must be provably mechanical. Add a regression test showing that a
  real content change is still reported.

## Pull requests

Describe the problem, the change and how you tested it. Update `CHANGELOG.md` under *Unreleased*.
