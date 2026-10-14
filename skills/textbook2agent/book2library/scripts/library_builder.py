"""Library operations: add books, keep units in step with the plan, and build draft or reviewed unit packages."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import shutil

from book_pdf import (PageLabels, PageRange, find_phrase, page_count, read_facts, render_page, sha256_file,
                      write_page_range)
from bundle_runner import BundleResult, PaperBundle
from catalog_writer import write_navigation
from library_errors import LibraryError
from library_layout import StudyLayout
from library_plan import Book, LibraryPlan, book_id_issues, load_plan, save_plan
from transcription_adjudicator import adjudicate_review_dir
from unit_planner import Unit, propose_units, slug


@dataclass(frozen=True)
class UnitSource:
    """What a unit's review directory was extracted from; any change means the unit must start over."""

    book_sha256: str
    first_page: int
    last_page: int

    @classmethod
    def of(cls, book: Book, unit: Unit) -> UnitSource:
        return cls(book.sha256, unit.first_page, unit.last_page)

    @classmethod
    def load(cls, path: Path) -> UnitSource | None:
        if not path.is_file():
            return None
        return cls(**json.loads(path.read_text(encoding="utf-8")))

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2) + "\n", encoding="utf-8")


class DraftBuild:
    def build(self, bundle: PaperBundle, output: Path) -> BundleResult:
        return bundle.build_draft(output)


class ReviewedBuild:
    def build(self, bundle: PaperBundle, output: Path) -> BundleResult:
        return bundle.build_reviewed(output)


