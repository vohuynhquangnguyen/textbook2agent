#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pymupdf==1.28.2", "pymupdf4llm==1.28.2", "pypdf==6.18.1", "pillow==12.2.0"]
# ///
"""Tests for the textbook library: outline planning (pure) and the full pipeline on a synthetic book."""

from __future__ import annotations

import contextlib
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest

import pymupdf

from catalog_writer import (Statement, StatementScanner, compile_statement_patterns, first_statement_match,
                            numbering_gaps)
from library_plan import Book, LibraryPlan, DEFAULT_STATEMENT_PATTERNS, load_plan, save_plan
import textbook_library
from transcription_adjudicator import (Adjudication, Box, PageEvidence, classify_unresolved, content_key,
                                      is_transcribed_formula_line, latex_as_text, merge_adjudications)
from unit_planner import OutlineEntry, Unit, propose_units, validate_units

NUMBERED_OUTLINE = [
    OutlineEntry(1, "Preface", 3),
    OutlineEntry(1, "Part I Foundations", 5),
    OutlineEntry(2, "1 Sets", 6),
    OutlineEntry(3, "1.1 Unions", 7),
    OutlineEntry(2, "Exercises", 9),
    OutlineEntry(2, "2 Measures", 10),
    OutlineEntry(2, "A Background", 14),
    OutlineEntry(2, "Solutions to Exercises", 16),
    OutlineEntry(2, "References", 18),
    OutlineEntry(2, "Index", 19),
]
NUMBERED_PAGES = 20


def proposal_units() -> dict[str, Unit]:
    return {unit.id: unit for unit in propose_units(NUMBERED_OUTLINE, NUMBERED_PAGES).units}


class NumberedOutlineTests(unittest.TestCase):
    def test_unit_ids_follow_book_structure(self):
        expected = ["front", "ch01", "ch02", "app-a", "solutions", "back-references", "back-index"]
        self.assertEqual(list(proposal_units()), expected)

    def test_part_divider_page_starts_the_following_chapter(self):
        self.assertEqual(proposal_units()["ch01"].first_page, 5)

    def test_unnumbered_exercises_stay_inside_their_chapter(self):
        self.assertEqual(proposal_units()["ch01"].last_page, 9)

    def test_front_matter_covers_pages_before_first_chapter(self):
        self.assertEqual((proposal_units()["front"].first_page, proposal_units()["front"].last_page), (1, 4))

    def test_solutions_unit_is_marked(self):
        self.assertEqual(proposal_units()["solutions"].kind, "solutions")

    def test_back_matter_runs_to_last_page(self):
        self.assertEqual(proposal_units()["back-index"].last_page, NUMBERED_PAGES)

    def test_sections_attach_to_their_chapter(self):
        self.assertEqual([s.title for s in proposal_units()["ch01"].sections], ["1.1 Unions", "Exercises"])

    def test_proposal_is_valid(self):
        self.assertEqual(validate_units(list(proposal_units().values()), NUMBERED_PAGES), [])


class FallbackOutlineTests(unittest.TestCase):
    def test_unnumbered_top_level_entries_become_chapters(self):
        outline = [OutlineEntry(1, "Preface", 2), OutlineEntry(1, "Sets", 4), OutlineEntry(1, "Measures", 8),
                   OutlineEntry(1, "Integration", 12), OutlineEntry(1, "Index", 15)]
        kinds = [unit.kind for unit in propose_units(outline, 16).units]
        self.assertEqual(kinds, ["front", "chapter", "chapter", "chapter", "back"])

    def test_unnumbered_fallback_warns(self):
        outline = [OutlineEntry(1, "Sets", 1), OutlineEntry(1, "Measures", 5), OutlineEntry(1, "Integration", 9)]
        self.assertTrue(propose_units(outline, 12).warnings)

    def test_missing_outline_yields_whole_book_unit(self):
        self.assertEqual([unit.id for unit in propose_units([], 30).units], ["whole"])


