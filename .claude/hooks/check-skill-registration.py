#!/usr/bin/env python3
"""Stop hook: every skill dir must be registered in plugin.json and README.md,
and its SKILL.md must carry valid frontmatter (non-empty name + description)."""
import json, os, sys
from pathlib import Path

REQUIRED_FRONTMATTER = ("name", "description")


def frontmatter_fields(text):
    """Return the top-level scalar keys of the leading `---` frontmatter block.

    Returns None when there is no leading frontmatter block at all. A targeted
    delimiter-and-key scan — no YAML dependency, stdlib only.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    fields = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return fields
        if ":" in line and not line.startswith((" ", "\t", "#")):
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip()
    return None  # opened with `---` but never closed -> malformed

# Defensive loop-guard: bail if this Stop was itself triggered by a hook block.
try:
    stdin = json.load(sys.stdin)
    if stdin.get("stop_hook_active"):
        sys.exit(0)
except Exception:
    pass

root = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
plugin_path = root / ".claude-plugin" / "plugin.json"
readme_path = root / "README.md"

# Skill dirs = any dir under skills/ holding a SKILL.md -> "./skills/<bucket>/<name>"
skill_dirs = sorted(
    "./" + str(p.parent.relative_to(root))
    for p in root.glob("skills/*/*/SKILL.md")
)

try:
    registered = set(json.loads(plugin_path.read_text()).get("skills", []))
except Exception as e:
    print(f"skill-registration: cannot read plugin.json ({e})", file=sys.stderr)
    sys.exit(2)

readme = readme_path.read_text() if readme_path.exists() else ""

problems = []
for s in skill_dirs:
    if s not in registered:
        problems.append(f"  - {s} is missing from .claude-plugin/plugin.json `skills[]`")
    if f"({s}/SKILL.md)" not in readme:
        problems.append(f"  - {s} has no link in README.md (expected `({s}/SKILL.md)`)")
    fields = frontmatter_fields((root / s / "SKILL.md").read_text())
    if fields is None:
        problems.append(f"  - {s}/SKILL.md has no valid `---` frontmatter block")
    else:
        for key in REQUIRED_FRONTMATTER:
            if not fields.get(key):
                problems.append(f"  - {s}/SKILL.md frontmatter is missing or has an empty `{key}:` field")

# Reverse: registered entries with no SKILL.md on disk
on_disk = set(skill_dirs)
for r in registered:
    if r not in on_disk:
        problems.append(f"  - plugin.json registers {r} but no {r}/SKILL.md exists")

if problems:
    print("Skill-registration check failed - fix before finishing:\n"
          + "\n".join(problems)
          + "\n(CLAUDE.md: every skill must be registered in plugin.json AND README.md, "
            "with non-empty name + description frontmatter in SKILL.md)",
          file=sys.stderr)
    sys.exit(2)  # block the stop, feed message back to Claude
