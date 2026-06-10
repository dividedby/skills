"""The proposal-loop harness CLI — the drift-prone logic every loop runs.

A **proposal loop** is a scheduled, skill-driven GitHub Actions workflow that
reads some input and *proposes via labeled issues, never applies*. Historically
the parts that are generic across loops — the ``stream-json`` cost scrape and the
``<output>``/``<body>`` publish seam — were hand-written in each repo's workflow
``.yml`` and drifted: the same invalid-JSON fix had to be applied twice, by hand,
in dividedby/skills#119 and dividedby/agent-research#211. This module pulls that
logic onto the same fetch-fresh rail as the skill ([ADR 0008]/[ADR 0014]): repos
commit only the thin **workflow envelope** (cron, permissions, tokens, tool
scoping, a clone-and-invoke body) and call this CLI for the rest, so one fix here
reaches every loop on its next run.

The publish seam is the #117 root cause, so it is a *tested* Python parser, not
brittle ``sed``/``jq`` hand-escaping of JSON (clears the [ADR 0004] "helpers are
stdlib once they earn tests" bar). The pure decisions — ``parse_output``,
``extract_block``, ``parse_digest`` — hold no transport and are unit-tested; the
subcommand handlers add the thin ``gh`` / file-writing shell on top.

Invoked **by file path** (``python3 <clone>/harness/cli.py``), the same way the
skill is, from the workflow stub. Two subcommands:

    # JSONL stream  ->  clean result log + cost-ledger line (shared by all loops)
    python3 harness/cli.py digest --jsonl agent.jsonl \
        --result-out agent.log --cost-out agent.cost

    # result log  ->  parse <output>/<body-N>, file <=5 labeled issues, summarise
    python3 harness/cli.py publish --log agent.log \
        --label source:architecture-review --cost-file agent.cost \
        --heading "Architecture review"
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

# --- pure helpers (no I/O, unit-tested directly) ---------------------------

_NA = "n/a"

# Hard per-run cap on filed issues, enforced in code (not prompt adherence).
# 5 is a ceiling, not a target — the prompts instruct agents to file only
# proposals that would each have cleared the old one-per-run bar on their own.
MAX_PROPOSALS = 5


def extract_block(text, tag):
    """Return the inner text of the LAST ``<tag>…</tag>`` block, or ``None``.

    The agent emits these at the very end of its run; taking the last match is
    robust to the tag name appearing earlier in reasoning. Leading/trailing
    blank lines are stripped; inner content is otherwise verbatim.
    """
    matches = re.findall(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
    if not matches:
        return None
    return matches[-1].strip("\n")


def parse_output(text):
    """Parse the agent's ``<output>`` block into a dict.

    Strips an optional ```json fence inside the block. Raises ``ValueError`` on
    a missing block or invalid JSON — loud beats lossy: an unattended loop that
    "succeeds" with no signal is worse than one that fails visibly (#117).
    """
    block = extract_block(text, "output")
    if block is None:
        raise ValueError("no <output> block found in the agent result")
    block = re.sub(r"^\s*```json\s*$", "", block, flags=re.MULTILINE)
    block = re.sub(r"^\s*```\s*$", "", block, flags=re.MULTILINE).strip()
    if not block:
        raise ValueError("the <output> block was empty")
    try:
        return json.loads(block)
    except json.JSONDecodeError as exc:
        raise ValueError(f"the <output> block was not valid JSON: {exc}") from exc


def parse_proposals(output, text):
    """Resolve a ``status: proposed`` output into ``[{title, oneLineSummary, body}]``.

    Two accepted shapes:

    - **Multi** — ``output["proposals"]`` is a non-empty array of
      ``{title, oneLineSummary}``; each entry's body lives in a matching
      ``<body-1>`` … ``<body-N>`` block (1-indexed, proposal order).
    - **Single (legacy)** — top-level ``title``/``oneLineSummary`` with one
      ``<body>`` block, as every loop emitted before the multi-proposal cap.

    Raises ``ValueError`` on a missing title or a missing body block — loud
    beats lossy (#117). Does NOT cap the list; the caller enforces
    ``MAX_PROPOSALS`` so the truncation is visible at the filing site.
    """
    proposals = output.get("proposals")
    if proposals is not None:
        if not isinstance(proposals, list) or not proposals:
            raise ValueError("status=proposed but 'proposals' is not a non-empty array")
        resolved = []
        for i, p in enumerate(proposals, start=1):
            title = (p or {}).get("title") if isinstance(p, dict) else None
            if not title:
                raise ValueError(f"proposal {i} has no title")
            body = extract_block(text, f"body-{i}")
            if not body:
                raise ValueError(f"proposal {i} ({title!r}) has no <body-{i}> block")
            resolved.append(
                {"title": title, "oneLineSummary": p.get("oneLineSummary", ""), "body": body}
            )
        return resolved

    title = output.get("title")
    body = extract_block(text, "body")
    if not title or not body:
        raise ValueError("status=proposed but title is empty or no <body> block was found")
    return [{"title": title, "oneLineSummary": output.get("oneLineSummary", ""), "body": body}]


