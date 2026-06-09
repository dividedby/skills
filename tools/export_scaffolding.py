#!/usr/bin/env python3
"""Bundle a repo's agent-meta surfaces into a markdown report for external deep research.

Deterministic file-gathering: read a per-repo manifest (tools/scaffolding-export.toml),
concatenate the files each cluster names into one markdown bundle, prepend the
deep-research task + required output format, and run a best-effort secret scrub.
No agent, no network, stdlib only — run it locally and paste the output into a
deep-research tool (e.g. Perplexity).

    python3 tools/export_scaffolding.py                 # this repo, all clusters
    python3 tools/export_scaffolding.py --repo ../agent-research
    python3 tools/export_scaffolding.py --cluster skills-loops --stdout

"best-effort secret-scrubbed" is exactly that: an allowlist manifest plus a token
regex pass, NOT a security boundary. Eyeball every bundle before sending it out.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import fnmatch
import glob
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

# --- the two outputs per cluster: a prompt you paste, a file you attach ---------
# Perplexity deep research (and most chat UIs) take a typed prompt plus an
# attachment, so we emit them separately: PROMPT_TEMPLATE is what you paste,
# SCAFFOLDING_HEADER tops the file you attach.

PROMPT_TEMPLATE = """\
# Deep-research prompt — {title}

Repo `{repo}` @ `{sha}` · cluster `{name}` · generated {ts}

**Attach the file `{scaffolding_file}` to this conversation, then send the prompt
below.**

---

You are reviewing the agent-meta **scaffolding** in the attached file
`{scaffolding_file}` — the CI workflows, system prompts, helper code, and
governing docs (CLAUDE.md, CONTEXT.md, ADRs) that run a set of unattended,
Claude-powered agent loops. Each file in it sits under a `===== path =====`
delimiter. Find concrete, **current-sourced** opportunities to improve this
scaffolding: outdated assumptions, missing safeguards, better prompt or agent
patterns, newer model/API/tooling features, and gaps versus today's published
best practice for autonomous / agentic LLM workflows.

Ground every finding in up-to-date web sources and cite them. Prefer primary
sources — provider docs, framework docs, well-known practitioners — over
listicles. Read what is actually in the attached file; do not invent capabilities
the code does not have.

## Gating discipline — apply to every candidate BEFORE you write it up

This scaffolding is already deliberately designed. Most candidate "findings" are
noise; your job is to surface only the few that survive every gate below. Drop —
do not weaken, drop — any candidate that fails one:

