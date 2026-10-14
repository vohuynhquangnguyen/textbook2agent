#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml==6.0.3"]
# ///
"""Checks on the published skill folder: SKILL.md metadata, working relative links, and no book content."""

from __future__ import annotations

from pathlib import Path
import re
import unittest

import yaml

REPOSITORY = Path(__file__).resolve().parent.parent
SKILL = REPOSITORY / "skills" / "textbook2agent"
SKILL_NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MAX_NAME_CHARACTERS = 64
MAX_DESCRIPTION_CHARACTERS = 1024
MAX_UPLOAD_DESCRIPTION_CHARACTERS = 200  # Claude apps' limit for an uploaded skill
FRONTMATTER = re.compile(r"\A---\n(?P<yaml>.*?)\n---\n", re.DOTALL)
MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\((?P<target>[^)\s]+)\)")
# Generated into the learner's workspace, where its links resolve; not resolvable inside the skill folder.
GENERATED_TEMPLATES = {SKILL / "book2library" / "templates" / "library_skill.md"}
FORBIDDEN_SUFFIXES = {".pdf", ".djvu", ".epub"}
MAX_FILE_BYTES = 200_000


def skill_files() -> list[Path]:
    return sorted(path for path in SKILL.rglob("SKILL.md"))


def markdown_files() -> list[Path]:
    return sorted(path for path in SKILL.rglob("*.md") if path not in GENERATED_TEMPLATES)


def relative(path: Path) -> str:
    return path.relative_to(REPOSITORY).as_posix()


def frontmatter(path: Path) -> dict:
    match = FRONTMATTER.match(path.read_text(encoding="utf-8"))
    if match is None:
        raise AssertionError(f"{relative(path)} has no YAML frontmatter")
    return yaml.safe_load(match["yaml"])


def local_targets(path: Path) -> list[str]:
    text = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.DOTALL)
    targets = [match["target"].split("#")[0] for match in MARKDOWN_LINK.finditer(text)]
    return [target for target in targets if target and "://" not in target and not target.startswith("mailto:")]


def broken_links() -> list[str]:
    broken = []
    for path in markdown_files():
        for target in local_targets(path):
            if not (path.parent / target).exists():
                broken.append(f"{relative(path)} -> {target}")
    return broken


class TopLevelSkillTests(unittest.TestCase):
    def test_name_matches_folder(self):
        self.assertEqual(frontmatter(SKILL / "SKILL.md")["name"], SKILL.name)

    def test_description_fits_the_upload_limit(self):
        self.assertLessEqual(len(frontmatter(SKILL / "SKILL.md")["description"]), MAX_UPLOAD_DESCRIPTION_CHARACTERS)

    def test_name_is_a_valid_skill_name(self):
        name = frontmatter(SKILL / "SKILL.md")["name"]
        self.assertTrue(SKILL_NAME.match(name) and len(name) <= MAX_NAME_CHARACTERS)


class ComponentSkillTests(unittest.TestCase):
    def test_every_skill_file_has_a_valid_name(self):
        invalid = [relative(p) for p in skill_files() if not SKILL_NAME.match(frontmatter(p)["name"])]
        self.assertEqual(invalid, [])

    def test_every_description_fits_the_limit(self):
        too_long = [relative(p) for p in skill_files()
                    if not 0 < len(frontmatter(p)["description"]) <= MAX_DESCRIPTION_CHARACTERS]
        self.assertEqual(too_long, [])

    def test_no_description_contains_angle_brackets(self):
        bracketed = [relative(p) for p in skill_files() if re.search("[<>]", frontmatter(p)["description"])]
        self.assertEqual(bracketed, [])


class LinkTests(unittest.TestCase):
    def test_relative_links_resolve(self):
        self.assertEqual(broken_links(), [])

    def test_repository_documents_link_to_existing_files(self):
        broken = [f"{name} -> {target}" for name in ("README.md", "CONTRIBUTING.md", "THIRD_PARTY_NOTICES.md")
                  for target in local_targets(REPOSITORY / name) if not (REPOSITORY / target).exists()]
        self.assertEqual(broken, [])


class ContentTests(unittest.TestCase):
    def test_no_book_files_are_packaged(self):
        books = [relative(p) for p in REPOSITORY.rglob("*")
                 if p.suffix.lower() in FORBIDDEN_SUFFIXES and ".git" not in p.parts]
        self.assertEqual(books, [])

    def test_no_large_files_are_packaged(self):
        large = [relative(p) for p in SKILL.rglob("*") if p.is_file() and p.stat().st_size > MAX_FILE_BYTES]
        self.assertEqual(large, [])

    def test_vendored_engine_keeps_its_license(self):
        self.assertTrue((SKILL / "book2library" / "scripts" / "paper2skill" / "LICENSE").is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