class PlannerEdgeCaseTests(unittest.TestCase):
    def kinds(self, outline, pages):
        return {unit.title: unit.kind for unit in propose_units(outline, pages).units}

    def test_appendix_word_title_is_an_appendix(self):
        outline = [OutlineEntry(1, "1 Sets", 1), OutlineEntry(1, "2 Measures", 5),
                   OutlineEntry(1, "Appendix A Review", 9)]
        self.assertEqual(self.kinds(outline, 12)["Appendix A Review"], "appendix")

    def test_numbered_chapter_about_solutions_stays_a_chapter(self):
        outline = [OutlineEntry(1, "1 Preliminaries", 1), OutlineEntry(1, "2 Solutions of Equations", 5),
                   OutlineEntry(1, "3 Interpolation", 9)]
        self.assertEqual(self.kinds(outline, 12)["2 Solutions of Equations"], "chapter")

    def test_section_numbers_are_not_chapter_numbers(self):
        outline = [OutlineEntry(1, "Sets", 1), OutlineEntry(2, "1.1 Unions", 2), OutlineEntry(2, "1.2 Products", 3),
                   OutlineEntry(1, "Measures", 5), OutlineEntry(1, "Integration", 9)]
        self.assertEqual([unit.title for unit in propose_units(outline, 12).units], ["Sets", "Measures", "Integration"])

    def test_outline_out_of_page_order_is_sorted(self):
        outline = [OutlineEntry(1, "Index", 11), OutlineEntry(1, "1 Sets", 1), OutlineEntry(1, "2 Measures", 5)]
        self.assertEqual([unit.id for unit in propose_units(outline, 12).units], ["ch01", "ch02", "back-index"])

    def test_preface_before_first_chapter_is_not_a_divider(self):
        outline = [OutlineEntry(1, "Preface", 2), OutlineEntry(2, "1 Sets", 4), OutlineEntry(2, "2 Measures", 8)]
        self.assertEqual(propose_units(outline, 12).units[1].first_page, 4)

    def test_symbol_list_in_front_matter_stays_front_matter(self):
        outline = [OutlineEntry(1, "List of Symbols", 2), OutlineEntry(1, "1 Sets", 4),
                   OutlineEntry(1, "2 Measures", 8)]
        self.assertEqual([unit.id for unit in propose_units(outline, 12).units], ["front", "ch01", "ch02"])


class ValidationTests(unittest.TestCase):
    def test_gap_between_units_is_reported(self):
        units = [Unit("ch01", "chapter", "1", 1, 4), Unit("ch02", "chapter", "2", 6, 10)]
        self.assertIn("ch02: starts at page 6, expected 5 (gap or overlap)", validate_units(units, 10))

    def test_duplicate_unit_id_is_reported(self):
        units = [Unit("ch01", "chapter", "1", 1, 4), Unit("ch01", "chapter", "2", 5, 10)]
        self.assertIn("ch01: duplicate unit id", validate_units(units, 10))

    def test_uncovered_tail_is_reported(self):
        units = [Unit("ch01", "chapter", "1", 1, 4)]
        self.assertIn("units end at page 4, but the book has 10 pages", validate_units(units, 10))

    def test_unknown_kind_is_reported(self):
        units = [Unit("ch01", "lecture", "1", 1, 10)]
        self.assertTrue(any("kind 'lecture'" in issue for issue in validate_units(units, 10)))


def sample_book(statement_patterns: list[str]) -> Book:
    return Book("demo", "Demo", "A. Author", ".work/originals/demo.pdf", "0" * 64, 10,
                [Unit("ch01", "chapter", "1 Demo", 1, 10)], 1, statement_patterns=statement_patterns)


class PlanTests(unittest.TestCase):
    def test_plan_round_trips_through_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "library-plan.json"
            save_plan(LibraryPlan([sample_book([])]), path)
            self.assertEqual(load_plan(path).books[0], sample_book([]))

    def test_empty_statement_patterns_mean_defaults(self):
        self.assertEqual(sample_book([]).active_statement_patterns, list(DEFAULT_STATEMENT_PATTERNS))

    def test_pattern_without_named_groups_is_reported(self):
        self.assertTrue(any("named groups" in issue for issue in sample_book([r"^Def"]).issues()))


def default_match(text: str):
    match = first_statement_match(text, compile_statement_patterns(list(DEFAULT_STATEMENT_PATTERNS)))
    return (match["kind"].lower(), match["number"]) if match else None


