"""CLI seam over the pure helpers, for the ``apply-agent-research`` skill.

The skill runs unattended in CI and must enforce the leak guard and the
one-proposal cap *mechanically*, not by prompt discipline. This module exposes
the two pure decisions — ``sanitizer.check`` and ``proposal_gate.decide`` — as
stdin/stdout subcommands so the workflow can gate on an exit code or parse a JSON
decision from Bash. The decisions themselves hold no transport and live in
``sanitizer.py`` / ``proposal_gate.py``, where they are unit-tested.

It also exposes the **guarded filing path** — ``file`` and ``comment`` — which is
the *only* way the wired loop writes to a tracker. Each folds the leak guard and
the ``gh`` write into one act: it runs ``sanitizer.check`` on the body and shells
to ``gh`` **only on ALLOW**. So "sanitize before filing" is guaranteed by
construction, not by the agent remembering a separate step (the realistic
forgetting-failure). The pure decision stays pure and testable; this seam adds the
thin, gated transport on top — the agent never calls ``gh issue create`` itself.

Invoked by file path (``python3 <skill-dir>/lib/cli.py``), not ``-m`` — the skill
folder name is hyphenated, so it is not an importable module. It bootstraps its
own directory onto ``sys.path`` so the sibling imports resolve from any cwd, which
is what lets the helpers travel with the installed skill into a Consumer repo.

    # block iff the body trips the structural guard or names a private marker
    echo "<body>" | python3 <skill-dir>/lib/cli.py sanitize [--marker M ...]

    # pick at most one candidate to file (exact-key dedup against open issues)
    echo '{"candidates": [...], "open_issues": [...]}' \
        | python3 <skill-dir>/lib/cli.py gate

    # guarded write: sanitize title+body, then `gh issue create` ONLY on ALLOW
    python3 <skill-dir>/lib/cli.py file --title T --body-file F \
        --label source:agent-research [--repo owner/name] [--marker M ...]

    # guarded +1 comment: sanitize body, then `gh issue comment` ONLY on ALLOW
    python3 <skill-dir>/lib/cli.py comment --issue N --body-file F \
        [--repo owner/name] [--marker M ...]
"""

import argparse
import json
import os
import subprocess
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


def _guarded(body, markers, out):
    """Run the leak guard. Return True on ALLOW; print the block reason and
    return False on BLOCK. The single chokepoint both writes go through, so no
    filing path can reach ``gh`` without passing the guard first."""
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
    return subprocess.run(cmd).returncode


def _comment(args, stdin, out):
    with open(args.body_file, encoding="utf-8") as fh:
        body = fh.read()
    if not _guarded(body, args.marker, out):
        return 1
    cmd = ["gh", "issue", "comment", args.issue, "--body-file", args.body_file]
    if args.repo:
        cmd += ["--repo", args.repo]
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

    p_sanitize = sub.add_parser("sanitize", help="leak guard over stdin")
    _add_marker(p_sanitize)
    p_sanitize.set_defaults(func=_sanitize)

    p_gate = sub.add_parser("gate", help="pick <=1 candidate to file, from stdin JSON")
    p_gate.set_defaults(func=_gate)

    p_file = sub.add_parser("file", help="guarded gh issue create (sanitize, then file on ALLOW)")
    p_file.add_argument("--title", required=True)
    p_file.add_argument("--body-file", required=True, dest="body_file")
    p_file.add_argument("--label", action="append", help="issue label (repeatable)")
    p_file.add_argument("--repo", help="owner/name; defaults to the current repo / GH_REPO")
    _add_marker(p_file)
    p_file.set_defaults(func=_file)

    p_comment = sub.add_parser("comment", help="guarded gh issue comment (the +1 path)")
    p_comment.add_argument("--issue", required=True, help="issue number or URL")
    p_comment.add_argument("--body-file", required=True, dest="body_file")
    p_comment.add_argument("--repo", help="owner/name; defaults to the current repo / GH_REPO")
    _add_marker(p_comment)
    p_comment.set_defaults(func=_comment)

    args = parser.parse_args(argv)
    return args.func(args, stdin, out)


if __name__ == "__main__":
    sys.exit(main())
