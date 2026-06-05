#!/usr/bin/env python3
"""Self-test for check-skill-registration.py.

Builds a synthetic project tree in a temp dir (plugin.json + README.md + one
skill), points the hook at it via CLAUDE_PROJECT_DIR, and asserts exit 2
(blocked) when a SKILL.md is mis-registered or has bad frontmatter, exit 0
otherwise. This is the feedback gate for the hook: run it directly
(`./check-skill-registration.test.py`) — no test framework required.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).with_name("check-skill-registration.py")

GOOD_FRONTMATTER = "---\nname: demo\ndescription: A demo skill.\n---\n\n# Demo\n"
BLOCK = True
ALLOW = False

# (skill_md_body, registered_in_plugin, linked_in_readme, should_be_blocked)
CASES = [
    # fully valid -> passes
    (GOOD_FRONTMATTER, True, True, ALLOW),
    # registration gaps (existing behavior must still hold)
    (GOOD_FRONTMATTER, False, True, BLOCK),
    (GOOD_FRONTMATTER, True, False, BLOCK),
    # frontmatter gaps (new behavior)
    ("---\ndescription: no name here.\n---\n", True, True, BLOCK),       # missing name
    ("---\nname: demo\n---\n", True, True, BLOCK),                        # missing description
    ("---\nname:\ndescription:\n---\n", True, True, BLOCK),               # empty both
    ("---\nname: demo\ndescription:   \n---\n", True, True, BLOCK),       # whitespace-only desc
    ("# Demo\n\nNo frontmatter at all.\n", True, True, BLOCK),            # no frontmatter block
    ("---\nname: demo\ndescription: unterminated\n", True, True, BLOCK),  # never closed
]


def run(body: str, registered: bool, linked: bool) -> int:
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        skill_dir = root / "skills" / "bucket" / "demo"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(body)

        rel = "./skills/bucket/demo"
        (root / ".claude-plugin").mkdir()
        (root / ".claude-plugin" / "plugin.json").write_text(
            json.dumps({"skills": [rel] if registered else []})
        )
        (root / "README.md").write_text(
            f"- [Demo]({rel}/SKILL.md)\n" if linked else "no links here\n"
        )

        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(root)}
        proc = subprocess.run(
            [sys.executable, str(HOOK)],
            input="{}", capture_output=True, text=True, env=env,
        )
        return proc.returncode


def main() -> int:
    failures = []
    for body, registered, linked, should_block in CASES:
        code = run(body, registered, linked)
        blocked = code == 2
        if blocked != should_block:
            want = "BLOCK" if should_block else "ALLOW"
            got = "BLOCK" if blocked else f"ALLOW(exit {code})"
            failures.append(f"  body={body!r} reg={registered} link={linked}: want {want}, got {got}")

    if failures:
        print("check-skill-registration self-test FAILED:\n" + "\n".join(failures))
        return 1
    print(f"check-skill-registration self-test passed ({len(CASES)} cases)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
