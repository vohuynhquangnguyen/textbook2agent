#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["av==19.0.1", "pillow==12.3.0", "numpy==2.5.3", "scipy==1.18.1", "contourpy==1.4.0"]
# ///
"""Tests for the visualize component.

Unit tests need no Manim or LaTeX. The end-to-end render test runs only when TEXTBOOK2AGENT_RENDER_TESTS=1, because
it needs LaTeX, dvisvgm and (on Linux and macOS) the Cairo and Pango headers.
"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from PIL import Image

from caption_markup import unbreakable_lines
import render_scene as render

SCRIPTS = Path(__file__).resolve().parent
EXAMPLES = SCRIPTS.parent / "examples"
RENDER_TESTS_ENABLED = os.environ.get("TEXTBOOK2AGENT_RENDER_TESTS") == "1"
TEST_FPS = 10
TEST_SECONDS = 3


def load_example_quantities(folder: str):
    spec = importlib.util.spec_from_file_location(f"quantities_{folder.replace('-', '_')}",
                                                  EXAMPLES / folder / "quantities.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses look their module up while the module is executing
    spec.loader.exec_module(module)
    return module


def write_test_video(path: Path) -> None:
    """A short video whose frames get brighter, so the last frame is recognisable."""
    import av
    import numpy as np

    with av.open(str(path), mode="w") as container:
        stream = container.add_stream("libx264", rate=TEST_FPS)
        stream.width, stream.height, stream.pix_fmt = 64, 48, "yuv420p"
        for index in range(TEST_FPS * TEST_SECONDS):
            pixels = np.full((48, 64, 3), 5 * index, dtype=np.uint8)
            for packet in stream.encode(av.VideoFrame.from_ndarray(pixels, format="rgb24")):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)


class CommandTests(unittest.TestCase):
    def command(self) -> list[str]:
        return render.manim_command("python", Path("scene.py"), "Demo", "final", Path("media"))

    def test_quality_maps_to_manim_flag(self):
        self.assertIn("-qh", self.command())

    def test_sections_are_saved(self):
        self.assertIn("--save_sections", self.command())

    def test_scene_class_is_last(self):
        self.assertEqual(self.command()[-1], "Demo")

    def test_environment_exposes_scene_kit(self):
        paths = render.scene_environment(Path("/study/visuals/x/scene.py"))["PYTHONPATH"].split(os.pathsep)
        self.assertEqual(paths[:2], [str(render.KIT_DIRECTORY), str(Path("/study/visuals/x"))])


class SectionTests(unittest.TestCase):
    def test_label_numbers_and_slugs_the_name(self):
        self.assertEqual(render.Section(3, "Lower Bound!", Path("x.mp4"), 1.0).label, "03-lower-bound")

    def test_sections_are_read_from_manim_index(self):
        with tempfile.TemporaryDirectory() as directory:
            index = Path(directory) / "Demo.json"
            index.write_text(json.dumps([{"name": "intro", "video": "Demo_0000_intro.mp4", "duration": "2.5"}]))
            section = render.load_sections(index)[0]
            parsed = (section.name, section.video.name, section.duration)
            self.assertEqual(parsed, ("intro", "Demo_0000_intro.mp4", 2.5))

    def test_missing_index_is_a_render_error(self):
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(render.RenderError):
            render.find_sections_index(Path(directory), "Demo")


class FrameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._directory = tempfile.TemporaryDirectory()
        cls.video = Path(cls._directory.name) / "test.mp4"
        write_test_video(cls.video)
        cls.samples = render.sampled_frames(cls.video, 1.0)

    @classmethod
    def tearDownClass(cls):
        cls._directory.cleanup()

    def test_one_sample_per_second_plus_the_last_frame(self):
        self.assertEqual(len(self.samples), TEST_SECONDS + 1)

    def test_last_sample_is_the_final_frame(self):
        self.assertGreater(self.samples[-1][1].getpixel((0, 0))[0], self.samples[-2][1].getpixel((0, 0))[0])

    def test_contact_sheet_has_a_grid_of_thumbnails(self):
        frames = [Image.new("RGB", (128, 72)) for _ in range(4)]
        sheet = render.contact_sheet(frames, ["a", "b", "c", "d"])
        self.assertEqual(sheet.width, render.SHEET_COLUMNS * render.SHEET_THUMBNAIL_WIDTH)


class CaptionMarkupTests(unittest.TestCase):
    def test_each_explicit_line_is_boxed(self):
        self.assertEqual(unbreakable_lines(r"first part \\ second part"), r"\mbox{first part} \\ \mbox{second part}")

    def test_single_line_is_boxed_without_a_break(self):
        self.assertEqual(unbreakable_lines("$f\\notin L^1$"), r"\mbox{$f\notin L^1$}")


class ExampleClaimTests(unittest.TestCase):
    def test_sinc_claims_hold(self):
        checks = load_example_quantities("sinc-improper-integral").CHECKS
        self.assertEqual([claim for claim, check in checks.items() if not check()], [])

    def test_gauss_newton_claims_hold(self):
        checks = load_example_quantities("gauss-newton-linear-regression").CHECKS
        self.assertEqual([claim for claim, check in checks.items() if not check()], [])


TINY_SCENE = '''
from manim import Circle, Create
from scene_kit import StudyScene

class Tiny(StudyScene):
    def construct(self):
        self.beat("first", "First")
        self.play(Create(Circle()))
        self.say("A circle.", hold=0.2)
        self.continue_beat("second")
        self.say(r"Still $\\pi r^2$.", hold=0.2)
'''


@unittest.skipUnless(RENDER_TESTS_ENABLED, "set TEXTBOOK2AGENT_RENDER_TESTS=1 to render with Manim and LaTeX")
class RenderTests(unittest.TestCase):
    def test_render_writes_one_sheet_per_beat(self):
        with tempfile.TemporaryDirectory() as directory:
            scene = Path(directory) / "scene.py"
            scene.write_text(TINY_SCENE, encoding="utf-8")
            command = [shutil.which("uv") or "uv", "run", "-q", str(SCRIPTS / "render_scene.py"), str(scene), "Tiny",
                       "--quality", "preview", "--out", str(Path(directory) / "out")]
            completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
            manifest = json.loads(completed.stdout) if completed.returncode == 0 else {"error": completed.stderr}
            sheets = [Path(directory) / "out" / section["sheet"] for section in manifest.get("sections", [])]
            self.assertEqual([sheet.is_file() for sheet in sheets], [True, True], manifest.get("error", ""))


if __name__ == "__main__":
    sys.path.insert(0, str(SCRIPTS))
    unittest.main(verbosity=2)
