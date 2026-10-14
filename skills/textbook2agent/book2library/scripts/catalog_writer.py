"""Generate the library's navigation files: SKILL.md, references/catalog.md and references/statements.csv."""

from __future__ import annotations

from collections import defaultdict
import csv
from dataclasses import dataclass
import json
from pathlib import Path
import re
from string import Template

from book_pdf import PageLabels
from library_layout import StudyLayout
from library_plan import Book, LibraryPlan
from unit_planner import Unit, slug

TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "library_skill.md"
MARKUP = re.compile(r"</?su[bp]>|[#*_`>]")
# "Exercises", "Exercises 2A", "Problems 3.4": a numeric prefix is joined to bare exercise numbers (2A + 4 -> 2A.4).
EXERCISES_HEADING = re.compile(r"^(?:exercises?|problems)\b\s*(?P<prefix>\d[0-9a-z]*(?:\.[0-9a-z]+)*)?", re.IGNORECASE)
NUMBERED_EXERCISE = re.compile(r"^(?P<number>\d+(?:\.\d+)*[a-z]?)[.)]?\s+\S")
SNIPPET_CHARACTERS = 160
SHA_PREFIX_CHARACTERS = 12
GAP_DENSITY = 0.6  # report gaps only where most numbers of a sequence were found
MAX_GAPS_PER_SEQUENCE = 12
STATEMENT_COLUMNS = ["book", "unit", "section", "kind", "number", "printed_page", "pdf_page", "tier", "text"]

Tiers = dict[tuple[str, str], str]


@dataclass(frozen=True)
class Statement:
    book: str
    unit: str
    section: str
    kind: str
    number: str
    printed_page: str
    pdf_page: int
    tier: str
    text: str

    def row(self) -> list[str]:
        return [self.book, self.unit, self.section, self.kind, self.number, self.printed_page, str(self.pdf_page),
                self.tier, self.text]


@dataclass(frozen=True)
class Found:
    """A statement located on one page of a unit (page counted within the unit)."""

    unit_page: int
    section: str
    kind: str
    number: str
    text: str


def plain_text(markdown: str) -> str:
    return " ".join(MARKUP.sub("", markdown).split())


def compile_statement_patterns(patterns: list[str]) -> list[re.Pattern]:
    return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]


def first_statement_match(text: str, patterns: list[re.Pattern]) -> re.Match | None:
    """The first pattern matching at the start of a paragraph's plain text, if any."""
    return next((match for match in (pattern.match(text) for pattern in patterns) if match), None)


class StatementScanner:
    """Walks a unit's page items in reading order, tracking the current heading and any Exercises section.

    Labelled statements ("Definition 2.7 …") are found everywhere; bare numbered paragraphs ("2.12 Consider …")
    count as exercises only inside a section headed "Exercises" or "Problems".
    """

    def __init__(self, patterns: list[re.Pattern], unit_title: str) -> None:
        self._patterns = patterns
        self._section = unit_title
        self._exercise_prefix: str | None = None  # None outside an Exercises section

    def scan(self, pages: list[dict]) -> list[Found]:
        found: list[Found] = []
        for page in pages:
            for item in page["items"]:
                statement = self._visit(item, page["page"])
                if statement:
                    found.append(statement)
        return found

    def _visit(self, item: dict, unit_page: int) -> Found | None:
        text = plain_text(item.get("markdown", ""))
        if item.get("kind") == "heading":
            self._enter_section(text)
        if item.get("kind") not in ("text", "heading", "caption") or not text:
            return None
        labelled = first_statement_match(text, self._patterns)
        if labelled:
            return Found(unit_page, self._section, labelled["kind"].lower(), labelled["number"], text)
        in_exercises = self._exercise_prefix is not None and item.get("kind") == "text"
        exercise = NUMBERED_EXERCISE.match(text) if in_exercises else None
        if exercise:
            return Found(unit_page, self._section, "exercise", self._exercise_number(exercise["number"]), text)
        return None

    def _exercise_number(self, number: str) -> str:
        if self._exercise_prefix and "." not in number:
            return f"{self._exercise_prefix}.{number}"
        return number

    def _enter_section(self, heading: str) -> None:
        self._section = heading
        match = EXERCISES_HEADING.match(heading)
        self._exercise_prefix = (match["prefix"] or "") if match else None