class Library:
    def __init__(self, root: Path) -> None:
        self.layout = StudyLayout(root.expanduser().resolve())
        self.plan: LibraryPlan = load_plan(self.layout.plan_file) if self.layout.plan_file.is_file() else LibraryPlan()

    @classmethod
    def open(cls, root: Path) -> Library:
        library = cls(root)
        if not library.layout.plan_file.is_file():
            raise LibraryError(f"no library-plan.json in {library.layout.root}; check --root, or run add first")
        return library

    def relative(self, path: Path) -> str:
        return self.layout.relative(path)

    # Books -----------------------------------------------------------------

    def add_book(self, pdf_path: Path, book_id: str | None) -> Book:
        source = pdf_path.expanduser().resolve()
        facts = read_facts(source)
        proposal = propose_units(facts.outline, facts.page_count)
        identifier = book_id or slug(source.stem)
        issues = book_id_issues(identifier, max((u.id for u in proposal.units), key=len))
        if issues:
            raise LibraryError("; ".join(issues))
        original = self.layout.original(identifier)
        book = Book(identifier, facts.title, facts.authors, self.relative(original), sha256_file(source),
                    facts.page_count, proposal.units, proposal.chapter_level, warnings=proposal.warnings)
        self.plan.add(book)
        original.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, original)
        save_plan(self.plan, self.layout.plan_file)
        return book

    # Plan health -----------------------------------------------------------

    def plan_issues(self) -> list[str]:
        issues = self.plan.issues()
        for book in self.plan.books:
            issues.extend(self._original_issues(book))
        return issues

    def _original_issues(self, book: Book) -> list[str]:
        original = self.layout.original(book.id)
        if not original.is_file():
            return [f"{book.id}: original snapshot missing at {self.relative(original)}"]
        if sha256_file(original) != book.sha256:
            return [f"{book.id}: original snapshot no longer matches the recorded SHA-256"]
        actual_pages = page_count(original)
        if actual_pages != book.page_count:
            return [f"{book.id}: page_count is {book.page_count} but the PDF has {actual_pages} pages"]
        return []

    def stale_units(self) -> list[tuple[Book, Unit]]:
        """Units whose extraction no longer matches the plan (pages moved, or an interrupted start)."""
        return [(book, unit) for book in self.plan.books for unit in book.units if self._is_stale(book, unit)]

    def _is_stale(self, book: Book, unit: Unit) -> bool:
        review_dir = self.layout.review_dir(book.id, unit.id)
        if not review_dir.exists():
            return False
        recorded = UnitSource.load(self.layout.source_marker(book.id, unit.id))
        return recorded != UnitSource.of(book, unit) or not self.bundle(book, unit).is_prepared()

    def orphaned_units(self) -> list[tuple[str, str]]:
        """Review directories on disk for units no longer in the plan."""
        planned = {(book.id, unit.id) for book in self.plan.books for unit in book.units}
        on_disk = {(path.parent.name, path.name) for path in self.layout.work.glob("review/*/*") if path.is_dir()}
        return sorted(on_disk - planned)

    def issues(self) -> list[str]:
        issues = self.plan_issues()
        issues += [f"{b.id}/{u.id}: pages changed since extraction; run ingest to restart it"
                   for b, u in self.stale_units()]
        issues += [f"{b}/{u}: not in the plan any more; run ingest to retire it" for b, u in self.orphaned_units()]
        return issues

    def require_valid_plan(self) -> None:
        issues = self.plan_issues()
        if issues:
            raise LibraryError("Fix library-plan.json first:\n- " + "\n- ".join(issues))

    def require_current(self, book: Book, unit: Unit) -> PaperBundle:
        bundle = self.bundle(book, unit)
        if not bundle.is_prepared():
            raise LibraryError(f"{book.id}/{unit.id} has not been ingested yet; run ingest")
        if self._is_stale(book, unit):
            raise LibraryError(f"{book.id}/{unit.id}: pages changed since extraction; run ingest to restart it")
        return bundle

    def selected_units(self, book_id: str | None, unit_ids: list[str]) -> list[tuple[Book, Unit]]:
        if unit_ids and not book_id:
            raise LibraryError("--unit needs --book")
        books = [self.plan.book(book_id)] if book_id else self.plan.books
        if unit_ids:
            return [(books[0], books[0].unit(unit_id)) for unit_id in unit_ids]
        return [(book, unit) for book in books for unit in book.units]

    # Units -----------------------------------------------------------------

    def bundle(self, book: Book, unit: Unit) -> PaperBundle:
        return PaperBundle(self.layout.review_dir(book.id, unit.id))

    def tiers(self) -> dict[tuple[str, str], str]:
        return {(book.id, unit.id): self.bundle(book, unit).tier() for book in self.plan.books for unit in book.units}

    def retire(self, book_id: str, unit_id: str) -> None:
        """Move a unit's review directory, package and marker aside, keeping them under .work/replaced/."""
        holder = self.layout.make_replaced_dir(book_id, unit_id)
        for path, name in ((self.layout.review_dir(book_id, unit_id), "review"),
                           (self.layout.unit_package(book_id, unit_id), "package"),
                           (self.layout.source_marker(book_id, unit_id), "source.json")):
            if path.exists():
                shutil.move(str(path), str(holder / name))

    def prepare_unit(self, book: Book, unit: Unit, ocr: str) -> PaperBundle:
        bundle = self.bundle(book, unit)
        if not bundle.is_prepared():
            unit_pdf = self.layout.unit_pdf(book.id, unit.id)
            write_page_range(self.layout.original(book.id), PageRange(unit.first_page, unit.last_page), unit_pdf)
            UnitSource.of(book, unit).save(self.layout.source_marker(book.id, unit.id))
            bundle.prepare(unit_pdf, f"{book.id}-{unit.id}", f"{book.title} — {unit.title}")
        bundle.extract(ocr)
        return bundle

    def ingest_unit(self, book: Book, unit: Unit, ocr: str) -> dict:
        bundle = self.prepare_unit(book, unit, ocr)
        package_missing = not self.layout.unit_package(book.id, unit.id).exists()
        if bundle.tier() == "planned" or package_missing:
            self.publish(book, unit, DraftBuild())
        return {"book": book.id, "unit": unit.id, "tier": bundle.tier()}

    def ingest(self, book_id: str | None, unit_ids: list[str], ocr: str) -> dict:
        """Build the selected units, plus every unit whose pages changed, so no unit is left without text."""
        self.require_valid_plan()
        stale = self.stale_units()
        orphaned = self.orphaned_units()
        for book, unit in stale:
            self.retire(book.id, unit.id)
        for orphan_book_id, orphan_unit_id in orphaned:
            self.retire(orphan_book_id, orphan_unit_id)
        selected = self.selected_units(book_id, unit_ids)
        to_build = selected + [pair for pair in stale if pair not in selected]
        try:
            results = [self.ingest_unit(book, unit, ocr) for book, unit in to_build]
        finally:
            navigation = self.navigation()
        return {"units": results, "restarted": [f"{book.id}/{unit.id}" for book, unit in stale],
                "retired": [f"{b}/{u}" for b, u in orphaned], "navigation": navigation}

    def finalize(self, book_id: str, unit_id: str) -> dict:
        self.require_valid_plan()
        book = self.plan.book(book_id)
        unit = book.unit(unit_id)
        bundle = self.require_current(book, unit)
        self.publish(book, unit, ReviewedBuild())
        result = bundle.verify_strict()
        return {"book": book.id, "unit": unit.id, "status": result.status, "strict_exit_code": result.exit_code,
                "verification": self.relative(bundle.work / "verification.json"), "navigation": self.navigation()}

    def review_aid(self, book_id: str, unit_id: str) -> dict:
        book = self.plan.book(book_id)
        bundle = self.require_current(book, book.unit(unit_id))
        return {**bundle.review_aid().report, "review_dir": self.relative(bundle.work)}

    def adjudicate(self, book_id: str, unit_id: str) -> dict:
        book = self.plan.book(book_id)
        bundle = self.require_current(book, book.unit(unit_id))
        return adjudicate_review_dir(bundle.work)

    def publish(self, book: Book, unit: Unit, mode) -> None:
        """Build into the stable unit path; if the build fails, put the previous package back."""
        package = self.layout.unit_package(book.id, unit.id)
        holder = None
        if package.exists():
            holder = self.layout.make_replaced_dir(book.id, unit.id)
            shutil.move(str(package), str(holder / "package"))
        try:
            mode.build(self.bundle(book, unit), package)
        except BaseException:
            if holder is not None:
                restore_package(holder / "package", package)
            raise
        if holder is not None:
            shutil.rmtree(holder, ignore_errors=True)

    def navigation(self) -> dict:
        return write_navigation(self.layout, self.plan, self.tiers())

    def unit_status(self, book: Book, unit: Unit) -> dict:
        return {
            "book": book.id,
            "unit": unit.id,
            "kind": unit.kind,
            "pdf_pages": [unit.first_page, unit.last_page],
            "tier": self.bundle(book, unit).tier(),
            "stale": self._is_stale(book, unit),
            "review_dir": self.relative(self.layout.review_dir(book.id, unit.id)),
            "text": self.relative(self.layout.unit_text(book.id, unit.id)),
        }

    def status(self, book_id: str | None) -> dict:
        return {"units": [self.unit_status(book, unit) for book, unit in self.selected_units(book_id, [])]}

    # Pages -----------------------------------------------------------------

    def labels(self, book: Book) -> PageLabels:
        return PageLabels.from_pdf(self.layout.original(book.id))

    def locate(self, book_id: str, phrase: str, unit_id: str | None, limit: int) -> dict:
        book = self.plan.book(book_id)
        unit = book.unit(unit_id) if unit_id else None
        pages = PageRange(unit.first_page, unit.last_page) if unit else PageRange(1, book.page_count)
        hits = find_phrase(self.layout.original(book.id), phrase, self.labels(book), pages, limit)
        rows = [{"pdf_page": hit.page, "printed_page": hit.label, "unit": book.unit_for_page(hit.page).id,
                 "context": hit.context} for hit in hits]
        return {"book": book.id, "phrase": phrase, "hits": rows}

    def pdf_page_for_label(self, book_id: str, label: str) -> int:
        return self.labels(self.plan.book(book_id)).pdf_page(label)

    def render(self, book_id: str, page: int, dpi: int) -> dict:
        book = self.plan.book(book_id)
        if not 1 <= page <= book.page_count:
            raise LibraryError(f"page {page} is outside 1–{book.page_count}")
        image = render_page(self.layout.original(book.id), page, dpi, self.layout.render(book.id, page, dpi))
        return {"book": book.id, "pdf_page": page, "printed_page": self.labels(book).label(page), "image": str(image)}


def restore_package(backup: Path, package: Path) -> None:
    """Remove a failed build and move the previous package back, refusing to merge the two."""
    shutil.rmtree(package, ignore_errors=True)
    if package.exists():
        raise LibraryError(f"could not remove the failed build at {package}; the previous package is kept at {backup}")
    shutil.move(str(backup), str(package))
