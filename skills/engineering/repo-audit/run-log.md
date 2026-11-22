# Repo Audit — Run Log

Every run writes `run-log.md` to the scratchpad while it works; `SKILL.md` says
when each section is written. All times are US Central. A guess is one row, a
command is one row, and no raw output is pasted in. The rows below are
illustrative.

## Run

```text
skill commit    | 9f3c2ab
subject commit  | 41d7e60 (branch main)
```

## Stages

```text
stage        | start | end
1 Scope      | 21:02 | 21:09
2 Capture    | 21:09 | 21:21
3 Lenses     | 21:21 | 21:40
```

## Agents

One row per agent. Findings are High / Med / Low.
Status is `running`, `running (retry)`, `done`, `partial (reason)` or
`failed (reason)`. `partial` keeps some output; `failed` left nothing usable, so
its areas are Not assessed.

```text
lens    | model  | wall time | tokens | tool uses | findings | status
code    | sonnet | 11 min    | 148k   | 62        | 2/5/3    | done
design  | opus   | 4 min     | 71k    | 24        | 1/3/2    | partial (stopped at cap)
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

```text
check                    | before          | after
git status --short       | clean           | clean
HEAD                     | 41d7e60         | 41d7e60
untracked, ignored files | build/ ignored  | build/ ignored, nothing new
process started          | dev server :8080| stopped 21:20
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
