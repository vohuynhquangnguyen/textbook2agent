"""Read-only access to a textbook PDF: metadata, outline, printed page labels, splitting, search and rendering."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
from pathlib import Path
import re

import pymupdf

from library_errors import LibraryError
from unit_planner import OutlineEntry

HASH_CHUNK_BYTES = 1 << 20
CONTEXT_CHARACTERS = 60
LINE_BREAK_HYPHEN = re.compile(r"(?<=\w)- (?=\w)")


@dataclass(frozen=True)
class BookFacts:
    title: str
    authors: str
    page_count: int
    outline: list[OutlineEntry]


@dataclass(frozen=True)
class PageHit:
    page: int
    label: str
    context: str


@dataclass(frozen=True)
class PageRange:
    first: int
    last: int


@contextmanager
def open_pdf(path: Path):
    """Open a PDF, turning missing or unreadable files into a clear LibraryError."""
    try:
        document = pymupdf.open(path)
    except (RuntimeError, ValueError) as error:
        raise LibraryError(f"cannot open PDF {path}: {error}") from error
    try:
        yield document
    finally:
        document.close()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(HASH_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_facts(path: Path) -> BookFacts:
    with open_pdf(path) as document:
        metadata = document.metadata or {}
        outline = [OutlineEntry(level, title, page) for level, title, page in document.get_toc(simple=True)]
        return BookFacts(metadata.get("title") or path.stem, metadata.get("author") or "", document.page_count, outline)


def page_count(path: Path) -> int:
    with open_pdf(path) as document:
        return document.page_count


class PageLabels:
    """Printed page labels ("xiv", "37") for one-based PDF pages; PDF numbers when the PDF has no labels."""

    def __init__(self, labels: list[str]) -> None:
        self._labels = labels

    @classmethod
    def from_pdf(cls, path: Path) -> PageLabels:
        with open_pdf(path) as document:
            return cls([page.get_label() for page in document])

    def label(self, page: int) -> str:
        if 1 <= page <= len(self._labels) and self._labels[page - 1]:
            return self._labels[page - 1]
        return str(page)

    def pdf_page(self, label: str) -> int:
        matches = [page for page in range(1, len(self._labels) + 1) if self.label(page) == label]
        if len(matches) != 1:
            raise LibraryError(f"printed page {label!r} matches {len(matches)} PDF pages; use --page with the PDF page")
        return matches[0]


def write_page_range(source: Path, pages: PageRange, destination: Path) -> None:
    """Copy one-based, inclusive pages into a new PDF (atomic replace)."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".pdf.tmp")
    with open_pdf(source) as document, pymupdf.open() as part:
        part.insert_pdf(document, from_page=pages.first - 1, to_page=pages.last - 1)
        part.save(temporary, garbage=3, deflate=True)
    temporary.replace(destination)


def render_page(source: Path, page: int, dpi: int, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with open_pdf(source) as document:
        document[page - 1].get_pixmap(dpi=dpi).save(destination)
    return destination


def searchable_forms(text: str) -> tuple[str, str]:
    """Whitespace-normalised, lower-case text, with and without line-break hyphens joined."""
    flat = " ".join(text.split()).lower()
    return flat, LINE_BREAK_HYPHEN.sub("", flat)


def find_phrase(source: Path, phrase: str, labels: PageLabels, pages: PageRange, limit: int) -> list[PageHit]:
    """Pages in the range whose text contains the phrase, ignoring case, spacing and line-break hyphens."""
    wanted = " ".join(phrase.lower().split())
    hits: list[PageHit] = []
    with open_pdf(source) as document:
        for page in range(pages.first, pages.last + 1):
            for text in searchable_forms(document[page - 1].get_text()):
                position = text.find(wanted)
                if position >= 0:
                    hits.append(PageHit(page, labels.label(page), context_around(text, position, len(wanted))))
                    break
            if len(hits) >= limit:
                break
    return hits


def context_around(text: str, position: int, length: int) -> str:
    start = max(0, position - CONTEXT_CHARACTERS)
    return text[start:position + length + CONTEXT_CHARACTERS]
