#!/usr/bin/env python3
"""Stop hook: every skill dir must be registered in plugin.json and README.md,
and its SKILL.md must carry valid frontmatter (non-empty name + description,
each within the skill spec's limits)."""
import json, os, re, sys
from pathlib import Path

REQUIRED_FRONTMATTER = ("name", "description")
ALLOWED_FRONTMATTER_KEYS = {"name", "description", "disable-model-invocation"}

# Spec limits, per skill-creator's quick_validate.py (source-first: read that
# script rather than guessing at the numbers).
NAME_MAX_LEN = 64
DESCRIPTION_MAX_LEN = 1024
KEBAB_RE = re.compile(r"^[a-z0-9-]+$")
_BLOCK_SCALAR_INDICATORS = {">", ">-", ">+", "|", "|-", "|+"}


def frontmatter_fields(text):
    """Return the top-level scalar keys of the leading `---` frontmatter block.

    Returns None when there is no leading frontmatter block at all. A targeted
    delimiter-and-key scan — no YAML dependency, stdlib only. Folded (`>`) and
    literal (`|`) block scalars are resolved by joining their continuation
    lines, so a multi-line `description: >` block reads as its real joined
    text rather than just the bare block indicator.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    fields = {}
    i = 1
    while i < len(lines):
        line = lines[i]
        if line.strip() == "---":
            return fields
        if ":" in line and not line.startswith((" ", "\t", "#")):
            key, _, value = line.partition(":")
            key, value = key.strip(), value.strip()
            if value in _BLOCK_SCALAR_INDICATORS:
                block_lines = []
                i += 1
                while i < len(lines) and (lines[i].startswith((" ", "\t")) or not lines[i].strip()):
                    block_lines.append(lines[i].strip())
                    i += 1
                fields[key] = " ".join(bl for bl in block_lines if bl)
                continue
            fields[key] = value
        i += 1
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
        name = fields.get("name", "")
        if name:
            if not KEBAB_RE.match(name) or name.startswith("-") or name.endswith("-") or "--" in name:
                problems.append(f"  - {s}/SKILL.md `name: {name}` is not kebab-case (lowercase letters, digits, "
                                 "hyphens only; no leading/trailing/double hyphens)")
            if len(name) > NAME_MAX_LEN:
                problems.append(f"  - {s}/SKILL.md `name:` is {len(name)} chars, over the {NAME_MAX_LEN}-char limit")
        description = fields.get("description", "")
        if description:
            if "<" in description or ">" in description:
                problems.append(f"  - {s}/SKILL.md `description:` contains an angle bracket (`<` or `>`), which is disallowed")
            if len(description) > DESCRIPTION_MAX_LEN:
                problems.append(f"  - {s}/SKILL.md `description:` is {len(description)} chars, over the "
                                 f"{DESCRIPTION_MAX_LEN}-char limit (over-limit descriptions are silently truncated "
                                 "in available_skills, degrading skill-triggering accuracy)")
        unknown = sorted(k for k in fields if k not in ALLOWED_FRONTMATTER_KEYS)
        for key in unknown:
            print(f"skill-registration WARNING: {s}/SKILL.md has unrecognised frontmatter key `{key}`",
                  file=sys.stderr)

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
