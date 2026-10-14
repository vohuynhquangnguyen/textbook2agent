"""The editable library plan (library-plan.json): which books, and how each splits into units."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import re

from library_errors import LibraryError
from unit_planner import Section, Unit, validate_units

SCHEMA_VERSION = 1
BOOK_ID = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MAX_PACKAGE_NAME = 63  # paper2skill's limit for "<book>-<unit>"
STATEMENT_KINDS = "definition|theorem|lemma|proposition|corollary|example|exercise|remark|algorithm"
DEFAULT_STATEMENT_PATTERNS = (
    # "Definition 2.7 (Name). ...", "Theorem 4.1. ...", "Example 2.3" -- but not "Theorem 2.17 states that ..."
    rf"^(?P<kind>{STATEMENT_KINDS}|problem)\s+(?P<number>(?>\d+(?:\.\d+)*[a-z]?))(?!\s+(?-i:[a-z]))",
    # "2.7 Definition outer measure", "1.2 Proposition. ..."
    rf"^(?P<number>(?>\d+(?:\.\d+)*[a-z]?))\s+(?P<kind>{STATEMENT_KINDS})\b",
)


def book_id_issues(book_id: str, longest_unit_id: str = "") -> list[str]:
    issues = []
    if not BOOK_ID.match(book_id):
        issues.append(f"{book_id!r}: book ids use lowercase letters, digits and single hyphens (e.g. axler-mira)")
    if len(book_id) + 1 + len(longest_unit_id) > MAX_PACKAGE_NAME:
        issues.append(f"{book_id}: book id plus unit id must be at most {MAX_PACKAGE_NAME} characters; shorten the id")
    return issues


@dataclass
class Book:
    id: str
    title: str
    authors: str
    source: str
    sha256: str
    page_count: int
    units: list[Unit]
    chapter_level: int | None = None
    edition: str = ""
    statement_patterns: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def active_statement_patterns(self) -> list[str]:
        """Book-specific patterns when given, otherwise the defaults."""
        return self.statement_patterns or list(DEFAULT_STATEMENT_PATTERNS)

    def unit(self, unit_id: str) -> Unit:
        for unit in self.units:
            if unit.id == unit_id:
                return unit
        raise LibraryError(f"book {self.id} has no unit {unit_id!r}; units: {', '.join(u.id for u in self.units)}")

    def unit_for_page(self, page: int) -> Unit:
        for unit in self.units:
            if unit.first_page <= page <= unit.last_page:
                return unit
        raise LibraryError(f"book {self.id}: no unit covers PDF page {page}; run check")

    def issues(self) -> list[str]:
        longest_unit_id = max((unit.id for unit in self.units), key=len, default="")
        issues = book_id_issues(self.id, longest_unit_id)
        issues.extend(f"{self.id}/{issue}" for issue in validate_units(self.units, self.page_count))
        issues.extend(self._pattern_issues())
        return issues

    def _pattern_issues(self) -> list[str]:
        issues = []
        for pattern in self.active_statement_patterns:
            try:
                groups = re.compile(pattern).groupindex
            except re.error as error:
                issues.append(f"{self.id}: invalid statement pattern {pattern!r}: {error}")
                continue
            if not {"kind", "number"} <= set(groups):
                issues.append(f"{self.id}: statement pattern {pattern!r} needs named groups 'kind' and 'number'")
        return issues


@dataclass
class LibraryPlan:
    books: list[Book] = field(default_factory=list)

    def book(self, book_id: str) -> Book:
        for book in self.books:
            if book.id == book_id:
                return book
        raise LibraryError(f"no book {book_id!r} in the plan; books: {', '.join(b.id for b in self.books) or 'none'}")

    def add(self, book: Book) -> None:
        if any(existing.id == book.id for existing in self.books):
            raise LibraryError(f"book id {book.id!r} already exists; pass a different --id")
        self.books.append(book)

    def issues(self) -> list[str]:
        issues = [issue for book in self.books for issue in book.issues()]
        ids = [book.id for book in self.books]
        issues.extend(f"duplicate book id {book_id!r}" for book_id in sorted({i for i in ids if ids.count(i) > 1}))
        return issues


def require_integers(data: dict, keys: tuple[str, ...]) -> None:
    for key in keys:
        if not isinstance(data[key], int) or isinstance(data[key], bool):
            raise TypeError(f"{key} must be a whole number, got {data[key]!r}")


def unit_from_json(data: dict) -> Unit:
    require_integers(data, ("first_page", "last_page"))
    sections = [Section(**section) for section in data.get("sections", [])]
    return Unit(data["id"], data["kind"], data["title"], data["first_page"], data["last_page"], sections)


def book_from_json(data: dict) -> Book:
    require_integers(data, ("page_count",))
    fields = {key: value for key, value in data.items() if key != "units"}
    return Book(units=[unit_from_json(unit) for unit in data["units"]], **fields)


def load_plan(path: Path) -> LibraryPlan:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if data.get("schema_version") != SCHEMA_VERSION:
            raise LibraryError(f"{path}: expected schema_version {SCHEMA_VERSION}")
        return LibraryPlan([book_from_json(book) for book in data["books"]])
    except json.JSONDecodeError as error:
        raise LibraryError(f"{path} is not valid JSON: {error}") from error
    except (KeyError, TypeError, AttributeError) as error:
        raise LibraryError(f"{path}: a book or unit entry has a missing, extra or mistyped field ({error})") from error


def save_plan(plan: LibraryPlan, path: Path) -> None:
    data = {"schema_version": SCHEMA_VERSION, "books": [asdict(book) for book in plan.books]}
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)
