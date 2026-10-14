"""Adjudicate verification diagnostics that come only from transcribing displayed formulas to LaTeX.

paper2skill compares the source PDF's native text and numbers with the reviewed output. A displayed formula
rewritten as LaTeX no longer matches its native text line by line, and LaTeX writes negative numbers with an
ASCII hyphen-minus where the PDF has a Unicode minus. An adjudication is recorded only when a diagnostic is
fully explained by those two causes:

- a missing line must lie inside a region the extractor itself classified as a formula (from the read-only
  evidence, not the editable page file), and its letters, digits and comparison or operator symbols
  (= < > ≤ ≥ ≠ ∈ ∉ ⊂ ⊆ ⊃ ⊇ ∪ ∩ + − ± × ∞ ∀ ∃) must appear in the same order in a LaTeX item on the same page;
- a number difference must vanish when the Unicode minus is read as a hyphen-minus.

What this cannot see: subscript and superscript placement, fonts, and symbols outside that set (dots, arrows,
brackets), because PDF text does not record them reliably. Those are left to the reviewer's and the verifier's
symbol-by-symbol check against the page image. Everything else is left for the reviewer. Adjudications made
stale by later edits are removed.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import json
from pathlib import Path
import re
import unicodedata

ADJUDICATION_SCHEMA = 1
UNICODE_MINUS, ASCII_MINUS = "−", "-"
FORMULA_BOX_PADDING = 6.0  # points; extractor boxes are slightly tighter than the rendered glyphs
LATEX_COMMAND = re.compile(r"\\([A-Za-z]+)")
LATEX_ENVIRONMENT = re.compile(r"\\(begin|end)\{[^}]*\}")
COMBINING_LONG_SOLIDUS = "\u0338"
NEGATED_SYMBOL = re.compile(COMBINING_LONG_SOLIDUS + r"\s*(\S)")  # TeX PDFs often write ≠ as "̸ ="
# Symbols compared besides letters and digits: each has one PDF character and one LaTeX command. Dots, arrows
# and brackets are left out because TeX fonts draw them from several glyphs.
COMPARED_SYMBOLS = frozenset("=<>≤≥≠∈∉⊂⊆⊃⊇∪∩+-±×∞∀∃")
LATEX_SYMBOLS = {
    "le": "≤", "leq": "≤", "ge": "≥", "geq": "≥", "ne": "≠", "neq": "≠", "in": "∈", "notin": "∉",
    "subset": "⊂", "subseteq": "⊆", "supset": "⊃", "supseteq": "⊇", "cup": "∪", "cap": "∩", "pm": "±",
    "times": "×", "infty": "∞", "forall": "∀", "exists": "∃",
}
GREEK_LETTERS = {
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε", "varepsilon": "ε", "zeta": "ζ",
    "eta": "η", "theta": "θ", "vartheta": "ϑ", "iota": "ι", "kappa": "κ", "lambda": "λ", "mu": "μ", "nu": "ν",
    "xi": "ξ", "pi": "π", "rho": "ρ", "varrho": "ϱ", "sigma": "σ", "tau": "τ", "upsilon": "υ", "phi": "φ",
    "varphi": "φ", "chi": "χ", "psi": "ψ", "omega": "ω", "Gamma": "Γ", "Delta": "Δ", "Theta": "Θ",
    "Lambda": "Λ", "Xi": "Ξ", "Pi": "Π", "Sigma": "Σ", "Upsilon": "Υ", "Phi": "Φ", "Psi": "Ψ", "Omega": "Ω",
    "ell": "ℓ",
}


@dataclass(frozen=True)
class Adjudication:
    page: int
    check: str
    fingerprint: str
    reason: str

    def as_json(self) -> dict:
        return {"page": self.page, "check": self.check, "fingerprint": self.fingerprint, "reason": self.reason}


@dataclass(frozen=True)
class Box:
    left: float
    top: float
    right: float
    bottom: float

    def contains_center_of(self, bbox: list[float]) -> bool:
        x, y = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
        return self.left <= x <= self.right and self.top <= y <= self.bottom


@dataclass(frozen=True)
class PageEvidence:
    """What the adjudicator may rely on for one page: extractor formula regions and the page's LaTeX items."""

    formula_boxes: list[Box]
    latex_keys: list[str]


def combine_negations(text: str) -> str:
    """Turn a combining long solidus followed by a symbol ("̸ =") into the negated symbol ("≠")."""
    return NEGATED_SYMBOL.sub(lambda match: unicodedata.normalize("NFC", match.group(1) + COMBINING_LONG_SOLIDUS), text)


def content_key(text: str) -> str:
    """Letters, digits and compared symbols, compatibility-normalised (ℝ -> R, ² -> 2) and case-folded."""
    normalized = unicodedata.normalize("NFKC", combine_negations(text)).casefold().replace(UNICODE_MINUS, ASCII_MINUS)
    return "".join(character for character in normalized if character.isalnum() or character in COMPARED_SYMBOLS)


def latex_symbol(command: str) -> str:
    return GREEK_LETTERS.get(command) or LATEX_SYMBOLS.get(command) or " "


def latex_as_text(latex: str) -> str:
    """Drop environment markers and command names, keep arguments, and write symbol commands as symbols."""
    without_environments = LATEX_ENVIRONMENT.sub(" ", latex)
    return LATEX_COMMAND.sub(lambda match: latex_symbol(match.group(1)), without_environments)


