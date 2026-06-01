"""CLI seam over the pure helpers, for the ``apply-agent-research`` skill.

The skill runs unattended in CI and must enforce the leak guard and the
one-proposal cap *mechanically*, not by prompt discipline. This module exposes
the two pure decisions — ``sanitizer.check`` and ``proposal_gate.decide`` — as
stdin/stdout subcommands so the workflow can gate on an exit code or parse a JSON
decision from Bash. It holds no policy of its own; the decisions live in
``sanitizer.py`` / ``proposal_gate.py`` and are tested there.

Invoked by file path (``python3 <skill-dir>/lib/cli.py``), not ``-m`` — the skill
folder name is hyphenated, so it is not an importable module. It bootstraps its
own directory onto ``sys.path`` so the sibling imports resolve from any cwd, which
is what lets the helpers travel with the installed skill into a Consumer repo.

    # block iff the body trips the structural guard or names a private marker
    echo "<body>" | python3 <skill-dir>/lib/cli.py sanitize [--marker M ...]

    # pick at most one candidate to file (exact-key dedup against open issues)
    echo '{"candidates": [...], "open_issues": [...]}' \
        | python3 <skill-dir>/lib/cli.py gate
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from proposal_gate import decide  # noqa: E402  (after sys.path bootstrap)
from sanitizer import check  # noqa: E402


def _sanitize(args, stdin, out):
    body = stdin.read()
    result = check(body, private_markers=args.marker or ())
    if result["allowed"]:
        print("ALLOW", file=out)
        return 0
    print(f"BLOCK: {result['reason']}", file=out)
    return 1


def _gate(args, stdin, out):
    payload = json.load(stdin)
    result = decide(
        payload["candidates"],
        payload.get("open_issues", []),
        min_priority=payload.get("min_priority", 1),
    )
    json.dump(result, out)
    out.write("\n")
    return 0


def main(argv=None, stdin=None, out=None):
    stdin = stdin if stdin is not None else sys.stdin
    out = out if out is not None else sys.stdout

    parser = argparse.ArgumentParser(prog="cli.py")
    sub = parser.add_subparsers(dest="command", required=True)

    p_sanitize = sub.add_parser("sanitize", help="leak guard over stdin")
    p_sanitize.add_argument(
        "--marker",
        action="append",
        help="a private marker string; any occurrence blocks (repeatable)",
    )
    p_sanitize.set_defaults(func=_sanitize)

    p_gate = sub.add_parser("gate", help="pick <=1 candidate to file, from stdin JSON")
    p_gate.set_defaults(func=_gate)

    args = parser.parse_args(argv)
    return args.func(args, stdin, out)


if __name__ == "__main__":
    sys.exit(main())