def parse_digest(lines):
    """Reduce ``stream-json`` JSONL lines to the run's result + cost fields.

    Returns ``{"result", "total_cost_usd", "duration_ms", "num_turns"}`` taken
    from the LAST ``type == "result"`` event (the whole ``.result`` text, so a
    multi-line ``<output>``/``<body>`` block survives intact). Non-JSON lines are
    skipped. With no result event, ``result`` is ``""`` and the cost fields are
    ``"n/a"`` — a crashed/empty run still produces a well-formed digest.
    """
    last = None
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict) and event.get("type") == "result":
            last = event
    if last is None:
        return {"result": "", "total_cost_usd": _NA, "duration_ms": _NA, "num_turns": _NA}
    return {
        "result": last.get("result") or "",
        "total_cost_usd": last.get("total_cost_usd", _NA),
        "duration_ms": last.get("duration_ms", _NA),
        "num_turns": last.get("num_turns", _NA),
    }


def cost_line(digest):
    """The single cost-ledger line the cross-repo cost hub scrapes from logs."""
    return (
        f"total_cost_usd={digest['total_cost_usd']}  "
        f"duration_ms={digest['duration_ms']}  "
        f"num_turns={digest['num_turns']}"
    )


# --- subcommand handlers (thin transport over the pure helpers) ------------


def _digest(args, out):
    """JSONL -> result log + cost line. Best-effort: never fail the run here.

    pipefail in the workflow already propagates an agent failure; the cost is in
    the log regardless, so a digest hiccup must not mask the real outcome.
    """
    try:
        with open(args.jsonl, encoding="utf-8") as fh:
            digest = parse_digest(fh)
    except OSError:
        digest = {"result": "", "total_cost_usd": _NA, "duration_ms": _NA, "num_turns": _NA}
    with open(args.result_out, "w", encoding="utf-8") as fh:
        fh.write(digest["result"])
    with open(args.cost_out, "w", encoding="utf-8") as fh:
        fh.write(cost_line(digest) + "\n")
    return 0


def _append(path, text):
    if not path:
        return
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(text)


def _summary_proposed(heading, cost, filed, output, truncated=0):
    candidates = output.get("candidatesConsidered") or []
    lines = [
        f"## {heading}",
        "",
        f"**Cost:** {cost}",
        "",
        f"**Created ({len(filed)}):**",
        *[f"- {f['url']} — {f['oneLineSummary']}" for f in filed],
        "",
    ]
    if truncated:
        lines += [
            f"**Truncated:** the agent emitted {truncated} proposal(s) beyond the "
            f"{MAX_PROPOSALS}-per-run cap; they were not filed.",
            "",
        ]
    lines += [
        "### Candidates considered",
        *[f"- {c}" for c in candidates],
        "",
    ]
    return "\n".join(lines)


def _summary_skipped(heading, cost, output):
    return "\n".join(
        [
            f"## {heading}",
            "",
            f"**Cost:** {cost}",
            "",
            "**Skipped — no fresh candidates today.**",
            "",
            output.get("reason", ""),
            "",
        ]
    )


