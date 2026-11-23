"""On-demand eval runner: run the repo-audit skill headless on fixtures and check the results.

This spends tokens. It is not run in CI. Each fixture is one `claude -p` call
(the skill at `quick` depth by default); the runner then reads the run's
findings.json and checks it against expectations.json, checks the fixture repo
is unchanged, and reports the cost of each run.

    python3 run_evals.py --dry-run        # generate fixtures, print the commands, spend nothing
    python3 run_evals.py                  # the paid run on the default three fixtures

See README.md in this folder.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, NamedTuple

import findings_check
import fixtures

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]

# Slash name of the skill under --plugin-dir: the plugin name in
# .claude-plugin/plugin.json and the skill's `name` frontmatter.
DEFAULT_SKILL = "/dividedby-skills:repo-audit"

# Not the Artifact tool or any publish or send tool: with none, the skill falls
# back to saving the page and findings.json in its scratchpad. Edit is left out
# because the audit is read-only. The rest is what a quick run uses: lenses read
# and search (Read, Grep, Glob), write their reports (Write), run git and the
# baseline (Bash), launch lenses (Agent) and check external facts (WebSearch,
# WebFetch).
ALLOWED_TOOLS = [
    "Read",
    "Grep",
    "Glob",
    "Write",
    "Bash",
    "Agent",
    "WebSearch",
    "WebFetch",
]

DEFAULT_FIXTURES = ["single-script", "docs-only", "unknown-type"]
DEFAULT_BUDGET_USD = 10.0
TOKEN_NOTE = "about 150k agent tokens each at quick"


# ------------------------------------------------------------------ command


def build_prompt(skill: str, depth: str, artifacts: Path) -> str:
    return (
        f"{skill} {depth}\n\n"
        "This is a synthetic eval fixture; nothing in it is real. No user is available to "
        "answer questions: where the skill asks one, record that it could not ask and continue. "
        "The Artifact tool is not available, so save the page, run-log.md and findings.json "
        "as the skill describes for that case. After Stage 6, also copy findings.json to "
        f"{artifacts / 'findings.json'}. Report to the invoking session."
    )


def build_command(
    claude: str,
    skill: str,
    depth: str,
    plugin_dir: Path,
    artifacts: Path,
    budget: float,
) -> list[str]:
    return [
        claude,
        "-p",
        build_prompt(skill, depth, artifacts),
        "--output-format",
        "json",
        "--plugin-dir",
        str(plugin_dir),
        "--permission-mode",
        "dontAsk",
        "--allowedTools",
        ",".join(ALLOWED_TOOLS),
        "--disallowedTools",
        "Artifact",
        "--add-dir",
        str(artifacts),
        "--max-budget-usd",
        f"{budget:g}",
        "--no-session-persistence",
    ]


# -------------------------------------------------------------------- cost


class Cost(NamedTuple):
    usd: float
    tokens: int
    wall_s: float
    status: str


def _num(value: Any) -> float:
    return (
        float(value)
        if isinstance(value, (int, float)) and not isinstance(value, bool)
        else 0.0
    )


def parse_result(text: str) -> dict:
    """The result object of `claude -p --output-format json`; {} when unreadable."""
    try:
        doc = json.loads(text)
    except ValueError:
        return {}
    if isinstance(doc, list):
        doc = next(
            (
                d
                for d in reversed(doc)
                if isinstance(d, dict) and d.get("type") == "result"
            ),
            {},
        )
    return doc if isinstance(doc, dict) else {}


def summarise_cost(result: dict) -> Cost:
    """Cost, tokens (input, output and cache, all models) and wall time of a run.

    Subagent usage is part of total_cost_usd and modelUsage.
    """
    tokens = 0
    usage = result.get("modelUsage")
    if isinstance(usage, dict):
        for model in usage.values():
            if isinstance(model, dict):
                for field in (
                    "inputTokens",
                    "outputTokens",
                    "cacheReadInputTokens",
                    "cacheCreationInputTokens",
                ):
                    tokens += int(_num(model.get(field)))
    status = "ok"
    if result.get("is_error"):
        # A failed start (auth, API) still reports subtype "success"; the
        # reason is in terminal_reason and the result text.
        subtype = result.get("subtype")
        reason = (
            subtype
            if subtype and subtype != "success"
            else result.get("terminal_reason") or "unknown"
        )
        status = f"error: {reason}"
        text = str(result.get("result") or "").strip()
        if text and reason != subtype:
            status += f" ({text[:80]})"
    elif not result:
        status = "no result JSON"
    return Cost(
        _num(result.get("total_cost_usd")),
        tokens,
        _num(result.get("duration_ms")) / 1000,
        status,
    )


# ------------------------------------------------------------------ findings


def _fresh(path: Path, started: float) -> bool:
    return path.is_file() and path.stat().st_mtime >= started


def locate_findings(artifacts: Path, result_text: str, started: float) -> Path | None:
    """Find the findings.json this run wrote: the copy in the artifacts folder, else
    a path the run's result names. A file older than the run's start is never
    accepted, so a leftover from an earlier run cannot pass as this one.

    There is no scan of the temp folders for a scratchpad copy: another session's
    file could match. A run that saves findings.json but neither copies it nor
    names it reports "no findings.json", which is a real miss.
    """
    copy = artifacts / "findings.json"
    if _fresh(copy, started):
        return copy
    for match in re.findall(r"(/[^\s\"'`()<>\[\]]+findings\.json)", result_text):
        if _fresh(Path(match), started):
            return Path(match)
    return None


# ------------------------------------------------------------------ unchanged


def _git_out(repo: Path, *args: str) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        env=env,
        capture_output=True,
        text=True,
    )
    return proc.stdout


def snapshot_repo(repo: Path) -> dict[str, Any]:
    """HEAD, `git status --porcelain --ignored`, and a hash per file outside .git."""
    files: dict[str, str] = {}
    for root, dirs, names in os.walk(repo):
        dirs[:] = sorted(d for d in dirs if d != ".git")
        for name in sorted(names):
            path = Path(root) / name
            digest = (
                hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "-"
            )
            files[str(path.relative_to(repo))] = digest
    return {
        "head": _git_out(repo, "rev-parse", "HEAD").strip(),
        "status": _git_out(repo, "status", "--porcelain", "--ignored"),
        "files": files,
    }


def compare_snapshots(before: dict, after: dict) -> list[str]:
    changes = []
    if before["head"] != after["head"]:
        changes.append(f"HEAD {before['head'][:7]} -> {after['head'][:7]}")
    if before["status"] != after["status"]:
        changes.append("git status changed")
    for path in sorted(set(before["files"]) | set(after["files"])):
        old, new = before["files"].get(path), after["files"].get(path)
        if old != new:
            changes.append(
                f"{path}: {'added' if old is None else 'removed' if new is None else 'modified'}"
            )
    return changes


# ----------------------------------------------------------------------- run


class FixtureRun(NamedTuple):
    name: str
    results: list[findings_check.Result]
    cost: Cost


def run_claude(cmd: list[str], cwd: Path, timeout_s: float) -> tuple[str, str]:
    """The one place that spawns claude (and spends tokens). Returns stdout, stderr."""
    try:
        proc = subprocess.run(
            cmd, cwd=cwd, check=False, capture_output=True, text=True, timeout=timeout_s
        )
    except subprocess.TimeoutExpired as err:
        return _text(err.stdout), _text(
            err.stderr
        ) + f"\ntimed out after {timeout_s:.0f}s"
    except OSError as err:
        return "", f"could not start {cmd[0]}: {err}"
    return proc.stdout, proc.stderr


def _text(value: Any) -> str:
    return value.decode() if isinstance(value, bytes) else (value or "")


def run_fixture(
    name: str,
    repo: Path,
    out: Path,
    args: argparse.Namespace,
    schema: dict,
    expectations: dict,
) -> FixtureRun:
    artifacts = out / name
    artifacts.mkdir(parents=True, exist_ok=True)
    cmd = build_command(
        args.claude,
        args.skill,
        args.depth,
        args.plugin_dir,
        artifacts,
        args.max_budget_usd,
    )
    for stale in ("findings.json", "result.json", "stderr.txt"):
        (artifacts / stale).unlink(missing_ok=True)
    before = snapshot_repo(repo)
    started = time.time()
    stdout, stderr = run_claude(cmd, repo, args.timeout_min * 60)
    (artifacts / "result.json").write_text(stdout, encoding="utf-8")
    (artifacts / "stderr.txt").write_text(stderr, encoding="utf-8")
    result = parse_result(stdout)
    cost = summarise_cost(result)
    result_text = str(result.get("result", "")) or stdout

    results: list[findings_check.Result] = []
    found = locate_findings(artifacts, result_text, started)
    if found is None:
        results.append(
            findings_check.Result("findings.json", False, "no findings.json found")
        )
    else:
        try:
            doc = json.loads(found.read_text(encoding="utf-8"))
        except ValueError as err:
            results.append(
                findings_check.Result(
                    "findings.json", False, f"{found}: not JSON ({err})"
                )
            )
        else:
            if found != artifacts / "findings.json":
                (artifacts / "findings.json").write_text(
                    json.dumps(doc, indent=2), encoding="utf-8"
                )
            errors = findings_check.validate(doc, schema)
            results.append(
                findings_check.Result(
                    "schema-valid",
                    not errors,
                    "; ".join(errors[:3])
                    + (f"; {len(errors) - 3} more" if len(errors) > 3 else "")
                    or "matches findings.schema.json",
                )
            )
            results += findings_check.check_expectations(
                doc, expectations["fixtures"][name], args.depth
            )
    changes = compare_snapshots(before, snapshot_repo(repo))
    results.append(
        findings_check.Result(
            "repo unchanged",
            not changes,
            "; ".join(changes[:5]) or "HEAD, status and files identical",
        )
    )
    return FixtureRun(name, results, cost)


# -------------------------------------------------------------------- output


def format_report(runs: list[FixtureRun]) -> str:
    lines = ["fixture | expectation | result | detail", "--- | --- | --- | ---"]
    for run in runs:
        for r in run.results:
            lines.append(
                f"{run.name} | {r.name} | {'PASS' if r.ok else 'FAIL'} | {r.detail}"
            )
    lines += [
        "",
        "fixture | cost USD | tokens | wall | status",
        "--- | --- | --- | --- | ---",
    ]
    for run in runs:
        c = run.cost
        lines.append(
            f"{run.name} | {c.usd:.2f} | {c.tokens:,} | {c.wall_s / 60:.1f} min | {c.status}"
        )
    total = sum(r.cost.usd for r in runs)
    tokens = sum(r.cost.tokens for r in runs)
    wall = sum(r.cost.wall_s for r in runs)
    lines.append(f"TOTAL | {total:.2f} | {tokens:,} | {wall / 60:.1f} min |")
    return "\n".join(lines)


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    parser.add_argument(
        "--fixtures", default=",".join(DEFAULT_FIXTURES), help="comma-separated names"
    )
    parser.add_argument("--depth", default="quick", choices=["quick", "standard"])
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="generate fixtures and print the commands; spend nothing",
    )
    parser.add_argument(
        "--max-budget-usd",
        type=float,
        default=DEFAULT_BUDGET_USD,
        help="cap per fixture",
    )
    parser.add_argument(
        "--out", type=Path, help="output folder (default: a new temp folder)"
    )
    parser.add_argument("--plugin-dir", type=Path, default=REPO_ROOT)
    parser.add_argument(
        "--skill",
        default=DEFAULT_SKILL,
        help="the skill's slash name under --plugin-dir",
    )
    parser.add_argument("--claude", default="claude", help="the claude binary")
    parser.add_argument(
        "--timeout-min", type=float, default=60, help="wall-time limit per fixture"
    )
    args = parser.parse_args(argv)
    args.fixtures = [n for n in args.fixtures.split(",") if n]
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    unknown = [n for n in args.fixtures if n not in fixtures.FIXTURES]
    if unknown:
        print(f"error: unknown fixture(s): {', '.join(unknown)}", file=sys.stderr)
        return 2
    out = args.out or Path(tempfile.mkdtemp(prefix="repo-audit-evals-"))
    try:
        made = fixtures.generate(out / "fixtures", args.fixtures)
    except fixtures.FixtureError as err:
        print(f"error: {err}", file=sys.stderr)
        return 2
    print(f"output folder: {out}")

    if args.dry_run:
        print(
            f"dry run: nothing is spawned and nothing is spent; a real run is {TOKEN_NOTE}."
        )
        print(f"allowed tools: {','.join(ALLOWED_TOOLS)}")
        for name, repo in made.items():
            cmd = build_command(
                args.claude,
                args.skill,
                args.depth,
                args.plugin_dir,
                out / name,
                args.max_budget_usd,
            )
            print(
                f"\n# {name}: cwd {repo}, budget cap ${args.max_budget_usd:g}\n{shlex.join(cmd)}"
            )
        return 0

    schema = json.loads((HERE / "findings.schema.json").read_text(encoding="utf-8"))
    expectations = json.loads((HERE / "expectations.json").read_text(encoding="utf-8"))
    runs = []
    for name, repo in made.items():
        print(f"running {name} ...", flush=True)
        runs.append(run_fixture(name, repo, out, args, schema, expectations))
    report = format_report(runs)
    print("\n" + report)
    summary = {
        "depth": args.depth,
        "runs": [
            {
                "fixture": r.name,
                "cost": r.cost._asdict(),
                "results": [x._asdict() for x in r.results],
            }
            for r in runs
        ],
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    failed = sum(1 for r in runs for x in r.results if not x.ok)
    print(f"\n{failed} failing expectation(s); output in {out}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