def load_evidence(document: Path, page_number: int) -> PageEvidence:
    evidence = json.loads((document / "evidence" / f"page-{page_number:04d}.json").read_text(encoding="utf-8"))
    boxes = [padded_box(box["bbox"]) for box in evidence.get("layout", {}).get("page_boxes", [])
             if box.get("class") == "formula"]
    page = json.loads((document / "pages" / f"page-{page_number:04d}.json").read_text(encoding="utf-8"))
    latex_keys = [content_key(latex_as_text(item.get("markdown", ""))) for item in page["items"]
                  if item.get("kind") == "text" and "$" in item.get("markdown", "")]
    return PageEvidence(boxes, latex_keys)


def padded_box(bbox: list[float]) -> Box:
    return Box(bbox[0] - FORMULA_BOX_PADDING, bbox[1] - FORMULA_BOX_PADDING,
               bbox[2] + FORMULA_BOX_PADDING, bbox[3] + FORMULA_BOX_PADDING)


def is_transcribed_formula_line(line: dict, evidence: PageEvidence) -> bool:
    inside_formula = any(box.contains_center_of(line["bbox"]) for box in evidence.formula_boxes)
    key = content_key(line["text"])
    return inside_formula and any(key in latex for latex in evidence.latex_keys)


def explain_missing_lines(record: dict, evidence: PageEvidence) -> str | None:
    missing = record.get("missing_lines", [])
    if not missing or not all(is_transcribed_formula_line(line, evidence) for line in missing):
        return None
    return (f"All {len(missing)} missing native-text lines lie in extractor-classified formula regions, and their "
            f"letters, digits and comparison or operator symbols appear in the same order in the page's LaTeX. "
            f"Sub/superscript placement and other symbols are not compared here; they were checked against the "
            f"page image in review (see page review notes).")


def normalized_minus(counts: dict) -> Counter:
    normalized: Counter = Counter()
    for token, count in counts.items():
        normalized[token.replace(UNICODE_MINUS, ASCII_MINUS)] += count
    return normalized


def explain_number_differences(differences: dict) -> str | None:
    missing, extra = differences.get("missing", {}), differences.get("extra", {})
    if not missing or normalized_minus(missing) != normalized_minus(extra):
        return None
    return ("Only the minus sign differs: the PDF uses a Unicode minus (U+2212); the LaTeX transcriptions use an "
            "ASCII hyphen-minus. Every number is otherwise identical.")


class MissingLinesCheck:
    def explain(self, record: dict, evidence: PageEvidence) -> str | None:
        return explain_missing_lines(record, evidence)


class NumberCheck:
    def __init__(self, key: str) -> None:
        self._key = key

    def explain(self, record: dict, evidence: PageEvidence) -> str | None:
        return explain_number_differences(record.get(self._key, {}))


CHECKS = {
    "missing_lines": MissingLinesCheck(),
    "number_differences": NumberCheck("number_differences"),
    "independent_parser_number_differences": NumberCheck("independent_parser_number_differences"),
}


def explanation(check: str, record: dict, evidence: PageEvidence) -> str | None:
    handler = CHECKS.get(check)
    return handler.explain(record, evidence) if handler else None


def classify_unresolved(document: Path) -> tuple[list[Adjudication], list[dict]]:
    """Split a document's unresolved diagnostics into mechanical adjudications and manual leftovers."""
    verification = json.loads((document / "verification.json").read_text(encoding="utf-8"))
    adjudications: list[Adjudication] = []
    manual: list[dict] = []
    for record in verification.get("pages", []):
        if not record.get("unresolved_checks"):
            continue
        evidence = load_evidence(document, record["page"])
        for check in record["unresolved_checks"]:
            reason = explanation(check["check"], record, evidence) if record.get("agent_reviewed") else None
            if reason:
                adjudications.append(Adjudication(record["page"], check["check"], check["fingerprint"], reason))
            else:
                manual.append({"page": record["page"], "check": check["check"]})
    return adjudications, manual


def stale_keys(document: Path) -> set[tuple]:
    verification = json.loads((document / "verification.json").read_text(encoding="utf-8"))
    stale = verification.get("stale_adjudications", [])
    return {(entry["page"], entry["check"], entry["fingerprint"]) for entry in stale}


def merge_adjudications(document: Path, new: list[Adjudication], stale: set[tuple]) -> list[dict]:
    """Drop stale entries, replace entries for the same page and check, keep the rest. Returns dropped entries."""
    path = document / "adjudications.json"
    existing = json.loads(path.read_text(encoding="utf-8"))["entries"] if path.is_file() else []
    replaced = {(entry.page, entry.check) for entry in new}
    dropped = [e for e in existing if (e["page"], e["check"], e["fingerprint"]) in stale]
    kept = [e for e in existing if e not in dropped and (e["page"], e["check"]) not in replaced]
    entries = sorted(kept + [entry.as_json() for entry in new], key=lambda e: (e["page"], e["check"]))
    if entries or path.is_file():
        path.write_text(json.dumps({"schema_version": ADJUDICATION_SCHEMA, "entries": entries}, indent=2) + "\n",
                        encoding="utf-8")
    return dropped


def adjudicate_review_dir(review_dir: Path) -> dict:
    applied, manual, removed = [], [], []
    for document in sorted(review_dir.glob("documents/*")):
        if not (document / "verification.json").is_file():
            continue
        adjudications, leftovers = classify_unresolved(document)
        dropped = merge_adjudications(document, adjudications, stale_keys(document))
        applied += [{"document": document.name, **a.as_json()} for a in adjudications]
        manual += [{"document": document.name, **item} for item in leftovers]
        removed += [{"document": document.name, **entry} for entry in dropped]
    next_step = ("Inspect the remaining diagnostics against the page images, fix or adjudicate them by hand, "
                 "then run finalize." if manual else "Run finalize again.")
    return {"adjudicated": applied, "removed_stale": removed, "needs_manual_review": manual, "next": next_step}