def _publish(args, out):
    """result log -> parse <output>/<body-N>, file <=MAX_PROPOSALS issues, summarise.

    Filing, the provenance label, and the per-run issue cap live here, in code,
    so none of it rests on prompt adherence: proposals beyond ``MAX_PROPOSALS``
    are dropped (visibly, in the summary), never filed. A missing/garbled block
    fails the run (exit 1) without writing a summary — the workflow's
    ``if: failure()`` step then surfaces the raw log. On a clean proposed/skipped
    run this writes the step summary itself, so the stub needs no jq.
    """
    cost = _NA
    if args.cost_file and os.path.exists(args.cost_file):
        with open(args.cost_file, encoding="utf-8") as fh:
            cost = fh.read().strip() or _NA

    with open(args.log, encoding="utf-8") as fh:
        text = fh.read()
    output = parse_output(text)  # raises ValueError -> caught in main(), exit 1

    status = output.get("status")
    summary_file = args.summary_file or os.environ.get("GITHUB_STEP_SUMMARY")

    if status == "skipped":
        reason = output.get("reason", "")
        print(f"SKIPPED: {reason}", file=out)
        _append(summary_file, _summary_skipped(args.heading, cost, output))
        return 0

    if status != "proposed":
        raise ValueError(f"unknown status {status!r} in <output>")

    proposals = parse_proposals(output, text)  # raises ValueError -> exit 1
    truncated = max(0, len(proposals) - MAX_PROPOSALS)
    if truncated:
        print(
            f"WARNING: {len(proposals)} proposals emitted; filing only the "
            f"first {MAX_PROPOSALS} (in-code cap)",
            file=out,
        )
        proposals = proposals[:MAX_PROPOSALS]

    repo = args.repo or os.environ.get("GH_REPO")
    _ensure_label(args.label, args.label_color, args.label_description, repo)

    filed = []
    for proposal in proposals:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".md", delete=False, encoding="utf-8"
        ) as bf:
            bf.write(proposal["body"])
            body_path = bf.name
        try:
            url = _create_issue(proposal["title"], body_path, args.label, repo)
        finally:
            os.unlink(body_path)
        print(f"Published {url}", file=out)
        filed.append({"url": url, "oneLineSummary": proposal["oneLineSummary"]})

    gh_output = args.output_file or os.environ.get("GITHUB_OUTPUT")
    _append(gh_output, f"issue_url={filed[0]['url']}\n")
    _append(gh_output, "issue_urls=" + ",".join(f["url"] for f in filed) + "\n")
    _append(summary_file, _summary_proposed(args.heading, cost, filed, output, truncated))
    return 0


def _ensure_label(label, color, description, repo):
    cmd = ["gh", "label", "create", label, "--color", color]
    if description:
        cmd += ["--description", description]
    if repo:
        cmd += ["--repo", repo]
    # Best-effort: a pre-existing label exits non-zero, which is fine.
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _create_issue(title, body_path, label, repo):
    cmd = ["gh", "issue", "create", "--title", title, "--body-file", body_path, "--label", label]
    if repo:
        cmd += ["--repo", repo]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return result.stdout.strip().splitlines()[-1]


def main(argv=None, out=None):
    out = out if out is not None else sys.stdout

    parser = argparse.ArgumentParser(prog="cli.py")
    sub = parser.add_subparsers(dest="command", required=True)

    p_digest = sub.add_parser("digest", help="JSONL stream -> result log + cost line")
    p_digest.add_argument("--jsonl", required=True)
    p_digest.add_argument("--result-out", required=True, dest="result_out")
    p_digest.add_argument("--cost-out", required=True, dest="cost_out")
    p_digest.set_defaults(func=_digest)

    p_publish = sub.add_parser(
        "publish", help=f"parse <output>/<body-N>, file <={MAX_PROPOSALS} issues, summarise"
    )
    p_publish.add_argument("--log", required=True, help="the agent result log from `digest`")
    p_publish.add_argument("--label", required=True)
    p_publish.add_argument("--label-color", default="5319E7", dest="label_color")
    p_publish.add_argument("--label-description", default="", dest="label_description")
    p_publish.add_argument("--cost-file", dest="cost_file", help="cost line for the summary")
    p_publish.add_argument("--heading", default="Proposal", help="step-summary heading")
    p_publish.add_argument("--repo", help="owner/name; defaults to $GH_REPO")
    p_publish.add_argument("--summary-file", dest="summary_file", help="defaults to $GITHUB_STEP_SUMMARY")
    p_publish.add_argument("--output-file", dest="output_file", help="defaults to $GITHUB_OUTPUT")
    p_publish.set_defaults(func=_publish)

    args = parser.parse_args(argv)
    try:
        return args.func(args, out)
    except ValueError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
