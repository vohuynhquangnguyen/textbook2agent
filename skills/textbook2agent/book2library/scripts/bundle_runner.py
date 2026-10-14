"""Drive the vendored paper2skill engine (paper_bundle.py) through its supported command-line interface."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
import sys

PAPER_BUNDLE = Path(__file__).resolve().parent / "paper2skill" / "paper_bundle.py"
STRICT_PENDING_EXIT = 2
STDERR_TAIL_CHARACTERS = 2000
UTF8_CHILD_ENVIRONMENT = {"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}  # Windows pipes default to a code page
TIERS_BY_STATUS = {
    "planned": "planned",
    "unreviewed": "draft",
    "unresolved_discrepancies": "draft",
    "mechanical_failure": "broken",
    "reviewed": "reviewed",
    "reviewed_with_limitations": "reviewed",
}
REVIEWED_STATUSES = {"reviewed", "reviewed_with_limitations"}


class BundleError(RuntimeError):
    """paper_bundle.py failed; the message carries the end of its stderr."""


@dataclass(frozen=True)
class BundleResult:
    exit_code: int
    report: dict

    @property
    def status(self) -> str:
        return self.report.get("status", "unknown")


class PaperBundle:
    """One paper2skill review directory, i.e. one study unit."""

    def __init__(self, work: Path, python: str = sys.executable, script: Path = PAPER_BUNDLE) -> None:
        self.work = work
        self._python = python
        self._script = script

    def prepare(self, unit_pdf: Path, name: str, title: str) -> BundleResult:
        return self._run("prepare", str(unit_pdf), "--work", str(self.work), "--name", name, "--title", title)

    def extract(self, ocr: str) -> BundleResult:
        return self._run("extract", "--work", str(self.work), "--ocr", ocr)

    def review_aid(self) -> BundleResult:
        return self._run("review-aid", "--work", str(self.work))

    def build_draft(self, output: Path) -> BundleResult:
        return self._run("build", "--work", str(self.work), "--output", str(output), "--draft")

    def build_reviewed(self, output: Path) -> BundleResult:
        return self._run("build", "--work", str(self.work), "--output", str(output), "--require-reviewed")

    def verify_strict(self) -> BundleResult:
        return self._run("verify", "--work", str(self.work), "--strict", accepted_exit_codes=(0, STRICT_PENDING_EXIT))

    def recorded_status(self) -> str:
        """Status from the latest build's verification, or 'planned' when never built."""
        verification = self.work / "verification.json"
        if not verification.is_file():
            return "planned"
        return json.loads(verification.read_text(encoding="utf-8")).get("status", "unknown")

    def tier(self) -> str:
        status = self.recorded_status()
        return TIERS_BY_STATUS.get(status, status)

    def is_prepared(self) -> bool:
        return (self.work / "bundle.json").is_file()

    def _run(self, *arguments: str, accepted_exit_codes: tuple[int, ...] = (0,)) -> BundleResult:
        completed = subprocess.run(
            [self._python, str(self._script), *arguments],
            capture_output=True, text=True, encoding="utf-8", env={**os.environ, **UTF8_CHILD_ENVIRONMENT},
        )
        if completed.returncode not in accepted_exit_codes:
            stderr_tail = completed.stderr.strip()[-STDERR_TAIL_CHARACTERS:]
            raise BundleError(f"paper_bundle {arguments[0]} failed: {stderr_tail}")
        return BundleResult(completed.returncode, json.loads(completed.stdout))
