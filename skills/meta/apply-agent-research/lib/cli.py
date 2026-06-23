"""CLI seam over the pure helpers, for the ``apply-agent-research`` skill.

The skill runs unattended in CI and must enforce the leak guard and the
per-run proposal budget *mechanically*, not by prompt discipline. This module exposes
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

**Token selection invariant.** When ``--repo`` is exactly ``dividedby/skills``,
``_gh_env`` injects ``SKILLS_TRACKER_TOKEN`` as ``GH_TOKEN`` in the subprocess
environment — automatically, for every ``gh`` call that targets that repo. Any other
``--repo`` value (or no ``--repo``) keeps the ambient ``GH_TOKEN`` unchanged. The
agent and workflow shell MUST NOT set ``GH_TOKEN`` manually or read the token value;
cli.py owns that selection.

Invoked by file path (``python3 <skill-dir>/lib/cli.py``), not ``-m`` — the skill
folder name is hyphenated, so it is not an importable module. It bootstraps its
own directory onto ``sys.path`` so the sibling imports resolve from any cwd, which
is what lets the helpers travel with the installed skill into a Consumer repo.

    # block iff the body trips the structural guard or names a private marker
    echo "<body>" | python3 <skill-dir>/lib/cli.py sanitize [--marker M ...]

    # pick the ranked candidates to file, up to the run budget (default 1,
    # hard-capped at 2; exact-key dedup against open issues)
    echo '{"candidates": [...], "open_issues": [...], "budget": 2}' \
        | python3 <skill-dir>/lib/cli.py gate

    # guarded write: sanitize title+body, then `gh issue create` ONLY on ALLOW
    python3 <skill-dir>/lib/cli.py file --title T --body-file F \
        --label source:agent-research [--repo owner/name] [--marker M ...]

    # guarded +1 comment: sanitize body, then `gh issue comment` ONLY on ALLOW
    python3 <skill-dir>/lib/cli.py comment --issue N --body-file F \
        [--repo owner/name] [--marker M ...]

    # cross-repo dedup read: print the first open issue number whose body contains
    # <!-- capability: <slug> -->, or nothing on no match; exits non-zero if gh fails
    python3 <skill-dir>/lib/cli.py find-open --repo owner/name \
        --label <label> --capability <slug>

    # allowlist-safe mode discriminator: prints "consumer" or "host" (never the token)
    python3 <skill-dir>/lib/cli.py mode
"""

import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from json_repair import repair_json  # noqa: E402  (after sys.path bootstrap)
from proposal_gate import decide  # noqa: E402
from sanitizer import check  # noqa: E402

# The one repo that requires the cross-repo PAT rather than the ambient GH_TOKEN.
CROSS_REPO = "dividedby/skills"


def _gh_env(repo):
    """Return a subprocess env with GH_TOKEN swapped in for cross-repo writes.

    When ``repo`` is exactly ``dividedby/skills`` and ``SKILLS_TRACKER_TOKEN`` is
    set, GH_TOKEN is overridden with that PAT so gh can write into the tracker
    without the caller ever touching the token value. Any other repo (or no repo)
    keeps the ambient environment unchanged.
    """
    env = os.environ.copy()
    tok = os.environ.get("SKILLS_TRACKER_TOKEN")
    if repo == CROSS_REPO and tok:
        env["GH_TOKEN"] = tok
    return env


def _sanitize(args, stdin, out):
    body = stdin.read()
    result = check(body, private_markers=args.marker or ())
    if result["allowed"]:
        print("ALLOW", file=out)
        return 0
    print(f"BLOCK: {result['reason']}", file=out)
    return 1


