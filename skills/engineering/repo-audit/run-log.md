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

```text
stage        | start | end
1 Scope      | 21:02 | 21:09
2 Capture    | 21:09 | 21:21
3 Lenses     | 21:21 | 21:40
```

## Agents

One row per agent: each lens, and the rules-harvest helper when Stage 1 used
one (it is not a lens). Findings are Blocker / High / Med / Low. A lens not
launched has no row here; State names it and why. Status is `running`, `running (retry)`, `done`, `partial (reason)` or
`failed (reason)`. `partial` keeps some output; `failed` left nothing usable, so
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

One `process started` row per instance Stage 2 starts: its role, port, PID and
data directory (in the scratchpad), and when it was stopped. One `after gate`
row per gate or scan that runs the repo's code, from the per-gate check in
[`baseline.md`](./baseline.md#setup): equal to the previous check, or the breach
with the path. The Stage 1 and Stage 6 rows compare with Stage 1. A breach file is left in place and named in the closing message.

```text
check                           | before (compared with)   | after
git status --short              | clean            | clean
git status --porcelain --ignored| Stage 1 snapshot  | equal to Stage 1
HEAD                            | 41d7e60          | 41d7e60
files newer than the marker     | Stage 1 marker   | none
after gate: swift test          | previous check   | breach: default.profraw (repo root), left in place
process started                 | primary :8080 pid 4121 data $B/data/a | stopped 21:20
process started                 | second :8081 pid 4130 data $B/data/b | stopped 21:20, before Stage 4
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
run's depth and tier. Agent tokens include the rules-harvest helper. A measure
over its budget by more than 50% is marked in `over` with by how much, and the
page and the closing message say so. Main-session context is reported, not
budgeted.

```text
measure               | total  | budget          | over
wall time             | 71 min | 45 min          | +58%
agent tokens          | 980k   | 1,120k          | no
main session context  | 415k   | not budgeted    | n/a
```