1. **Contradiction gate.** Does it conflict with a decision already documented in
   the bundle (an ADR under `docs/adr/`, a `CONTEXT.md` choice, a `CLAUDE.md`
   rule)? The repo deciding *against* something on purpose is not a gap. If your
   recommendation argues against a documented decision, drop it (or, at most, note
   the decision and why you think it's worth revisiting — never propose as if the
   decision didn't exist).
2. **Already-encoded gate.** Does the bundle already do this, or already track it
   (an open issue, a TODO, an ADR that names it as future work)? If so, drop it.
3. **Source gate.** Is the claim grounded in a *primary, verifiable* source you
   can actually link? Be especially skeptical of dramatic security claims (named
   CVEs, "disclosure", "advisory", breach counts) — if you cannot cite a primary
   source that says exactly what you claim, drop the finding. Do not manufacture
   urgency from secondary blog posts.
4. **Reality gate.** A claim about how a tool, flag, API, model, or version
   behaves may be marked *verified* **only** if you fetched the primary source in
   this session and can quote its **actual** text. You may NOT satisfy this gate
   from memory, from a paraphrase, or by reconstructing what a doc "would say."
   Inventing, approximating, or attributing a quote you did not actually retrieve
   is a disqualifying error — drop the finding entirely. If you did not
   fetch-and-quote, the verification stays **outstanding**: keep the finding only
   if it is still worth a human's time, set **Confidence: low**, and put the exact
   unresolved check on the `Verification` line (below). Never upgrade a recalled
   fact into a "confirmed" one to make a finding pass.

**Zero findings is a fully acceptable, even expected, report.** A short report of
1–3 genuinely strong findings is worth far more than a padded list. Do not invent
findings to fill space.

## Required output format

Produce a single markdown report in exactly this structure:

```
# Scaffolding Review — {name} — <today's date>

## Summary
<2–3 sentences: the through-line of what you found>

## Findings
<for each finding, strongest first>
### N. <title>   [category: defect | deepening | new-source]
- **Surface:** <which file / workflow / doc it touches>
- **Observation:** <what is weak, dated, or missing now — quote the current text>
- **Recommendation:** <the single concrete change to make>
- **Sources:** <1–3 primary URLs, each with a publication or access date>
- **Confidence:** <high | medium | low>
- **Verification:** <"verified in-session: <quote actual fetched text>", OR the
  exact unresolved check a human must run before acting — e.g. "confirm `--flag`
  exists via `tool --help`", "confirm model ID in the provider catalog". Required
  whenever the recommendation depends on a tool/flag/API/model/version behaving as
  claimed. If unresolved, Confidence must be `low`.>

## Sources consulted
<deduped list of every URL cited above>
```

Rules: **one recommendation per finding** (no menus — alternatives go in a one-line
aside). Separate what is *broken now* from what *could* be sharpened. Every finding
must have passed the four gates above. If nothing survives, say so plainly — zero
strong findings is an acceptable and common report; never pad.

Deliver the report as a downloadable markdown file named exactly
`{report_file}` (substitute today's date for `<YYYY-MM-DD>`).
"""

SCAFFOLDING_HEADER = """\
> ⚠️ **Generated scaffolding bundle — best-effort secret-scrubbed, NOT guaranteed
> clean. Eyeball before sending anywhere external.**

# Agent-meta scaffolding — {title}

Repo `{repo}` @ `{sha}` · cluster `{name}` · generated {ts}

Each file below sits under a `===== path =====` delimiter. Reviewed by the
companion prompt in `{prompt_file}`.
"""

# --- best-effort secret scrubbing ---------------------------------------------
# These redact obvious secret *values*. `${{ secrets.NAME }}` references carry no
# value and are intentionally left intact (the template token has no long secret).

_SCRUB_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"gho_[A-Za-z0-9]{20,}"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),           # OpenAI / Anthropic-style keys
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),    # Slack
    re.compile(r"AKIA[0-9A-Z]{16}"),                # AWS access key id
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]

# key: value / key=value where the value is a long opaque token (not a ${{ ... }} ref).
_KV_SECRET = re.compile(
    r"(?i)\b(token|secret|api[_-]?key|apikey|password|passwd|access[_-]?key|"
    r"client[_-]?secret|bearer)\b(\s*[:=]\s*)"
    r"(?!\$\{\{)"                       # skip GitHub Actions secret references
    r"(['\"]?)([A-Za-z0-9/+_.\-]{16,})\3"
)


def scrub(text: str) -> tuple[str, int]:
    """Redact obvious secret values. Returns (scrubbed_text, redaction_count)."""
    count = 0

    def _kv(m: re.Match[str]) -> str:
        nonlocal count
        count += 1
        return f"{m.group(1)}{m.group(2)}{m.group(3)}<REDACTED>{m.group(3)}"

    text = _KV_SECRET.sub(_kv, text)
    for pat in _SCRUB_PATTERNS:
        text, n = pat.subn("<REDACTED>", text)
        count += n
    return text, count


# --- file selection ------------------------------------------------------------


def _excluded(rel: str, patterns: list[str]) -> bool:
    base = os.path.basename(rel)
    for p in patterns:
        # fnmatch's '*' already spans '/', but a leading '**/' still demands at
        # least one slash, so root-level files slip past '**/*secret*'. Also try
        # the pattern with the leading '**/' dropped (matches zero directories).
        forms = {p, p[3:]} if p.startswith("**/") else {p}
        if any(fnmatch.fnmatch(rel, f) or fnmatch.fnmatch(base, f) for f in forms):
            return True
    return False


def select_files(root: Path, include: list[str], exclude: list[str]) -> list[Path]:
    """Resolve include globs (minus excludes) into a sorted, de-duplicated list."""
    seen: dict[str, Path] = {}
    for pattern in include:
        for hit in glob.glob(str(root / pattern), recursive=True):
            p = Path(hit)
            if not p.is_file():
                continue
            rel = p.relative_to(root).as_posix()
            if _excluded(rel, exclude):
                continue
            seen[rel] = p
    return [seen[k] for k in sorted(seen)]


# --- bundle assembly -----------------------------------------------------------


def _git_sha(root: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip() or "unknown"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def build_bundle(root: Path, repo: str, cluster: dict) -> tuple[str, str, int, int]:
    """Return (prompt_md, scaffolding_md, file_count, redaction_count) for a cluster.

    Two documents: the prompt you paste, and the scaffolding file you attach. They
    cross-reference each other by filename.
    """
    name = cluster["name"]
    prompt_file = f"{name}.prompt.md"
    scaffolding_file = f"{name}.scaffolding.md"
    fields = dict(
        title=cluster.get("title", name), name=name, repo=repo,
        sha=_git_sha(root), ts=_dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        prompt_file=prompt_file, scaffolding_file=scaffolding_file,
        report_file=f"scaffolding-review-{name}-<YYYY-MM-DD>.md",
    )

    files = select_files(root, cluster.get("include", []), cluster.get("exclude", []))
    parts = [SCAFFOLDING_HEADER.format(**fields)]
    redactions = 0
    for p in files:
        rel = p.relative_to(root).as_posix()
        body, n = scrub(p.read_text(encoding="utf-8", errors="replace"))
        redactions += n
        parts.append(f"\n\n===== {rel} =====\n\n{body.rstrip()}\n")
    return PROMPT_TEMPLATE.format(**fields), "\n".join(parts), len(files), redactions


def load_manifest(root: Path) -> dict:
    path = root / "tools" / "scaffolding-export.toml"
    if not path.is_file():
        sys.exit(f"no manifest at {path} — this repo has no scaffolding-export.toml")
    return tomllib.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", default=".", help="repo root to export (default: cwd)")
    ap.add_argument("--cluster", help="only this cluster (default: all in manifest)")
    ap.add_argument("--out-dir", default="scaffolding-export",
                    help="write <cluster>.prompt.md + .scaffolding.md here "
                         "(default: ./scaffolding-export/)")
    ap.add_argument("--stdout", action="store_true",
                    help="print the prompt to stdout (scaffolding still written to "
                         "a file, since it is the attachment); one cluster only")
    args = ap.parse_args(argv)

    root = Path(args.repo).resolve()
    manifest = load_manifest(root)
    repo = manifest.get("meta", {}).get("repo", root.name)
    clusters = manifest.get("cluster", [])
    if args.cluster:
        clusters = [c for c in clusters if c["name"] == args.cluster]
        if not clusters:
            sys.exit(f"no cluster named {args.cluster!r} in manifest")
    if args.stdout and len(clusters) != 1:
        sys.exit("--stdout needs exactly one cluster; pass --cluster NAME")

    out_dir = Path(args.out_dir).resolve()
    for cluster in clusters:
        prompt_md, scaffolding_md, n_files, n_red = build_bundle(root, repo, cluster)
        out_dir.mkdir(parents=True, exist_ok=True)
        scaffolding_dest = out_dir / f"{cluster['name']}.scaffolding.md"
        scaffolding_dest.write_text(scaffolding_md, encoding="utf-8")
        if args.stdout:
            sys.stdout.write(prompt_md)
            print(f"\n(wrote attachment {scaffolding_dest}, "
                  f"{n_files} files, {n_red} redactions)", file=sys.stderr)
            continue
        prompt_dest = out_dir / f"{cluster['name']}.prompt.md"
        prompt_dest.write_text(prompt_md, encoding="utf-8")
        print(f"wrote {prompt_dest}", file=sys.stderr)
        print(f"wrote {scaffolding_dest}  ({n_files} files, {n_red} redactions)",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