def _load_gate_payload(text):
    """Parse the consolidated gate JSON, recovering from common corruption.

    The agent pipes one consolidated object across every channel's candidates, so
    a bare ``json.load`` dropped the whole run on a single malformed blob (#369).
    Mirror the harness publish seam's recovery hierarchy (ADR 0025, loud beats
    lossy — #117):

    1. Clean parse → return dict.
    2. ``JSONDecodeError`` → ``repair_json``, retry once.
       - Repair succeeds → emit ``::warning::`` to stderr, return dict.
       - Repair also fails → raise ``ValueError`` (clear message) so ``_gate``
         can fail loud only when nothing parses.
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError as original_exc:
        try:
            result = json.loads(repair_json(text))
        except json.JSONDecodeError:
            raise ValueError(f"the gate JSON was not valid JSON: {original_exc}") from original_exc
        print(
            f"::warning::the gate JSON was malformed; applied deterministic repair ({original_exc})",
            file=sys.stderr,
        )
        return result


def _gate(args, stdin, out):
    try:
        payload = _load_gate_payload(stdin.read())
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
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
    # stderr intentionally uncaptured: gh writes diagnostics to stderr directly,
    # which a CI log captures without any plumbing on our side.
    return subprocess.run(cmd, env=_gh_env(args.repo)).returncode


def _comment(args, stdin, out):
    with open(args.body_file, encoding="utf-8") as fh:
        body = fh.read()
    if not _guarded(body, args.marker, out):
        return 1
    cmd = ["gh", "issue", "comment", args.issue, "--body-file", args.body_file]
    if args.repo:
        cmd += ["--repo", args.repo]
    # stderr intentionally uncaptured: gh writes diagnostics to stderr directly,
    # which a CI log captures without any plumbing on our side.
    return subprocess.run(cmd, env=_gh_env(args.repo)).returncode


def _mode(args, stdin, out):
    """Print 'consumer' or 'host' depending on whether SKILLS_TRACKER_TOKEN is set.

    This is the allowlist-safe alternative to shell env introspection (``printenv``,
    ``$VAR`` expansion, etc.), which are denied in the scoped sandbox. Never prints
    the token value — only the word 'host' or 'consumer'.
    """
    tok = os.environ.get("SKILLS_TRACKER_TOKEN")
    if tok:
        print("consumer", file=out)
    else:
        print("host", file=out)
    return 0


def _find_open(args, stdin, out):
    """List open issues by label, print the first matching the capability marker.

    Exits non-zero if gh itself fails — a gh failure must never collapse into the
    silent "no match" signal, because that would cause a duplicate file instead of
    a clean +1.
    """
    cmd = [
        "gh", "issue", "list",
        "--repo", args.repo,
        "--label", args.label,
        "--state", "open",
        "--json", "number,body",
        "--limit", "200",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, env=_gh_env(args.repo))
    if result.returncode != 0:
        # Pass gh's stderr through so the caller sees exactly why gh failed.
        print(result.stderr, file=sys.stderr, end="")
        return result.returncode
    marker = f"<!-- capability: {args.capability} -->"
    try:
        issues = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        print(f"ERROR: could not parse gh output: {exc}", file=sys.stderr)
        return 1
    for issue in issues:
        if marker in (issue.get("body") or ""):
            print(issue["number"], file=out)
            return 0
    # No match — empty output, exit 0 (clean "not found" signal).
    return 0


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

    p_gate = sub.add_parser(
        "gate", help="pick the budgeted (<=2) ranked candidates to file, from stdin JSON"
    )
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

    p_mode = sub.add_parser(
        "mode",
        help="print 'consumer' or 'host' (allowlist-safe mode discriminator; never prints the token)",
    )
    p_mode.set_defaults(func=_mode)

    p_find_open = sub.add_parser(
        "find-open",
        help=(
            "list open issues by label, print the number of the first whose body "
            "contains <!-- capability: <slug> -->; empty output = no match"
        ),
    )
    p_find_open.add_argument("--repo", required=True, help="owner/name")
    p_find_open.add_argument("--label", required=True, help="label to filter on")
    p_find_open.add_argument(
        "--capability", required=True, help="capability slug (the <!-- capability: <slug> --> marker)"
    )
    p_find_open.set_defaults(func=_find_open)

    args = parser.parse_args(argv)
    return args.func(args, stdin, out)


if __name__ == "__main__":
    sys.exit(main())
