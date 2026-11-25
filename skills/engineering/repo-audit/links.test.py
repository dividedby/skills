"""Check that every relative Markdown link in the repo-audit folder resolves.

`SKILL.md` is split into stage files and supporting files that link to each
other and to each other's headings. A moved or renamed heading breaks a link
without any other test noticing, so this walks every `*.md` file in the skill
folder and checks, for each relative link, that the target path exists and, when
the link has a `#anchor` into a Markdown file, that a heading of that file has
that GitHub-style slug.

Plain python3, standard library only: `python3 links.test.py`.
"""

from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent

FENCE = re.compile(r"^\s*(```|~~~)")
HEADING = re.compile(r"^#{1,6}\s+(.*?)\s*#*\s*$")
LINK = re.compile(r"\]\(([^)\s]+)\)")
CODE_SPAN = re.compile(r"`[^`\n]*`")
MD_LINK_TEXT = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def outside_fences(text: str) -> list[str]:
    """The lines of `text` that are not inside a fenced code block."""
    kept: list[str] = []
    fence = ""
    for line in text.split("\n"):
        m = FENCE.match(line)
        if m:
            if not fence:
                fence = m.group(1)
            elif m.group(1) == fence:
                fence = ""
            continue
        if not fence:
            kept.append(line)
    return kept


def slug(heading: str) -> str:
    """GitHub's heading anchor: lowercase, drop punctuation, spaces to hyphens."""
    text = MD_LINK_TEXT.sub(r"\1", heading).replace("`", "")
    text = re.sub(r"[*_]", "", text).strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def anchors(path: Path) -> set[str]:
    """Every heading anchor in a Markdown file, with GitHub's -1, -2 suffixes."""
    seen: dict[str, int] = {}
    found: set[str] = set()
    for line in outside_fences(path.read_text(encoding="utf-8")):
        m = HEADING.match(line)
        if not m:
            continue
        base = slug(m.group(1))
        n = seen.get(base, 0)
        seen[base] = n + 1
        found.add(base if n == 0 else f"{base}-{n}")
    return found


def check_tree(root: Path) -> list[str]:
    """One message per broken relative link under `root`."""
    errors: list[str] = []
    cache: dict[Path, set[str]] = {}
    for md in sorted(root.rglob("*.md")):
        if "node_modules" in md.parts or "__pycache__" in md.parts:
            continue
        lines = outside_fences(md.read_text(encoding="utf-8"))
        for lineno, line in enumerate(lines, 1):
            for target in LINK.findall(CODE_SPAN.sub("", line)):
                if re.match(r"[a-z][a-z0-9+.-]*:", target, re.IGNORECASE):
                    continue  # http:, https:, mailto:
                path_part, _, anchor = target.partition("#")
                dest = md if not path_part else (md.parent / path_part).resolve()
                where = f"{md.relative_to(root)}: {target}"
                if not dest.exists():
                    errors.append(f"{where}: no such file")
                    continue
                if anchor and dest.suffix == ".md":
                    if dest not in cache:
                        cache[dest] = anchors(dest)
                    if anchor not in cache[dest]:
                        errors.append(f"{where}: no heading with that anchor")
    return errors


class LinkTests(unittest.TestCase):
    def test_every_relative_link_in_the_skill_folder_resolves(self) -> None:
        self.assertEqual(check_tree(SKILL_DIR), [])

    def test_slug_matches_github(self) -> None:
        cases = {
            "Stage 1 — Scope": "stage-1--scope",
            "1. Read the checklist fresh": "1-read-the-checklist-fresh",
            "10. Skipped dimensions": "10-skipped-dimensions",
            "Lenses, depth and budgets": "lenses-depth-and-budgets",
            "The `run-log.md` file": "the-run-logmd-file",
            "A [link](./x.md) here": "a-link-here",
        }
        for heading, want in cases.items():
            with self.subTest(heading=heading):
                self.assertEqual(slug(heading), want)

    def test_flags_a_missing_file_and_a_missing_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.md").write_text(
                "# One\n\n[ok](#one) [bad](#two) [gone](./nope.md) "
                "[head](./b.md#there) [miss](./b.md#absent) "
                "[web](https://example.com/#x) `[code](#skipped)`\n\n"
                "```text\n[fenced](#skipped)\n```\n",
                encoding="utf-8",
            )
            (root / "b.md").write_text("## There\n\n## There\n", encoding="utf-8")
            errors = check_tree(root)
        self.assertEqual(
            errors,
            [
                "a.md: #two: no heading with that anchor",
                "a.md: ./nope.md: no such file",
                "a.md: ./b.md#absent: no heading with that anchor",
            ],
        )

    def test_repeated_headings_get_numbered_anchors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.md"
            path.write_text("## Run\n\n## Run\n", encoding="utf-8")
            self.assertEqual(anchors(path), {"run", "run-1"})


if __name__ == "__main__":
    unittest.main()
