#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["manim==0.21.0", "numpy==2.5.3", "scipy==1.18.1", "contourpy==1.4.0"]
# ///
"""Render a Manim study scene and collect what a reviewer needs.

Usage: render_scene.py SCENE_FILE SCENE_CLASS [--quality preview|draft|final|4k] [--out DIR]

Writes to DIR (default: a `render/<quality>` folder next to the scene file):
  <SceneClass>.mp4              the whole animation
  sections/NN-<beat>.mp4        one video per beat (StudyScene.beat / Manim section), to release beats one at a time
  frames/NN-<beat>.png          the last frame of each beat
  frames/NN-<beat>-sheet.png    frames every SAMPLE_INTERVAL seconds through the beat, for review
  contact-sheet.png             the last frame of every beat on one image
  manifest.json                 paths and durations
Prints the manifest as JSON. Exit codes: 0 success, 1 error.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

KIT_DIRECTORY = Path(__file__).resolve().parent
QUALITY_FLAGS = {"preview": "l", "draft": "m", "final": "h", "4k": "k"}
STDERR_TAIL_CHARACTERS = 3000
SAMPLE_INTERVAL_SECONDS = 2.0
SHEET_COLUMNS = 3
SHEET_THUMBNAIL_WIDTH = 640
SHEET_LABEL_HEIGHT = 28
SHEET_BACKGROUND = (24, 24, 24)
SHEET_LABEL_COLOUR = (230, 230, 230)


class RenderError(Exception):
    """Reported to the user as one message with exit code 1."""


@dataclass(frozen=True)
class Section:
    number: int
    name: str
    video: Path
    duration: float

    @property
    def label(self) -> str:
        return f"{self.number:02d}-{slug(self.name)}"


@dataclass(frozen=True)
class SectionRecord:
    name: str
    video: str
    frame: str
    sheet: str
    duration: float


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "section"


def manim_command(python: str, scene_file: Path, scene_class: str, quality: str, media_dir: Path) -> list[str]:
    return [python, "-m", "manim", "render", f"-q{QUALITY_FLAGS[quality]}", "--save_sections",
            "--media_dir", str(media_dir), str(scene_file), scene_class]


def scene_environment(scene_file: Path) -> dict[str, str]:
    """Let the scene import scene_kit and modules next to it (such as its numbers module)."""
    paths = [str(KIT_DIRECTORY), str(scene_file.parent)]
    existing = os.environ.get("PYTHONPATH")
    if existing:
        paths.append(existing)
    return {**os.environ, "PYTHONPATH": os.pathsep.join(paths), "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}


def run_manim(command: list[str], environment: dict[str, str]) -> None:
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", env=environment)
    if completed.returncode != 0:
        output = (completed.stdout + completed.stderr).strip()[-STDERR_TAIL_CHARACTERS:]
        raise RenderError(f"Manim failed:\n{output}")


def find_sections_index(media_dir: Path, scene_class: str) -> Path:
    indexes = list(media_dir.glob(f"videos/*/*/sections/{scene_class}.json"))
    if not indexes:
        raise RenderError(f"Manim produced no section index for {scene_class} under {media_dir}")
    return max(indexes, key=lambda path: path.stat().st_mtime)


def load_sections(index: Path) -> list[Section]:
    entries = json.loads(index.read_text(encoding="utf-8"))
    return [Section(number, entry["name"], index.parent / entry["video"], float(entry["duration"]))
            for number, entry in enumerate(entries, start=1)]


def full_video(index: Path, scene_class: str) -> Path:
    video = index.parent.parent / f"{scene_class}.mp4"
    if not video.is_file():
        raise RenderError(f"Manim produced no video at {video}")
    return video


def sampled_frames(video: Path, interval: float) -> list[tuple[float, object]]:
    """(time, PIL image) every `interval` seconds from the start, always ending with the final frame."""
    import av

    samples, latest, next_time = [], None, 0.0
    with av.open(str(video)) as container:
        for latest in container.decode(video=0):
            if latest.time is not None and latest.time >= next_time:
                samples.append((latest.time, latest.to_image()))
                next_time += interval
    if latest is None:
        raise RenderError(f"{video} contains no frames")
    if samples[-1][0] != latest.time:
        samples.append((latest.time, latest.to_image()))
    return samples


def contact_sheet(frames: list, labels: list[str]):
    """Key frames in a grid, each with its beat label underneath."""
    from PIL import Image, ImageDraw

    thumbnails = [frame.resize((SHEET_THUMBNAIL_WIDTH, round(frame.height * SHEET_THUMBNAIL_WIDTH / frame.width)))
                  for frame in frames]
    cell_height = max(thumbnail.height for thumbnail in thumbnails) + SHEET_LABEL_HEIGHT
    rows = -(-len(thumbnails) // SHEET_COLUMNS)
    sheet = Image.new("RGB", (SHEET_COLUMNS * SHEET_THUMBNAIL_WIDTH, rows * cell_height), SHEET_BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    for position, (thumbnail, label) in enumerate(zip(thumbnails, labels, strict=True)):
        left = (position % SHEET_COLUMNS) * SHEET_THUMBNAIL_WIDTH
        top = (position // SHEET_COLUMNS) * cell_height
        sheet.paste(thumbnail, (left, top))
        draw.text((left + 8, top + thumbnail.height + 6), label, fill=SHEET_LABEL_COLOUR)
    return sheet


def collect_outputs(index: Path, scene_class: str, out: Path) -> list[SectionRecord]:
    (out / "sections").mkdir(parents=True, exist_ok=True)
    (out / "frames").mkdir(parents=True, exist_ok=True)
    shutil.copy2(full_video(index, scene_class), out / f"{scene_class}.mp4")
    records, last_frames = [], []
    for section in load_sections(index):
        video = out / "sections" / f"{section.label}.mp4"
        frame_path = out / "frames" / f"{section.label}.png"
        sheet_path = out / "frames" / f"{section.label}-sheet.png"
        shutil.copy2(section.video, video)
        samples = sampled_frames(section.video, SAMPLE_INTERVAL_SECONDS)
        samples[-1][1].save(frame_path)
        contact_sheet([image for _, image in samples], [f"{section.label} t={time:.1f}s" for time, _ in samples]
                      ).save(sheet_path)
        last_frames.append(samples[-1][1])
        records.append(SectionRecord(section.name, relative(video, out), relative(frame_path, out),
                                     relative(sheet_path, out), section.duration))
    contact_sheet(last_frames, [Path(record.frame).stem for record in records]).save(out / "contact-sheet.png")
    return records


def relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def write_manifest(out: Path, scene_file: Path, scene_class: str, quality: str, records: list[SectionRecord]) -> dict:
    manifest = {
        "scene_file": str(scene_file),
        "scene": scene_class,
        "quality": quality,
        "video": f"{scene_class}.mp4",
        "contact_sheet": "contact-sheet.png",
        "duration_seconds": round(sum(record.duration for record in records), 2),
        "sections": [asdict(record) for record in records],
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def render(scene_file: Path, scene_class: str, quality: str, out: Path) -> dict:
    if not scene_file.is_file():
        raise RenderError(f"no scene file at {scene_file}")
    with tempfile.TemporaryDirectory(prefix="manim-media-") as media:
        media_dir = Path(media)
        run_manim(manim_command(sys.executable, scene_file, scene_class, quality, media_dir),
                  scene_environment(scene_file))
        records = collect_outputs(find_sections_index(media_dir, scene_class), scene_class, out)
    return write_manifest(out, scene_file, scene_class, quality, records)


def parser() -> argparse.ArgumentParser:
    command_line = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    command_line.add_argument("scene_file", type=Path)
    command_line.add_argument("scene_class")
    command_line.add_argument("--quality", choices=list(QUALITY_FLAGS), default="preview")
    command_line.add_argument("--out", type=Path, help="Output folder (default: render/<quality> beside the scene)")
    return command_line


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = parser().parse_args(argv)
    scene_file = args.scene_file.expanduser().resolve()
    out = (args.out or scene_file.parent / "render" / args.quality).expanduser().resolve()
    try:
        manifest = render(scene_file, args.scene_class, args.quality, out)
    except (RenderError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    print(json.dumps({**manifest, "out": str(out)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
