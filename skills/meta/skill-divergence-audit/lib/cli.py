"""CLI seam over the pure helpers, for the ``skill-divergence-audit`` skill.

The skill runs unattended and must enforce the leak guard and the per-run
proposal budget *mechanically*, not by prompt discipline. This module exposes
the two pure decisions — ``sanitizer.check`` (imported from the sibling
``apply-agent-research`` skill) and ``proposal_gate.decide`` — as stdin/stdout
subcommands so a workflow can gate on an exit code or parse a JSON decision
from Bash.

It also exposes the **guarded filing path** — ``file`` — which is the *only*
way the skill writes to a tracker. It folds the leak guard and the ``gh``
write into one act: it runs ``sanitizer.check`` on the body and shells to
``gh issue create`` **only on ALLOW**.  The skill never calls ``gh`` directly.

Invoked by file path (``python3 <skill-dir>/lib/cli.py``), not ``-m`` — the
skill folder name is hyphenated.  It bootstraps its own directory AND the
sibling ``apply-agent-research/lib/`` directory onto ``sys.path`` so the
shared helpers (``sanitizer``, ``proposal_gate``) resolve from any cwd.

    # pick the ranked candidates to file, up to the run budget (default 1,
    # hard-capped at 2; exact-key dedup against open issues)
    echo '{"candidates": [...], "open_issues": [...], "budget": 2}' \\
        | python3 <skill-dir>/lib/cli.py gate

    # guarded write: sanitize title+body, then `gh issue create` ONLY on ALLOW
    python3 <skill-dir>/lib/cli.py file --title T --body-file F \\
        --label source:skill-audit [--repo owner/name] [--marker M ...]
"""

import argparse
import json
import os
import subprocess
import sys

# Bootstrap: this skill's own lib/ first, then the sibling apply-agent-research
# lib/ for the shared sanitizer and proposal_gate.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_SIBLING_LIB = os.path.join(
    _THIS_DIR, "..", "..", "apply-agent-research", "lib"
)
sys.path.insert(0, _THIS_DIR)
sys.path.insert(0, os.path.normpath(_SIBLING_LIB))

from proposal_gate import decide  # noqa: E402  (after sys.path bootstrap)
from sanitizer import check  # noqa: E402


def _gate(args, stdin, out):
    payload = json.load(stdin)
    result = decide(
        payload["candidates"],
        payload.get("open_issues", []),
        min_priority=payload.get("min_priority", 1),
        budget=payload.get("budget", 1),
    )
    json.dump(result, out)
    out.write("\n")
    return 0


def _guarded(body, markers, out):
    """Run the leak guard. Return True on ALLOW; print the block reason and
    return False on BLOCK. Single chokepoint: no filing path reaches ``gh``
    without passing the guard first."""
    result = check(body, private_markers=markers or ())
    if result["allowed"]:
        return True
    print(f"BLOCK: {result['reason']}", file=out)
    return False


def _file(args, stdin, out):
    with open(args.body_file, encoding="utf-8") as fh:
        body = fh.read()
    # Guard the full title + body, exactly what reaches the public tracker.
    if not _guarded(f"{args.title}\n{body}", args.marker, out):
        return 1
    cmd = ["gh", "issue", "create", "--title", args.title, "--body-file", args.body_file]
    for label in args.label or ():
        cmd += ["--label", label]
    if args.repo:
        cmd += ["--repo", args.repo]
    # stderr intentionally uncaptured: gh writes diagnostics to stderr directly.
    return subprocess.run(cmd).returncode


def _add_marker(parser):
    parser.add_argument(
        "--marker",
        action="append",
        help="a private marker string; any occurrence blocks (repeatable)",
    )


def main(argv=None, stdin=None, out=None):
    stdin = stdin if stdin is not None else sys.stdin
    out = out if out is not None else sys.stdout

    parser = argparse.ArgumentParser(prog="cli.py")
    sub = parser.add_subparsers(dest="command", required=True)

    p_gate = sub.add_parser(
        "gate", help="pick the budgeted (<=5) ranked candidates to file, from stdin JSON"
    )
    p_gate.set_defaults(func=_gate)

    p_file = sub.add_parser("file", help="guarded gh issue create (sanitize, then file on ALLOW)")
    p_file.add_argument("--title", required=True)
    p_file.add_argument("--body-file", required=True, dest="body_file")
    p_file.add_argument("--label", action="append", help="issue label (repeatable)")
    p_file.add_argument("--repo", help="owner/name; defaults to the current repo / GH_REPO")
    _add_marker(p_file)
    p_file.set_defaults(func=_file)

    args = parser.parse_args(argv)
    return args.func(args, stdin, out)


if __name__ == "__main__":
    sys.exit(main())
