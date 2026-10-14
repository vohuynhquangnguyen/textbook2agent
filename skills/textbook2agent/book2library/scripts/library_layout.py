"""Every path in a study workspace, in one place."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tempfile

PLAN_FILE = "library-plan.json"
LIBRARY_DIR = "library"
WORK_DIR = ".work"


@dataclass(frozen=True)
class StudyLayout:
    root: Path

    @property
    def plan_file(self) -> Path:
        return self.root / PLAN_FILE

    @property
    def library(self) -> Path:
        return self.root / LIBRARY_DIR

    @property
    def library_skill(self) -> Path:
        return self.library / "SKILL.md"

    @property
    def catalog(self) -> Path:
        return self.library / "references" / "catalog.md"

    @property
    def statements(self) -> Path:
        return self.library / "references" / "statements.csv"

    @property
    def work(self) -> Path:
        return self.root / WORK_DIR

    def original(self, book_id: str) -> Path:
        return self.work / "originals" / f"{book_id}.pdf"

    def unit_pdf(self, book_id: str, unit_id: str) -> Path:
        return self.work / "unit-pdfs" / book_id / f"{unit_id}.pdf"

    def review_dir(self, book_id: str, unit_id: str) -> Path:
        return self.work / "review" / book_id / unit_id

    def source_marker(self, book_id: str, unit_id: str) -> Path:
        return self.work / "review" / book_id / f"{unit_id}.source.json"

    def unit_package(self, book_id: str, unit_id: str) -> Path:
        return self.library / "units" / book_id / unit_id

    def unit_text(self, book_id: str, unit_id: str) -> Path:
        return self.unit_package(book_id, unit_id) / "references" / "paper.md"

    def make_replaced_dir(self, book_id: str, unit_id: str) -> Path:
        """Create a new, uniquely named folder to hold a unit's retired review directory or package."""
        parent = self.work / "replaced" / book_id
        parent.mkdir(parents=True, exist_ok=True)
        return Path(tempfile.mkdtemp(prefix=f"{unit_id}-", dir=parent))

    def render(self, book_id: str, page: int, dpi: int) -> Path:
        return self.work / "renders" / book_id / f"page-{page:04d}-{dpi}dpi.png"

    def relative(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()
