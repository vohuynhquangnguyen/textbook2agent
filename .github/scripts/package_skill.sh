#!/usr/bin/env bash
# Package the committed skill as textbook2agent-<version>.zip with textbook2agent/SKILL.md at the top,
# plus the license files, ready to upload as a skill. Only committed files are packaged (git archive of HEAD),
# so local caches and uncommitted edits never reach a release.
# Usage: package_skill.sh <version> <output-directory>
set -euo pipefail

version="$1"
output="$(mkdir -p "$2" && cd "$2" && pwd)"
repository="$(cd "$(dirname "$0")/../.." && pwd)"
staging="$(mktemp -d)"
trap 'rm -rf "$staging"' EXIT

mkdir "$staging/textbook2agent"
git -C "$repository" archive --format=tar HEAD:skills/textbook2agent | tar -x -C "$staging/textbook2agent"
git -C "$repository" archive --format=tar HEAD LICENSE THIRD_PARTY_NOTICES.md | tar -x -C "$staging/textbook2agent"

archive="$output/textbook2agent-$version.zip"
rm -f "$archive"
(cd "$staging" && zip -qr "$archive" textbook2agent)
echo "$archive"
