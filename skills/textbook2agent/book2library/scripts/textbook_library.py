#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pymupdf==1.28.2", "pymupdf4llm==1.28.2", "pypdf==6.18.1", "pillow==12.2.0"]
# ///
"""Turn a list of textbook PDFs into one searchable, chapter-level study library.

Typical flow: add -> (edit library-plan.json) -> check -> ingest;
then, for units on the study path: review-aid -> (agent review) -> finalize [-> adjudicate -> finalize].
Every command prints one JSON object. Exit codes: 0 success, 1 error, 2 issues or pending review.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from bundle_runner import REVIEWED_STATUSES, BundleError
from library_builder import Library
from library_errors import LibraryError

EXIT_OK, EXIT_ERROR, EXIT_PENDING = 0, 1, 2
DEFAULT_RENDER_DPI = 200
MIN_RENDER_DPI, MAX_RENDER_DPI = 36, 600
DEFAULT_LOCATE_LIMIT = 10


def add(args) -> tuple[dict, int]:
    if args.id and len(args.pdf) > 1:
        raise LibraryError("--id applies to a single PDF; add books one at a time to name them")
    library = Library(args.root)
    books = [library.add_book(Path(pdf), args.id) for pdf in args.pdf]
    summary = [{"id": b.id, "title": b.title, "pages": b.page_count, "units": [u.id for u in b.units],
                "warnings": b.warnings} for b in books]
    next_step = "Check each proposed split against the printed contents, edit library-plan.json, then run check."
    return {"added": summary, "plan": library.relative(library.layout.plan_file), "next": next_step}, EXIT_OK


def check(args) -> tuple[dict, int]:
    issues = Library.open(args.root).issues()
    if issues:
        return {"status": "issues", "issues": issues}, EXIT_PENDING
    return {"status": "ok", "issues": []}, EXIT_OK


def ingest(args) -> tuple[dict, int]:
    return Library.open(args.root).ingest(args.book, args.unit, args.ocr), EXIT_OK


def review_aid(args) -> tuple[dict, int]:
    return Library.open(args.root).review_aid(args.book, args.unit), EXIT_OK


def finalize(args) -> tuple[dict, int]:
    result = Library.open(args.root).finalize(args.book, args.unit)
    return result, EXIT_OK if result["status"] in REVIEWED_STATUSES else EXIT_PENDING


def adjudicate(args) -> tuple[dict, int]:
    result = Library.open(args.root).adjudicate(args.book, args.unit)
    return result, EXIT_PENDING if result["needs_manual_review"] else EXIT_OK


def catalog(args) -> tuple[dict, int]:
    library = Library.open(args.root)
    library.require_valid_plan()
    stale = [f"{book.id}/{unit.id}" for book, unit in library.stale_units()]
    if stale:
        raise LibraryError(f"pages changed since extraction for {', '.join(stale)}; run ingest first")
    return library.navigation(), EXIT_OK


def status(args) -> tuple[dict, int]:
    return Library.open(args.root).status(args.book), EXIT_OK


def locate(args) -> tuple[dict, int]:
    return Library.open(args.root).locate(args.book, args.phrase, args.unit, args.limit), EXIT_OK


def render(args) -> tuple[dict, int]:
    library = Library.open(args.root)
    page = args.page if args.page is not None else library.pdf_page_for_label(args.book, args.label)
    return library.render(args.book, page, args.dpi), EXIT_OK


def bounded_int(minimum: int, maximum: int):
    def parse(text: str) -> int:
        value = int(text)
        if not minimum <= value <= maximum:
            raise argparse.ArgumentTypeError(f"must be between {minimum} and {maximum}")
        return value
    return parse


def parser() -> argparse.ArgumentParser:
    root_parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = root_parser.add_subparsers(dest="command", required=True)

    def command(name: str, handler, help_text: str) -> argparse.ArgumentParser:
        sub = commands.add_parser(name, help=help_text)
        sub.add_argument("--root", type=Path, required=True, help="Study workspace directory")
        sub.set_defaults(handler=handler)
        return sub

    def unit_command(name: str, handler, help_text: str) -> None:
        sub = command(name, handler, help_text)
        sub.add_argument("--book", required=True)
        sub.add_argument("--unit", required=True)

    sub = command("add", add, "Snapshot textbook PDFs and propose units from their outlines")
    sub.add_argument("pdf", nargs="+")
    sub.add_argument("--id", help="Short book id (lowercase, hyphens), e.g. axler-mira")
    command("check", check, "Validate library-plan.json, the stored originals and extraction freshness")
    sub = command("ingest", ingest, "Split units and build draft packages (resumable)")
    sub.add_argument("--book")
    sub.add_argument("--unit", action="append", default=[])
    sub.add_argument("--ocr", choices=["auto", "never", "always"], default="auto")
    unit_command("review-aid", review_aid, "Contact sheets and review queue for one unit")
    unit_command("finalize", finalize, "Reviewed build plus strict verification for one unit")
    unit_command("adjudicate", adjudicate, "Adjudicate diagnostics caused only by LaTeX transcription of formulas")
    command("catalog", catalog, "Regenerate SKILL.md, catalog.md and statements.csv")
    sub = command("status", status, "Tier, freshness and paths of every unit")
    sub.add_argument("--book")
    sub = command("locate", locate, "Find the pages containing a phrase (3-5 words within one line work best)")
    sub.add_argument("--book", required=True)
    sub.add_argument("--unit", help="Search only this unit's pages")
    sub.add_argument("phrase")
    sub.add_argument("--limit", type=bounded_int(1, 1000), default=DEFAULT_LOCATE_LIMIT)
    sub = command("render", render, "Render one page to PNG for visual checking")
    sub.add_argument("--book", required=True)
    where = sub.add_mutually_exclusive_group(required=True)
    where.add_argument("--page", type=int, help="One-based PDF page")
    where.add_argument("--label", help="Printed page label, e.g. 37 or xiv")
    sub.add_argument("--dpi", type=bounded_int(MIN_RENDER_DPI, MAX_RENDER_DPI), default=DEFAULT_RENDER_DPI)
    return root_parser


def use_utf8_output() -> None:
    """Windows pipes default to a legacy code page; book text and JSON need UTF-8."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    use_utf8_output()
    args = parser().parse_args(argv)
    try:
        result, exit_code = args.handler(args)
    except (LibraryError, BundleError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return EXIT_ERROR
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