def unit_pages(review_dir: Path) -> list[dict]:
    files = sorted(review_dir.glob("documents/*/pages/page-*.json"))
    return [json.loads(path.read_text(encoding="utf-8")) for path in files]


def statements_in_unit(layout: StudyLayout, book: Book, unit: Unit, labels: PageLabels, tier: str) -> list[Statement]:
    scanner = StatementScanner(compile_statement_patterns(book.active_statement_patterns), unit.title)
    statements = []
    for found in scanner.scan(unit_pages(layout.review_dir(book.id, unit.id))):
        pdf_page = unit.first_page + found.unit_page - 1
        statements.append(Statement(book.id, unit.id, found.section, found.kind, found.number,
                                    labels.label(pdf_page), pdf_page, tier, found.text[:SNIPPET_CHARACTERS]))
    return statements


def collect_statements(layout: StudyLayout, plan: LibraryPlan, tiers: Tiers) -> list[Statement]:
    statements = []
    for book in plan.books:
        labels = PageLabels.from_pdf(layout.original(book.id))
        for unit in book.units:
            statements += statements_in_unit(layout, book, unit, labels, tiers[(book.id, unit.id)])
    return statements


def write_statements(layout: StudyLayout, statements: list[Statement]) -> None:
    layout.statements.parent.mkdir(parents=True, exist_ok=True)
    with layout.statements.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(STATEMENT_COLUMNS)
        writer.writerows(statement.row() for statement in statements)


def split_number(number: str) -> tuple[str, int] | None:
    """"2.21" -> ("2", 21); "7" -> ("", 7); anything else -> None."""
    prefix, _, last = number.rpartition(".")
    return (prefix, int(last)) if last.isdigit() else None


def numbering_gaps(statements: list[Statement]) -> list[str]:
    """Numbers missing from mostly complete sequences, e.g. Definition 2.21 between 2.20 and 2.22.

    A number used by another kind (a shared counter: Theorem 2.17 between Definitions 2.16 and 2.18) is not a gap.
    """
    sequences: dict[tuple, set[int]] = defaultdict(set)
    used: set[tuple] = set()
    for statement in statements:
        parts = split_number(statement.number)
        if parts is None:
            continue
        section = statement.section if statement.kind == "exercise" else ""
        sequences[(statement.book, statement.kind, section, parts[0])].add(parts[1])
        used.add((statement.book, section, *parts))
    lines = []
    for (book, kind, section, prefix), numbers in sorted(sequences.items()):
        missing = [n for n in range(1, max(numbers) + 1) if n not in numbers and (book, section, prefix, n) not in used]
        if missing and len(numbers) >= GAP_DENSITY * max(numbers):
            shown = ", ".join(f"{prefix}.{n}" if prefix else str(n) for n in missing[:MAX_GAPS_PER_SEQUENCE])
            where = f" in “{section}”" if section else ""
            lines.append(f"- `{book}` {kind}{where}: {shown}")
    return lines


def page_span(first: int | str, last: int | str) -> str:
    return str(first) if first == last else f"{first}–{last}"


def escape_cell(text: str) -> str:
    return text.replace("|", "\\|")


def unit_row(layout: StudyLayout, book: Book, unit: Unit, labels: PageLabels, tier: str) -> str:
    text = layout.unit_text(book.id, unit.id)
    link = f"[text](../units/{book.id}/{unit.id}/references/paper.md)" if text.is_file() else "—"
    printed = page_span(labels.label(unit.first_page), labels.label(unit.last_page))
    flag = " (spoilers: open only after an attempt)" if unit.kind == "solutions" else ""
    pdf_pages = page_span(unit.first_page, unit.last_page)
    cells = [f"`{unit.id}`", f"{unit.kind}{flag}", escape_cell(unit.title), pdf_pages, printed, tier, link]
    return "| " + " | ".join(cells) + " |"


