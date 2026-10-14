"""Propose study units (chapters, appendices, front and back matter) from a book outline.

Pure logic with no PDF access. A proposal is a starting point: the agent reviews it
against the printed contents pages and edits library-plan.json before extraction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re

NUMBERED_CHAPTER_TITLE = re.compile(r"^\s*(chapter|lecture)\s+\w+|^\s*\d+[.:]?\s+\S", re.IGNORECASE)
PART_TITLE = re.compile(r"^\s*part\b", re.IGNORECASE)
APPENDIX_TITLE = re.compile(r"^\s*(?i:appendix)\b|^\s*[A-Z][.:]?\s+[A-Z]\S")
SOLUTIONS_TITLE = re.compile(r"^\s*(solutions?|answers?|hints)\b", re.IGNORECASE)
FRONT_MATTER_TITLE = re.compile(
    r"^\s*(preface|foreword|contents|table of contents|acknowledge?ments?|dedication|"
    r"about (this|the) (book|authors?)|notation|list of (figures|tables|symbols)|copyright|title page)\b",
    re.IGNORECASE,
)
BACK_MATTER_TITLE = re.compile(
    r"^\s*(references|bibliography|index|subject index|author index|notation index|"
    r"index of notation|list of symbols|glossary)\s*$",
    re.IGNORECASE,
)
UNIT_ID = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
UNIT_KINDS = ("front", "chapter", "appendix", "solutions", "back")
MINIMUM_NUMBERED_CHAPTERS = 2
MINIMUM_TOP_LEVEL_ENTRIES = 3
LETTERED_APPENDICES = 26


@dataclass(frozen=True)
class OutlineEntry:
    level: int
    title: str
    page: int


@dataclass(frozen=True)
class Section:
    title: str
    page: int


@dataclass
class Unit:
    id: str
    kind: str
    title: str
    first_page: int
    last_page: int
    sections: list[Section] = field(default_factory=list)


@dataclass(frozen=True)
class UnitStart:
    kind: str
    page: int
    entry: OutlineEntry


@dataclass(frozen=True)
class Proposal:
    units: list[Unit]
    chapter_level: int | None
    warnings: list[str]


def matter_kind(title: str) -> str | None:
    """Kind of a non-chapter unit (back matter, solutions, appendix) named by a title, if any."""
    if BACK_MATTER_TITLE.match(title):
        return "back"
    if SOLUTIONS_TITLE.match(title):
        return "solutions"
    if APPENDIX_TITLE.match(title):
        return "appendix"
    return None


class NumberedChapterClassifier:
    """Outline whose chapter-level entries carry numbers ("2 Linear Algebra", "Chapter 2")."""

    warning = None

    def is_chapter(self, title: str) -> bool:
        return bool(NUMBERED_CHAPTER_TITLE.match(title)) and not PART_TITLE.match(title)

    def kind(self, title: str) -> str | None:
        return "chapter" if self.is_chapter(title) else matter_kind(title)


class TopLevelClassifier:
    """Fallback for unnumbered chapters: every top-level entry not recognised as front or back matter."""

    warning = "Chapters are unnumbered in the outline: every top-level entry became a unit; check kinds and boundaries."

    def is_chapter(self, title: str) -> bool:
        return not FRONT_MATTER_TITLE.match(title) and matter_kind(title) is None

    def kind(self, title: str) -> str | None:
        return matter_kind(title) or "chapter"


def numbered_chapter_level(entries: list[OutlineEntry]) -> int | None:
    """Shallowest outline level holding at least two numbered chapter titles."""
    classifier = NumberedChapterClassifier()
    for level in sorted({entry.level for entry in entries}):
        chapters = [e for e in entries if e.level == level and classifier.is_chapter(e.title)]
        if len(chapters) >= MINIMUM_NUMBERED_CHAPTERS:
            return level
    return None


def choose_classifier(entries: list[OutlineEntry]):
    """Return (classifier, chapter level), or (None, None) when the outline is unusable."""
    level = numbered_chapter_level(entries)
    if level is not None:
        return NumberedChapterClassifier(), level
    top_level = min((entry.level for entry in entries), default=None)
    if sum(1 for entry in entries if entry.level == top_level) >= MINIMUM_TOP_LEVEL_ENTRIES:
        return TopLevelClassifier(), top_level
    return None, None


def first_chapter_index(entries: list[OutlineEntry], level: int, classifier) -> int | None:
    return next((i for i, e in enumerate(entries) if e.level == level and classifier.is_chapter(e.title)), None)


def start_kind(entry: OutlineEntry, level: int, classifier) -> str | None:
    """Kind of unit an entry at or after the first chapter starts; None when it starts nothing."""
    if entry.level == level:
        return classifier.kind(entry.title)
    if entry.level < level:
        return matter_kind(entry.title)
    return None


def divider_page(previous: OutlineEntry | None, level: int) -> int | None:
    """A part divider (a shallower, non-front-matter entry) directly before a chapter belongs to that chapter."""
    if previous is None or previous.level >= level:
        return None
    if FRONT_MATTER_TITLE.match(previous.title) or matter_kind(previous.title):
        return None
    return previous.page


def unit_starts(entries: list[OutlineEntry], level: int, classifier) -> list[UnitStart]:
    first = first_chapter_index(entries, level, classifier)
    if first is None:
        return []
    starts: list[UnitStart] = []
    for index in range(first, len(entries)):
        entry = entries[index]
        kind = start_kind(entry, level, classifier)
        if kind is None:
            continue
        previous = entries[index - 1] if index > 0 else None
        divider = divider_page(previous, level) if kind in ("chapter", "appendix") else None
        starts.append(UnitStart(kind, divider or entry.page, entry))
    return drop_same_page_starts(starts)


def drop_same_page_starts(starts: list[UnitStart]) -> list[UnitStart]:
    """When several starts share a page, keep the first one in outline order."""
    kept: list[UnitStart] = []
    for start in starts:
        if not kept or start.page > kept[-1].page:
            kept.append(start)
    return kept


def slug(text: str, max_length: int = 40) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:max_length].strip("-") or "unit"


class UnitIdAllocator:
    """Readable, unique unit ids: front, ch01, app-a, solutions, back-index."""

    def __init__(self) -> None:
        self._chapters = 0
        self._appendices = 0
        self._used: set[str] = set()

    def next_id(self, kind: str, title: str) -> str:
        candidate = self._candidate(kind, title)
        unique, suffix = candidate, 2
        while unique in self._used:
            unique, suffix = f"{candidate}-{suffix}", suffix + 1
        self._used.add(unique)
        return unique

    def _candidate(self, kind: str, title: str) -> str:
        if kind == "chapter":
            self._chapters += 1
            return f"ch{self._chapters:02d}"
        if kind == "appendix":
            self._appendices += 1
            return f"app-{self._appendix_label()}"
        if kind == "back":
            return f"back-{slug(title)}"
        return kind

    def _appendix_label(self) -> str:
        if self._appendices <= LETTERED_APPENDICES:
            return chr(ord("a") + self._appendices - 1)
        return str(self._appendices)


def units_from_starts(starts: list[UnitStart], page_count: int) -> list[Unit]:
    allocator = UnitIdAllocator()
    units: list[Unit] = []
    if starts[0].page > 1:
        units.append(Unit(allocator.next_id("front", ""), "front", "Front matter", 1, starts[0].page - 1))
    for position, start in enumerate(starts):
        is_last = position + 1 == len(starts)
        last_page = page_count if is_last else starts[position + 1].page - 1
        title = start.entry.title.strip()
        units.append(Unit(allocator.next_id(start.kind, title), start.kind, title, start.page, last_page))
    return units


def section_entries(entries: list[OutlineEntry], level: int, starts: list[UnitStart]) -> list[OutlineEntry]:
    """Entries one level below chapters, plus chapter-level entries merged into a unit (e.g. "Exercises")."""
    start_entries = {start.entry for start in starts}
    first_start_page = starts[0].page
    return [entry for entry in entries
            if entry.level == level + 1
            or (entry.level == level and entry not in start_entries and entry.page >= first_start_page)]


def attach_sections(units: list[Unit], sections: list[OutlineEntry]) -> None:
    for entry in sections:
        owner = next((unit for unit in units if unit.first_page <= entry.page <= unit.last_page), None)
        if owner is not None:
            owner.sections.append(Section(entry.title.strip(), entry.page))


def whole_book_proposal(page_count: int) -> Proposal:
    unit = Unit("whole", "chapter", "Whole book (split by hand)", 1, page_count)
    warning = "No usable outline: split the single 'whole' unit by hand using the printed contents pages."
    return Proposal([unit], None, [warning])


def propose_units(entries: list[OutlineEntry], page_count: int) -> Proposal:
    in_range = sorted((entry for entry in entries if 1 <= entry.page <= page_count), key=lambda entry: entry.page)
    classifier, level = choose_classifier(in_range)
    if classifier is None:
        return whole_book_proposal(page_count)
    starts = unit_starts(in_range, level, classifier)
    if not starts:
        return whole_book_proposal(page_count)
    units = units_from_starts(starts, page_count)
    attach_sections(units, section_entries(in_range, level, starts))
    warnings = [classifier.warning] if classifier.warning else []
    return Proposal(units, level, warnings)


def validate_units(units: list[Unit], page_count: int) -> list[str]:
    """Units must be well formed, uniquely named and cover every page exactly once, in order."""
    issues: list[str] = []
    seen_ids: set[str] = set()
    expected_first_page = 1
    for unit in units:
        issues.extend(unit_issues(unit, seen_ids))
        seen_ids.add(unit.id)
        if unit.first_page != expected_first_page:
            issues.append(f"{unit.id}: starts at page {unit.first_page}, "
                          f"expected {expected_first_page} (gap or overlap)")
        expected_first_page = unit.last_page + 1
    if expected_first_page != page_count + 1:
        issues.append(f"units end at page {expected_first_page - 1}, but the book has {page_count} pages")
    return issues


def unit_issues(unit: Unit, seen_ids: set[str]) -> list[str]:
    issues = []
    if not UNIT_ID.match(unit.id):
        issues.append(f"{unit.id!r}: unit ids use lowercase letters, digits and single hyphens")
    if unit.id in seen_ids:
        issues.append(f"{unit.id}: duplicate unit id")
    if unit.kind not in UNIT_KINDS:
        issues.append(f"{unit.id}: kind {unit.kind!r} is not one of {', '.join(UNIT_KINDS)}")
    if unit.last_page < unit.first_page:
        issues.append(f"{unit.id}: last_page {unit.last_page} precedes first_page {unit.first_page}")
    return issues
