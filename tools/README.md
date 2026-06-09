# tools

Local maintainer utilities. Not skills, not wired into CI — run by hand.

## `export_scaffolding.py` — agent-meta bundle for external deep research

For each cluster, emits **two files**: a short `<cluster>.prompt.md` you paste
into a deep-research tool (e.g. Perplexity), and a `<cluster>.scaffolding.md` you
**attach** — the repo's agent-meta **surfaces** (CI workflows, system prompts,
helper code, `CLAUDE.md` / `CONTEXT.md` / ADRs) concatenated under `===== path =====`
delimiters, best-effort secret-scrubbed. The prompt carries the task + a fixed
report format and tells the tool to read the attachment. This gives current,
web-sourced improvement ideas for the loops — a human-paced, external complement
to the in-repo `apply-agent-research` / `improve-codebase-architecture` loops.

What each repo exports is declared in its own `tools/scaffolding-export.toml`
(one `[[cluster]]` = one bundle = one prompt), so each repo owns its surface list.

```sh
# this repo: writes scaffolding-export/skills-loops.{prompt,scaffolding}.md
python3 tools/export_scaffolding.py

# another repo that has its own manifest (e.g. the supply-side scout/synth loops)
python3 tools/export_scaffolding.py --repo ../agent-research \
  --out-dir ../agent-research/scaffolding-export

# print the prompt to stdout (attachment still written to a file)
python3 tools/export_scaffolding.py --cluster skills-loops --stdout
```

Then in the deep-research tool: paste `<cluster>.prompt.md` and attach
`<cluster>.scaffolding.md`. Output lands in `scaffolding-export/` (gitignored —
these are generated inputs, never commit them).

Save the report the tool returns (`scaffolding-review-<cluster>-<date>.md`) under
`scaffolding-export/reports/` — also gitignored, separated from the inputs. These
reports are transient: mine the findings into issues, then they're spent. The
durable artifact is the filed issue (with the report's sources), not the report.

**Secret hygiene is best-effort, not a boundary.** It is the manifest's `exclude`
globs plus a token-shape scrubber (`ghp_…`, `sk-…`, AWS keys, `key: <value>`
pairs → `<REDACTED>`; `${{ secrets.X }}` references are left intact). The bundle
header says so. Eyeball every bundle before sending it anywhere external.

Tests (the scrubber and file selection): `python3 -m unittest tools.test_export_scaffolding`.