class StatementPatternTests(unittest.TestCase):
    def test_named_statement_matches(self):
        self.assertEqual(default_match("Definition 2.1 (Matrix). With m, n"), ("definition", "2.1"))

    def test_statement_ending_with_period_keeps_full_number(self):
        self.assertEqual(default_match("Theorem 4.1. For any square matrix"), ("theorem", "4.1"))

    def test_statement_followed_by_capitalised_text_matches(self):
        self.assertEqual(default_match("Theorem 2.17 Let V and W be"), ("theorem", "2.17"))

    def test_paragraph_starting_with_a_reference_is_ignored(self):
        self.assertIsNone(default_match("Theorem 2.17 states that there exists a linear mapping"))

    def test_number_first_style_matches(self):
        self.assertEqual(default_match("2.7 Definition outer measure"), ("definition", "2.7"))

    def test_section_heading_is_not_a_problem_statement(self):
        self.assertIsNone(default_match("9.1 Problem Formulation"))


def page_of(*items) -> dict:
    return {"page": 1, "items": [{"kind": kind, "markdown": markdown} for kind, markdown in items]}


class StatementScannerTests(unittest.TestCase):
    def scan(self, *items):
        scanner = StatementScanner(compile_statement_patterns(list(DEFAULT_STATEMENT_PATTERNS)), "2 Linear Algebra")
        return [(f.section, f.kind, f.number) for f in scanner.scan([page_of(*items)])]

    def test_numbered_paragraph_under_exercises_heading_is_an_exercise(self):
        found = self.scan(("heading", "# **Exercises**"), ("text", "2.12 Consider two subspaces of R4"))
        self.assertEqual(found, [("Exercises", "exercise", "2.12")])

    def test_numbered_paragraph_outside_exercises_is_ignored(self):
        self.assertEqual(self.scan(("heading", "## 2.1 Systems"), ("text", "2 x1 + 3 x3 = 5 is a contradiction")), [])

    def test_exercise_heading_prefix_joins_bare_numbers(self):
        found = self.scan(("heading", "## Exercises 2A"), ("text", "4 Prove that every countable set is null."))
        self.assertEqual(found, [("Exercises 2A", "exercise", "2A.4")])

    def test_statement_records_its_section(self):
        found = self.scan(("heading", "## 2.2 Matrices"), ("text", "**Definition 2.1** (Matrix)."))
        self.assertEqual(found, [("2.2 Matrices", "definition", "2.1")])


def statement(kind: str, number: str, section: str = "") -> Statement:
    return Statement("mml", "ch02", section, kind, number, "1", 1, "draft", "")


class NumberingGapTests(unittest.TestCase):
    def test_missing_number_in_dense_sequence_is_reported(self):
        statements = [statement("definition", f"2.{n}") for n in (1, 2, 3, 5)]
        self.assertEqual(numbering_gaps(statements), ["- `mml` definition: 2.4"])

    def test_number_used_by_another_kind_is_not_a_gap(self):
        statements = [statement("definition", f"2.{n}") for n in (1, 2, 3, 5)] + [statement("theorem", "2.4")]
        self.assertEqual(numbering_gaps(statements), [])

    def test_sparse_sequence_is_not_reported(self):
        self.assertEqual(numbering_gaps([statement("theorem", "2.1"), statement("theorem", "2.9")]), [])


# Synthetic book: roman-numbered front matter, two chapters with a part divider, an index.
SYNTHETIC_PAGES = [
    "Synthetic Analysis Text",
    "Contents",
    "Part I Measure",
    "Chapter 1 Outer Measure",
    "Definition 1.1 (Outer measure). The outer measure of a set A is the infimum of total interval lengths.",
    "Theorem 1.2 (Countable subadditivity). Outer measure is countably subadditive.",
    "Chapter 2 Measurable Spaces",
    "Definition 2.1 (Sigma-algebra). A collection of subsets closed under complements and countable unions.",
    "Index",
]
SYNTHETIC_TOC = [[1, "Contents", 2], [1, "Part I Measure", 3], [2, "1 Outer Measure", 4],
                 [2, "2 Measurable Spaces", 7], [2, "Index", 9]]


def write_synthetic_book(path: Path) -> None:
    document = pymupdf.open()
    for text in SYNTHETIC_PAGES:
        document.new_page().insert_text((72, 100), text, fontsize=11)
    document.set_toc(SYNTHETIC_TOC)
    document.set_page_labels([{"startpage": 0, "prefix": "", "style": "r", "firstpagenum": 1},
                              {"startpage": 2, "prefix": "", "style": "D", "firstpagenum": 1}])
    document.save(path)


