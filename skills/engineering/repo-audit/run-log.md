# Repo Audit — Run Log

Every run writes `run-log.md` to the scratchpad while it works; `SKILL.md` says
when each section is written. All times are US Central. A guess is one row, a
command is one row, and no raw output is pasted in. The rows below are
illustrative.

## Run

```text
skill commit      | 9f3c2ab
subject commit    | 41d7e60 (branch main)
depth             | standard
ownership test    | fail (remote owner is not the user or an org of theirs)
trust             | untrusted (no override in the prompt)
execute repo code | no (asked 21:03 CT, no answer by 21:05 CT)
```

The `depth` row is `standard` or `quick`, as the prompt set it. The ownership test and trust are written at Stage 1. The execute row holds the
answer (`yes` or `no`) with the time asked and the time answered, or the reason
nobody was asked (`no (not asked: unattended run)`), or `not needed (trusted)`.
A resumed run reads it from here.

## Stages

`agent tokens` is the sum of the tokens the harness reports for the agents that
returned in that stage (`0` when none did). `main context at end` is the main
session's context size when the stage ended. The harness does not report
main-session tokens per stage, so none are recorded.

```text
stage        | start | end   | agent tokens | main context at end
1 Scope      | 21:02 | 21:09 | 146k         | 92k
2 Capture    | 21:09 | 21:21 | 0            | 160k
3 Lenses     | 21:21 | 21:40 | 219k         | 240k
```

## Agents

One row per agent: each lens, and each helper the run used (`rules-harvest`,
`fleet-check`, `findings-extract`; a helper is not a lens). Findings are Blocker
/ High / Med / Low. A lens not launched has no row here; State names it and why.
Status is `running`, `running (retry)`, `done`, `done (not progressive)`,
`partial (reason)` or `failed (reason)`. `partial` keeps some output; `failed` left nothing usable, so
its areas are Not assessed.

```text
lens                   | model  | wall time | tokens | tool uses | findings | status
rules-harvest (helper) | sonnet | 2 min     | 146k   | 16        | n/a      | done
code                   | sonnet | 11 min    | 148k   | 62        | 0/2/5/3  | done
design                 | opus   | 4 min     | 71k    | 24        | 0/1/3/2  | partial (stopped at cap)
```

## Commands

One row per logged command; `SKILL.md` says which.

```text
command                 | wall time | result
cargo test --workspace  | 52 s      | passed, 1,204 tests
terraform validate      | 3 s       | failed: provider plugins not installed, recorded as unverified
```

## Guesses

Each point where the skill was unclear, silent or contradictory, with the choice
made.

```text
# | stage | unclear point                                  | choice made
1 | 1     | profile fact has no file to cite (cadence)     | marked unverified
2 | 2     | no demo mode for a CLI whose output is the UI  | captured output of a sample input
```

## Read-only proof

