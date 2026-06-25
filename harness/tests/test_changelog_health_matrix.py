"""Pins the changelog-health ``prepare`` job's matrix-extraction shell.

The empty-list path is the regression surface: an all-comments/blank
``enrolled-repos.txt`` must make the step emit ``matrix=[]`` and exit 0, so the
dependent ``changelog-health`` job *skips* via ``if: ... != '[]'``. An earlier
cut ran the greps under ``set -o pipefail`` without ``|| true`` — a no-match
grep exit 1 killed the step red, the matrix output was never written, and the
dependent job skipped as a *failure* instead (violating the PR1 acceptance
criterion). These tests run the script extracted verbatim from the workflow
(not a copy) in bash, so a future YAML edit that reintroduces the bug fails here.
"""

import os
import subprocess
import tempfile
import unittest

import yaml

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_WORKFLOW = os.path.join(_REPO, ".github", "workflows", "changelog-health.yml")
_ENROLL_REL = os.path.join("harness", "changelog-health", "enrolled-repos.txt")


def _read_step_script():
    """Return the `run:` body of the prepare job's `id: read` step, verbatim."""
    with open(_WORKFLOW) as fh:
        wf = yaml.safe_load(fh)
    steps = wf["jobs"]["prepare"]["steps"]
    read = next(s for s in steps if s.get("id") == "read")
    return read["run"]


def _run(script, cwd):
    """Run `script` in bash from `cwd`; return (exit_code, parsed matrix line).

    GITHUB_OUTPUT lands in its own temp file (never inside `cwd`) so a run with
    `cwd` = the real repo root doesn't litter it.
    """
    with tempfile.NamedTemporaryFile("r", suffix=".out") as out:
        proc = subprocess.run(
            ["bash", "-c", script],
            cwd=cwd,
            env={**os.environ, "GITHUB_OUTPUT": out.name},
            capture_output=True,
            text=True,
        )
        matrix = None
        for line in out:
            if line.startswith("matrix="):
                matrix = line[len("matrix="):].strip()
    return proc.returncode, matrix


def _with_enroll(tmp, content):
    """Write `content` to a temp `enrolled-repos.txt` and return its repo dir."""
    path = os.path.join(tmp, _ENROLL_REL)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as fh:
        fh.write(content)
    return tmp


class ChangelogHealthMatrixTest(unittest.TestCase):
    def setUp(self):
        self.script = _read_step_script()

    def test_real_file_yields_six(self):
        code, matrix = _run(self.script, _REPO)
        self.assertEqual(code, 0)
        self.assertIn("dividedby/skills", matrix)
        self.assertEqual(matrix.count("dividedby/"), 6)

    def test_empty_list_skips_not_errors(self):
        # The regression: must be matrix=[] AND exit 0, never a red step.
        with tempfile.TemporaryDirectory() as tmp:
            cwd = _with_enroll(tmp, "# only comments\n\n   \n")
            code, matrix = _run(self.script, cwd)
        self.assertEqual(code, 0)
        self.assertEqual(matrix, "[]")

    def test_crlf_stripped(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = _with_enroll(tmp, "dividedby/skills\r\n# x\r\ndividedby/new\r\n")
            code, matrix = _run(self.script, cwd)
        self.assertEqual(code, 0)
        self.assertEqual(matrix, '["dividedby/skills","dividedby/new"]')


if __name__ == "__main__":
    unittest.main()