def run_cli(*arguments: str) -> tuple[int, dict]:
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        exit_code = textbook_library.main(list(arguments))
    return exit_code, json.loads(stdout.getvalue()) if stdout.getvalue() else {"stderr": stderr.getvalue()}


class PipelineTests(unittest.TestCase):
    """Runs add -> ingest once on a synthetic book; each test checks one outcome."""

    @classmethod
    def setUpClass(cls):
        cls._directory = tempfile.TemporaryDirectory()
        base = Path(cls._directory.name)
        cls.root = str(base / "study")
        write_synthetic_book(base / "synthetic.pdf")
        cls.add_result = run_cli("add", str(base / "synthetic.pdf"), "--id", "synth", "--root", cls.root)
        cls.ingest_result = run_cli("ingest", "--root", cls.root, "--ocr", "never")
        with (Path(cls.root) / "library/references/statements.csv").open(encoding="utf-8") as stream:
            cls.statements = list(csv.DictReader(stream))

    @classmethod
    def tearDownClass(cls):
        cls._directory.cleanup()

    def unit_tiers(self) -> dict[str, str]:
        return {unit["unit"]: unit["tier"] for unit in run_cli("status", "--root", self.root)[1]["units"]}

    def test_add_proposes_units_from_outline(self):
        self.assertEqual(self.add_result[1]["added"][0]["units"], ["front", "ch01", "ch02", "back-index"])

    def test_ingest_builds_draft_packages(self):
        self.assertEqual(set(self.unit_tiers().values()), {"draft"})

    def test_statement_found_with_printed_page(self):
        row = next(r for r in self.statements if r["kind"] == "definition" and r["number"] == "2.1")
        self.assertEqual((row["unit"], row["printed_page"], row["pdf_page"]), ("ch02", "6", "8"))

    def test_theorem_is_indexed(self):
        self.assertTrue(any(r["kind"] == "theorem" and r["number"] == "1.2" for r in self.statements))

    def test_catalog_links_unit_text(self):
        catalog = (Path(self.root) / "library/references/catalog.md").read_text(encoding="utf-8")
        self.assertIn("../units/synth/ch01/references/paper.md", catalog)

    def test_library_skill_names_the_workspace(self):
        skill = (Path(self.root) / "library/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("name: study-library", skill)

    def test_locate_reports_printed_page_and_unit(self):
        hit = run_cli("locate", "--root", self.root, "--book", "synth", "countably subadditive")[1]["hits"][0]
        self.assertEqual((hit["printed_page"], hit["unit"]), ("4", "ch01"))

    def test_render_by_printed_label_writes_png(self):
        result = run_cli("render", "--root", self.root, "--book", "synth", "--label", "ii", "--dpi", "72")[1]
        self.assertTrue(Path(result["image"]).is_file())

    def test_library_skill_description_is_quoted_yaml(self):
        skill = (Path(self.root) / "library/SKILL.md").read_text(encoding="utf-8")
        description = next(line for line in skill.splitlines() if line.startswith("description: "))
        self.assertTrue(json.loads(description.removeprefix("description: ")).startswith("Searchable"))


class SyntheticWorkspace:
    """A fresh workspace with the synthetic book added and the given units ingested."""

    def __init__(self, *units: str) -> None:
        self._directory = tempfile.TemporaryDirectory()
        base = Path(self._directory.name)
        self.root = str(base / "study")
        self.pdf = base / "synthetic.pdf"
        write_synthetic_book(self.pdf)
        run_cli("add", str(self.pdf), "--id", "synth", "--root", self.root)
        unit_options = [option for unit in units for option in ("--unit", unit)]
        run_cli("ingest", "--root", self.root, "--book", "synth", *unit_options, "--ocr", "never")

    def close(self) -> None:
        self._directory.cleanup()


class FinalizeTests(unittest.TestCase):
    def setUp(self):
        self.workspace = SyntheticWorkspace("ch02")
        self.result = run_cli("finalize", "--root", self.workspace.root, "--book", "synth", "--unit", "ch02")

    def tearDown(self):
        self.workspace.close()

    def test_finalize_explains_that_review_is_missing(self):
        self.assertIn("not been reviewed", self.result[1]["stderr"])

    def test_failed_finalize_keeps_draft_package(self):
        self.assertTrue((Path(self.workspace.root) / "library/units/synth/ch02/references/paper.md").is_file())


class ReplanTests(unittest.TestCase):
    def setUp(self):
        self.workspace = SyntheticWorkspace("ch01", "ch02")
        move_boundary(Path(self.workspace.root) / "library-plan.json", earlier_unit="ch01", later_unit="ch02")

    def tearDown(self):
        self.workspace.close()

    def test_check_reports_both_units_around_a_moved_boundary(self):
        issues = run_cli("check", "--root", self.workspace.root)[1]["issues"]
        self.assertEqual(sorted(issue.split(":")[0] for issue in issues), ["synth/ch01", "synth/ch02"])

    def test_ingest_of_one_unit_restarts_its_stale_neighbour_too(self):
        result = run_cli("ingest", "--root", self.workspace.root, "--book", "synth", "--unit", "ch01", "--ocr", "never")
        self.assertEqual(result[1]["restarted"], ["synth/ch01", "synth/ch02"])

    def test_ingest_of_one_unit_rebuilds_its_stale_neighbour(self):
        run_cli("ingest", "--root", self.workspace.root, "--book", "synth", "--unit", "ch01", "--ocr", "never")
        tiers = {u["unit"]: u["tier"] for u in run_cli("status", "--root", self.workspace.root)[1]["units"]}
        self.assertEqual(tiers["ch02"], "draft")

    def test_finalize_refuses_a_stale_unit(self):
        result = run_cli("finalize", "--root", self.workspace.root, "--book", "synth", "--unit", "ch02")
        self.assertIn("pages changed since extraction", result[1]["stderr"])


class AddValidationTests(unittest.TestCase):
    def test_invalid_book_id_is_refused_before_copying(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            write_synthetic_book(base / "synthetic.pdf")
            run_cli("add", str(base / "synthetic.pdf"), "--id", "../escape", "--root", str(base / "study"))
            self.assertFalse((base / "study" / ".work").exists())

    def test_missing_pdf_is_a_clean_error(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_cli("add", str(Path(directory) / "missing.pdf"), "--root", str(Path(directory) / "study"))
            self.assertIn("cannot open PDF", result[1]["stderr"])

    def test_commands_need_an_existing_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_cli("status", "--root", str(Path(directory) / "typo"))
            self.assertIn("no library-plan.json", result[1]["stderr"])


def move_boundary(plan_path: Path, earlier_unit: str, later_unit: str) -> None:
    """Give the later unit's first page to the earlier unit."""
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    units = {unit["id"]: unit for unit in plan["books"][0]["units"]}
    units[earlier_unit]["last_page"] += 1
    units[later_unit]["first_page"] += 1
    plan_path.write_text(json.dumps(plan), encoding="utf-8")


FORMULA_ITEM = {"id": "p0001-b002", "kind": "text", "source_class": "formula", "bbox": [100, 100, 400, 150],
                "markdown": "$$a_{ij} \\in \\mathbb{R}. \\tag{2.11}$$"}
PROSE_ITEM = {"id": "p0001-b003", "kind": "text", "source_class": "formula", "bbox": [100, 160, 400, 200],
              "markdown": "$x$ the mean and median are always equal"}
EXTRACTOR_FORMULA_BOXES = [{"class": "formula", "bbox": [105, 105, 395, 145]},
                           {"class": "formula", "bbox": [105, 165, 395, 195]}]
FORMULA_LINE = {"text": "aij ∈R . (2.11)", "bbox": [200, 120, 260, 130]}
CHANGED_PROSE_LINE = {"text": "the mean and median can be different", "bbox": [120, 170, 380, 180]}
OUTSIDE_LINE = {"text": "a body line", "bbox": [100, 300, 400, 310]}


def write_document(directory: Path, missing_lines: list[dict], numbers: dict, checks: list[str],
                   stale: list[dict] = ()) -> Path:
    document = directory / "documents" / "s001-unit"
    (document / "pages").mkdir(parents=True)
    (document / "evidence").mkdir()
    page = {"page": 1, "items": [FORMULA_ITEM, PROSE_ITEM]}
    (document / "pages" / "page-0001.json").write_text(json.dumps(page), encoding="utf-8")
    evidence = {"page": 1, "lines": [], "layout": {"page_boxes": EXTRACTOR_FORMULA_BOXES}}
    (document / "evidence" / "page-0001.json").write_text(json.dumps(evidence), encoding="utf-8")
    record = {"page": 1, "agent_reviewed": True, "missing_lines": missing_lines, "number_differences": numbers,
              "unresolved_checks": [{"check": check, "fingerprint": f"fp-{check}"} for check in checks]}
    verification = {"pages": [record], "stale_adjudications": list(stale)}
    (document / "verification.json").write_text(json.dumps(verification), encoding="utf-8")
    return document


def adjudication_entry(page: int, fingerprint: str) -> dict:
    return {"page": page, "check": "missing_lines", "fingerprint": fingerprint, "reason": "r"}


def transcription_matches(native_line: str, latex: str) -> bool:
    evidence = PageEvidence([Box(0, 0, 500, 500)], [content_key(latex_as_text(latex))])
    return is_transcribed_formula_line({"text": native_line, "bbox": [10, 10, 100, 20]}, evidence)


class AdjudicatorTests(unittest.TestCase):
    def classify(self, missing_lines, numbers, checks):
        with tempfile.TemporaryDirectory() as directory:
            return classify_unresolved(write_document(Path(directory), missing_lines, numbers, checks))

    def test_formula_line_matching_its_transcription_is_adjudicated(self):
        adjudications, _ = self.classify([FORMULA_LINE], {}, ["missing_lines"])
        self.assertEqual([a.check for a in adjudications], ["missing_lines"])

    def test_changed_prose_inside_a_formula_region_needs_manual_review(self):
        _, manual = self.classify([CHANGED_PROSE_LINE], {}, ["missing_lines"])
        self.assertEqual(manual, [{"page": 1, "check": "missing_lines"}])

    def test_line_outside_formula_regions_needs_manual_review(self):
        _, manual = self.classify([FORMULA_LINE, OUTSIDE_LINE], {}, ["missing_lines"])
        self.assertEqual(manual, [{"page": 1, "check": "missing_lines"}])

    def test_negated_relation_is_not_adjudicated(self):
        self.assertFalse(transcription_matches("x ∈ A", r"$$x \notin A$$"))

    def test_reversed_inequality_is_not_adjudicated(self):
        self.assertFalse(transcription_matches("f(x) ≤ g(x) + 1", r"$$f(x) \ge g(x) + 1$$"))

    def test_changed_operator_is_not_adjudicated(self):
        self.assertFalse(transcription_matches("f(x) ≤ g(x) + 1", r"$$f(x) \le g(x) - 1$$"))

    def test_pdf_not_equal_glyphs_match_latex_neq(self):
        self.assertTrue(transcription_matches("m\u0338 = n", r"$$m \neq n$$"))

    def test_unicode_minus_only_difference_is_adjudicated(self):
        numbers = {"missing": {"\u22121": 2}, "extra": {"-1": 2}}
        adjudications, _ = self.classify([], numbers, ["number_differences"])
        self.assertEqual(len(adjudications), 1)

    def test_real_number_difference_needs_manual_review(self):
        numbers = {"missing": {"\u22121": 1}, "extra": {"-7": 1}}
        _, manual = self.classify([], numbers, ["number_differences"])
        self.assertEqual(manual, [{"page": 1, "check": "number_differences"}])

    def test_merge_replaces_same_check_and_keeps_others(self):
        with tempfile.TemporaryDirectory() as directory:
            document = Path(directory)
            old = {"schema_version": 1, "entries": [adjudication_entry(1, "old"), adjudication_entry(2, "keep")]}
            (document / "adjudications.json").write_text(json.dumps(old), encoding="utf-8")
            merge_adjudications(document, [Adjudication(1, "missing_lines", "new", "r")], set())
            entries = json.loads((document / "adjudications.json").read_text(encoding="utf-8"))["entries"]
            self.assertEqual([e["fingerprint"] for e in entries], ["new", "keep"])

    def test_stale_adjudications_are_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            document = Path(directory)
            old = {"schema_version": 1, "entries": [adjudication_entry(3, "gone")]}
            (document / "adjudications.json").write_text(json.dumps(old), encoding="utf-8")
            merge_adjudications(document, [], {(3, "missing_lines", "gone")})
            entries = json.loads((document / "adjudications.json").read_text(encoding="utf-8"))["entries"]
            self.assertEqual(entries, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
