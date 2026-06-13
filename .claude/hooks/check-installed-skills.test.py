#!/usr/bin/env python3
"""Self-test for check-installed-skills.py.

Builds synthetic ~/.claude and docs/ fixtures in temp dirs, points the hook at
them via CLAUDE_PROJECT_DIR and a monkeypatched HOME, and asserts:
  - no drift → silent + exit 0
  - listed-but-missing skill/plugin → warning on stderr + exit 0
  - installed-but-unlisted skill/plugin → warning on stderr + exit 0
  - ~/.claude absent → silent + exit 0

No test framework required. Run directly:
    python3 .claude/hooks/check-installed-skills.test.py
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).with_name("check-installed-skills.py")

# Minimal installed-skills.md template — mirrors the real file's section headers.
SNAPSHOT_TEMPLATE = """\
# Installed Skills

## Globally installed skills

{skills_line}

## Installed plugins

From `claude-plugins-official`: {plugins_line}.

## Built-in CLI skills

none.
"""


def make_snapshot(skills: list[str], plugins: list[str]) -> str:
    skills_line = ", ".join(f"`{s}`" for s in skills) if skills else "(none)"
    plugins_line = ", ".join(f"`{p}`" for p in plugins) if plugins else "(none)"
    return SNAPSHOT_TEMPLATE.format(skills_line=skills_line, plugins_line=plugins_line)


def make_plugins_json(plugins: list[str]) -> dict:
    return {
        "version": 2,
        "plugins": {f"{p}@marketplace": [{"scope": "user"}] for p in plugins},
    }


def run(
    *,
    listed_skills: list[str],
    listed_plugins: list[str],
    installed_skills: list[str],
    installed_plugins: list[str],
    claude_dir_exists: bool = True,
) -> tuple[int, str]:
    """Run the hook in a fully synthetic environment; return (exit_code, stderr)."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # Project tree: docs/agents/installed-skills.md
        project = tmp_path / "project"
        snapshot_dir = project / "docs" / "agents"
        snapshot_dir.mkdir(parents=True)
        (snapshot_dir / "installed-skills.md").write_text(
            make_snapshot(listed_skills, listed_plugins)
        )

        # Fake HOME with or without ~/.claude
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        if claude_dir_exists:
            claude_dir = fake_home / ".claude"
            # skills/
            skills_dir = claude_dir / "skills"
            for name in installed_skills:
                (skills_dir / name).mkdir(parents=True)
            # plugins/installed_plugins.json
            plugins_dir = claude_dir / "plugins"
            plugins_dir.mkdir(parents=True)
            (plugins_dir / "installed_plugins.json").write_text(
                json.dumps(make_plugins_json(installed_plugins))
            )

        env = {
            **os.environ,
            "CLAUDE_PROJECT_DIR": str(project),
            "HOME": str(fake_home),
        }
        proc = subprocess.run(
            [sys.executable, str(HOOK)],
            input="{}",
            capture_output=True,
            text=True,
            env=env,
        )
        return proc.returncode, proc.stderr


def main() -> int:
    failures = []

    # Case 1: no drift → silent + exit 0
    code, stderr = run(
        listed_skills=["foo", "bar"],
        listed_plugins=["plug-a"],
        installed_skills=["foo", "bar"],
        installed_plugins=["plug-a"],
    )
    if code != 0 or stderr.strip():
        failures.append(f"no-drift: expected silent exit 0, got code={code} stderr={stderr!r}")

    # Case 2: listed skill not installed → warning + exit 0
    code, stderr = run(
        listed_skills=["foo", "ghost-skill"],
        listed_plugins=[],
        installed_skills=["foo"],
        installed_plugins=[],
    )
    if code != 0:
        failures.append(f"listed-missing-skill: expected exit 0, got {code}")
    if "ghost-skill" not in stderr:
        failures.append(f"listed-missing-skill: 'ghost-skill' not in stderr: {stderr!r}")

    # Case 3: installed skill not listed → warning + exit 0
    code, stderr = run(
        listed_skills=["foo"],
        listed_plugins=[],
        installed_skills=["foo", "unlisted-skill"],
        installed_plugins=[],
    )
    if code != 0:
        failures.append(f"installed-unlisted-skill: expected exit 0, got {code}")
    if "unlisted-skill" not in stderr:
        failures.append(f"installed-unlisted-skill: 'unlisted-skill' not in stderr: {stderr!r}")

    # Case 4: listed plugin not installed → warning + exit 0
    code, stderr = run(
        listed_skills=[],
        listed_plugins=["real-plugin", "ghost-plugin"],
        installed_skills=[],
        installed_plugins=["real-plugin"],
    )
    if code != 0:
        failures.append(f"listed-missing-plugin: expected exit 0, got {code}")
    if "ghost-plugin" not in stderr:
        failures.append(f"listed-missing-plugin: 'ghost-plugin' not in stderr: {stderr!r}")

    # Case 5: installed plugin not listed → warning + exit 0
    code, stderr = run(
        listed_skills=[],
        listed_plugins=["real-plugin"],
        installed_skills=[],
        installed_plugins=["real-plugin", "surprise-plugin"],
    )
    if code != 0:
        failures.append(f"installed-unlisted-plugin: expected exit 0, got {code}")
    if "surprise-plugin" not in stderr:
        failures.append(f"installed-unlisted-plugin: 'surprise-plugin' not in stderr: {stderr!r}")

    # Case 6: ~/.claude absent (CI) → silent + exit 0
    code, stderr = run(
        listed_skills=["foo"],
        listed_plugins=["bar"],
        installed_skills=[],
        installed_plugins=[],
        claude_dir_exists=False,
    )
    if code != 0 or stderr.strip():
        failures.append(f"no-claude-dir: expected silent exit 0, got code={code} stderr={stderr!r}")

    # Case 7: both skill and plugin drift together → warning covers both + exit 0
    code, stderr = run(
        listed_skills=["present", "absent-skill"],
        listed_plugins=["present-plugin", "absent-plugin"],
        installed_skills=["present", "extra-skill"],
        installed_plugins=["present-plugin", "extra-plugin"],
    )
    if code != 0:
        failures.append(f"combined-drift: expected exit 0, got {code}")
    for token in ("absent-skill", "extra-skill", "absent-plugin", "extra-plugin"):
        if token not in stderr:
            failures.append(f"combined-drift: '{token}' missing from stderr: {stderr!r}")

    if failures:
        print("check-installed-skills self-test FAILED:\n" + "\n".join(failures))
        return 1

    total = 7
    print(f"check-installed-skills self-test passed ({total} cases)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