One `process started` row per instance Stage 2 starts: its role, port, PID, the
background task id and data directory (in the scratchpad), and when it was
stopped. A `process restarted` row for each restart (the main session's curl
before Stage 3 found one down, or the architecture lens restarted the second
one), with the old and new PID and task id, the reason and who restarted it. Stage 6's preview
server is one more row: its port, PID and the publish folder it serves. One
`after gate` row per gate or scan that runs the repo's code, and one per lens
command that runs it, from the per-gate check in
[`baseline.md`](./baseline.md#keeping-the-repo-unchanged): equal to the previous
check, `mtime only` (a directory whose mtime moved with the same status, the same
paths and no newer file: not a change, with the command named), or the breach with
the path. A main-session probe that runs in the repo folder gets the same check
and a `probe` row. Every check compares `HEAD` and saves the path list with the
status; a check's row names the commit it compared with, and a moved `HEAD` gets
its own row. A `nested worktrees excluded` row names the other checkouts left
out of the check. A `HEAD moved` row records an outside change (old and new
commit, time, the check that saw it) and the Stage 1 restart; the rows above it
belong to the abandoned pin, and the rows after it compare with the new Stage 1
snapshot, so the Stage 6 `HEAD` row ends at the new commit. The Stage 6 rows
compare with Stage 1, so a breach found earlier shows there again, along with
the directory that holds it. A breach file is left in place and named in the
closing message.

```text
check                           | before (compared with)   | after
nested worktrees excluded       | Stage 1          | .claude/worktrees/qa-fix-b (another session's), .claude/worktrees/docs-pass
after gate: pnpm lint           | Stage 1 snapshot (41d7e60) | equal (abandoned, redone after the move)
HEAD moved                      | 41d7e60 (Stage 1) | 8c02d19, seen at 21:14 after pnpm lint; paths in git diff --name-only --no-renames 41d7e60 8c02d19 not counted; re-pinned, Stage 1 restarted
after gate: pnpm lint           | Stage 1 snapshot (8c02d19) | equal
after gate: pnpm test           | previous check   | equal
probe: pnpm store path          | previous check   | mtime only: <repo root> (run from the repo; not a change, run from $B/tmp next time)
after gate: swift test          | previous check   | breach: default.profraw (repo root), left in place
after gate: code lens: startup benchmark | lens baseline | equal
Stage 6: git status --porcelain --ignored | Stage 1 snapshot (8c02d19) | differs: default.profraw (the swift test breach)
Stage 6: path list              | Stage 1 snapshot (8c02d19) | differs: default.profraw (the swift test breach)
Stage 6: HEAD                   | 8c02d19          | 8c02d19
Stage 6: files newer than the marker | Stage 1 marker | default.profraw (breach), and <repo root>, which holds it
process started                 | primary :8080 pid 4121 task bk7q2 data $B/data/a | found down at 21:20, before Stage 3 (restarted below)
process started                 | second :8081 pid 4130 task bm3x9 data $B/data/b | stopped 21:31 (restarted below)
process restarted               | primary :8080 pid 4121 -> 4162 task bt5c1 (curl before Stage 3 found it down; main session) | same data $B/data/a; old pid gone; pid 4162 stopped 21:50, before Stage 4
process restarted               | second :8081 pid 4130 -> 4188 task bw8d4 (down-service test; architecture lens) | old pid stopped 21:31; pid 4188 gone after the kill fault, checked 21:50, before Stage 4
process started                 | preview :52814 pid 5230 serving $B/publish | stopped 22:41, before publish
```

## Scrub

One row per published file, from `scrub.py`'s own summary: what the scrub
removed, by category, and what was still there afterwards. Counts and category
names only; a value is never logged. The `run-log.md` row counts what the scrub
removed before this section was written. The `demo data read` row is the
Stage 6 read of demo, fixture and seed data for personal and real-location
facts: what it replaced or retook, by kind. The last row is the result of the
final `--check` over the same files. `literals passed` counts the `--literal`
values given, by kind, never the values.

```text
file               | removed | remaining | by category
page.html          | 4       | 0         | home-path 3, geo 1
findings.json      | 0       | 0         | none
run-log.md         | 2       | 0         | scratch-path 2
architecture.md    | 1       | 0         | token 1
total              | 7       | 0         |
literals passed    | 2 (ZIP, town; from rules.md)
demo data read     | page text and captions read for personal or real-location data: none found
final check        | pass
```

## State

The pinned commit, the stage reached and each lens's status; a resume reads it.
A lens not launched is a row reading `not launched` with its reason: at `quick`,
"Depth: quick run, `<lens>` lens not launched" (its areas are Not assessed
(depth)); for `market`, the failed market test or "standard four-agent cap".

```text
pinned commit | 41d7e60
stage reached | 3 Lenses, in progress
code          | done
design        | partial (stopped at cap)
architecture  | failed (usage limit, retried once)
market        | not launched (standard four-agent cap)
```

## Totals against budget

The budget is the row in [`SKILL.md`](./SKILL.md#lenses-depth-and-budgets) for the
run's depth and tier. Agent tokens include every helper. A measure
over its budget by more than 50% is marked in `over` with by how much, and the
page and the closing message say so. Main-session context is reported, not
budgeted.

```text
measure               | total  | budget          | over
wall time             | 71 min | 45 min          | +58%
agent tokens          | 980k   | 1,120k          | no
main session context  | 415k   | not budgeted    | n/a
```
