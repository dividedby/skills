# Repo Audit — Run Log

Every run writes `run-log.md` to the scratchpad while it works; `SKILL.md` says
when each section is written. All times are US Central. A guess is one row, a
command is one row, and no raw output is pasted in. The rows below are
illustrative.

## Run

```text
skill commit      | 9f3c2ab
subject commit    | 41d7e60 (branch main)
ownership test    | fail (remote owner is not the user or an org of theirs)
trust             | untrusted (no override in the prompt)
execute repo code | no (asked 21:03 CT, no answer by 21:05 CT)
```

The ownership test and trust are written at Stage 1. The execute row holds the
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

One row per agent. Findings are Blocker / High / Med / Low.
Status is `running`, `running (retry)`, `done`, `partial (reason)` or
`failed (reason)`. `partial` keeps some output; `failed` left nothing usable, so
its areas are Not assessed.

```text
lens    | model  | wall time | tokens | tool uses | findings | status
code    | sonnet | 11 min    | 148k   | 62        | 0/2/5/3  | done
design  | opus   | 4 min     | 71k    | 24        | 0/1/3/2  | partial (stopped at cap)
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
data directory (in the scratchpad), and when it was stopped.

```text
check                           | before           | after
git status --short              | clean            | clean
git status --porcelain --ignored| saved snapshot   | equal to before
HEAD                            | 41d7e60          | 41d7e60
files newer than the marker     | (marker made)    | none
process started                 | primary :8080 pid 4121 data $B/data/a | stopped 21:20
process started                 | second :8081 pid 4130 data $B/data/b | stopped 21:20, before Stage 4
```

## State

The pinned commit, the stage reached and each lens's status; a resume reads it.

```text
pinned commit | 41d7e60
stage reached | 3 Lenses, in progress
code          | done
design        | partial (stopped at cap)
architecture  | failed (usage limit, retried once)
```

## Totals against budget

Until a depth budget is set, totals only.

```text
measure       | total  | budget
wall time     | 41 min | none set
agent tokens  | 410k   | none set
```
