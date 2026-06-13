#!/usr/bin/env python3
"""Stop hook (advisory/non-blocking): warn when docs/agents/installed-skills.md
drifts from the live global install (~/.claude/skills/ + installed plugins).

Always exits 0 — never blocks the Stop. Prints a warning to stderr only when
drift is detected. Silent when there is no drift or when ~/.claude is absent
(e.g. CI). This prevents the double-run infinite loop: we check stop_hook_active
and bail immediately if set."""
import json
import os
import re
import sys
from pathlib import Path


def get_listed_skills(snapshot_path: Path) -> tuple[set[str], set[str]]:
    """Parse installed-skills.md and return (listed_skills, listed_plugins).

    Skills section: all backtick tokens are skill names (the section contains
    only skill names, no prose with backtick-quoted non-names).

    Plugins section: two line patterns carry plugin names:
      (a) A line starting with `<name>` followed by ` — ` (standalone entry).
      (b) A line starting with "From `marketplace`...: " followed by
          comma-separated backtick tokens — the names after the colon.
    Lines that are purely source attribution (the "From ..." prefix itself)
    are NOT harvested for plugin names.
    """
    text = snapshot_path.read_text()

    # Extract a section's raw text between its ## header and the next ## header.
    def section_text(header: str) -> str:
        m = re.search(
            r"## " + re.escape(header) + r".*?(?=\n## |\Z)", text, re.DOTALL
        )
        return m.group() if m else ""

    # Skills: backtick names in the section that have no '/' (excludes repo paths
    # and filesystem path prose like `mattpocock/skills` or `~/.claude/skills/`).
    listed_skills: set[str] = set()
    for m in re.finditer(r"`([^`]+)`", section_text("Globally installed skills")):
        name = m.group(1)
        if "/" not in name:
            listed_skills.add(name)

    # Plugins: line-aware parse to avoid marketplace attribution names.
    #
    # Two patterns carry plugin names:
    # (a) Standalone entry: a line starting with `<name>` then " —" (no slash in name).
    # (b) Attribution block: one or more lines following a "From `marketplace`...:"
    #     line. The `From ...` line itself only names the marketplace (skip it).
    #     Lines after the colon that are backtick-name lists are plugin names.
    listed_plugins: set[str] = set()
    lines = section_text("Installed plugins").splitlines()
    in_attribution_block = False
    for line in lines:
        stripped = line.strip()
        # Pattern (a): standalone entry
        m = re.match(r"^`([^`]+)`\s+—", stripped)
        if m:
            name = m.group(1)
            if "/" not in name:
                listed_plugins.add(name)
            in_attribution_block = False
            continue
        # Pattern (b) start: "From `marketplace` (...):" opens an attribution block
        if re.match(r"^From `[^`]+`", stripped):
            in_attribution_block = True
            # Names may follow the colon on the same line
            colon_pos = stripped.find(":")
            if colon_pos != -1:
                rest = stripped[colon_pos + 1:]
                for nm in re.finditer(r"`([^`]+)`", rest):
                    n = nm.group(1)
                    if "/" not in n:
                        listed_plugins.add(n)
            continue
        # Inside attribution block: harvest backtick names from continuation lines
        if in_attribution_block and stripped:
            if stripped.startswith("`") or re.search(r"`[^`]+`", stripped):
                for nm in re.finditer(r"`([^`]+)`", stripped):
                    n = nm.group(1)
                    if "/" not in n:
                        listed_plugins.add(n)
                continue
            # A non-backtick-list line ends the attribution block
            in_attribution_block = False

    return listed_skills, listed_plugins


def get_live_skills(claude_dir: Path) -> set[str]:
    """Return skill names from ~/.claude/skills/ (each subdir with a SKILL.md)."""
    skills_dir = claude_dir / "skills"
    if not skills_dir.is_dir():
        return set()
    return {p.name for p in skills_dir.iterdir() if p.is_dir()}


def get_live_plugins(claude_dir: Path) -> set[str]:
    """Return plugin names from ~/.claude/plugins/installed_plugins.json.

    Plugin keys are formatted as `<name>@<marketplace>`; we extract just the name.
    """
    plugins_json = claude_dir / "plugins" / "installed_plugins.json"
    if not plugins_json.exists():
        return set()
    try:
        data = json.loads(plugins_json.read_text())
        plugins: set[str] = set()
        for key in data.get("plugins", {}):
            name = key.split("@")[0]
            plugins.add(name)
        return plugins
    except Exception:
        return set()


def main() -> int:
    # Loop-guard: bail if this Stop was itself triggered by a hook block.
    try:
        stdin = json.load(sys.stdin)
        if stdin.get("stop_hook_active"):
            return 0
    except Exception:
        pass

    claude_dir = Path.home() / ".claude"
    if not claude_dir.exists():
        # CI or environment without a global install — silent exit.
        return 0

    root = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
    snapshot_path = root / "docs" / "agents" / "installed-skills.md"
    if not snapshot_path.exists():
        # Snapshot not present in this repo; nothing to check.
        return 0

    listed_skills, listed_plugins = get_listed_skills(snapshot_path)
    live_skills = get_live_skills(claude_dir)
    live_plugins = get_live_plugins(claude_dir)

    drift_lines = []

    # (a) listed-but-not-installed
    missing_skills = listed_skills - live_skills
    missing_plugins = listed_plugins - live_plugins
    for name in sorted(missing_skills):
        drift_lines.append(f"  listed in snapshot but not installed: skill '{name}'")
    for name in sorted(missing_plugins):
        drift_lines.append(f"  listed in snapshot but not installed: plugin '{name}'")

    # (b) installed-but-not-listed
    unlisted_skills = live_skills - listed_skills
    unlisted_plugins = live_plugins - listed_plugins
    for name in sorted(unlisted_skills):
        drift_lines.append(f"  installed but not in snapshot: skill '{name}'")
    for name in sorted(unlisted_plugins):
        drift_lines.append(f"  installed but not in snapshot: plugin '{name}'")

    if drift_lines:
        print(
            "installed-skills drift detected — update docs/agents/installed-skills.md:\n"
            + "\n".join(drift_lines),
            file=sys.stderr,
        )

    # Advisory only — never block.
    return 0


if __name__ == "__main__":
    sys.exit(main())