def section_lines(book: Book, labels: PageLabels) -> list[str]:
    lines = []
    for unit in book.units:
        if unit.sections:
            entries = "; ".join(f"{s.title} (p. {labels.label(s.page)} · PDF {s.page})" for s in unit.sections)
            lines.append(f"- **{unit.id}** — {entries}")
    return lines


def book_block(layout: StudyLayout, book: Book, tiers: Tiers) -> list[str]:
    labels = PageLabels.from_pdf(layout.original(book.id))
    edition = f" · {book.edition}" if book.edition else ""
    lines = [
        f"## {book.title} — `{book.id}`",
        "",
        f"{book.authors or 'Unknown authors'}{edition} · {book.page_count} PDF pages · "
        f"source SHA-256 `{book.sha256[:SHA_PREFIX_CHARACTERS]}…`",
        "",
        "| Unit | Kind | Title | PDF pages | Printed pages | Tier | Text |",
        "| --- | --- | --- | --- | --- | --- | --- |",
        *(unit_row(layout, book, unit, labels, tiers[(book.id, unit.id)]) for unit in book.units),
        "",
    ]
    sections = section_lines(book, labels)
    if sections:
        lines += ["### Sections", "", *sections, ""]
    return lines


def write_catalog(layout: StudyLayout, plan: LibraryPlan, tiers: Tiers, gaps: list[str]) -> None:
    lines = [
        "# Library catalog",
        "",
        "Tiers: **reviewed** = page-by-page reviewed and strictly verified; **draft** = automatic extraction, so "
        "check any formula, definition or statement against the page image before quoting it; "
        "**planned** = not extracted yet.",
        "Cite as `[book] Definition 2.7, p. <printed> (PDF <n>)`.",
        "",
    ]
    for book in plan.books:
        lines += book_block(layout, book, tiers)
    if gaps:
        lines += ["## Possible gaps in statements.csv", "",
                  "Numbers missing from otherwise complete sequences. The statement may exist but was not detected "
                  "(for example inside a formula image); find it with `locate` or the page images.", "", *gaps, ""]
    layout.catalog.parent.mkdir(parents=True, exist_ok=True)
    layout.catalog.write_text("\n".join(lines), encoding="utf-8")


def write_library_skill(layout: StudyLayout, plan: LibraryPlan) -> None:
    titles = "; ".join(f"{book.title} ({book.id})" for book in plan.books)
    description = (f"Searchable textbook library for self-study: {titles}. Look up definitions, theorems, examples "
                   f"and exercises with printed-page citations.")
    book_list = "\n".join(f"- `{book.id}` — {book.title}, {book.authors or 'unknown authors'}" for book in plan.books)
    text = Template(TEMPLATE.read_text(encoding="utf-8")).substitute(
        name=f"{slug(layout.root.name, max_length=50)}-library",
        description=json.dumps(description, ensure_ascii=False),
        book_list=book_list,
    )
    layout.library_skill.parent.mkdir(parents=True, exist_ok=True)
    layout.library_skill.write_text(text, encoding="utf-8")


def write_navigation(layout: StudyLayout, plan: LibraryPlan, tiers: Tiers) -> dict:
    statements = collect_statements(layout, plan, tiers)
    gaps = numbering_gaps(statements)
    write_library_skill(layout, plan)
    write_catalog(layout, plan, tiers, gaps)
    write_statements(layout, statements)
    return {
        "skill": layout.relative(layout.library_skill),
        "catalog": layout.relative(layout.catalog),
        "statements": layout.relative(layout.statements),
        "statement_count": len(statements),
        "possible_gaps": len(gaps),
    }
