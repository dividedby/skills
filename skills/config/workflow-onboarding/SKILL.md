---
name: workflow-onboarding
description: Install the loop-specific surface (LOOP/NETWORK labels + installed-skills snapshot) on a repo being onboarded into a proposal loop. Runs only after setup-dividedby-skills; every network mutation is gated behind explicit confirmation. Manual/slash invocation only.
disable-model-invocation: true
---

# Workflow onboarding

A **composed** pass — run **after** `setup-dividedby-skills` — that installs the loop-specific surface a repo needs when it is being onboarded into a proposal loop (e.g. `apply-agent-research`, `improve-codebase-architecture`).

**What setup-dividedby-skills gives you:** CORE labels, Idea Inbox, branching policy, the Conventions block, and label-convention doc.

**What this skill adds:** the LOOP/NETWORK labels on the target repo and a seeded `docs/agents/installed-skills.md` so remote/CI loops can read the maintainer's global capability set.

**Out of scope:** CHANNELS labels (`skill-request`, `skill-promotion`, `awaiting-corroboration`) — those are owned by `dividedby/skills` and live there only; this skill must not create them on the target.

Every network mutation — label creates — is preceded by a plan you must explicitly confirm. Nothing is written or mutated until you approve.

---

## Before starting

Identify the target repo:
- `cd` into the clone, or set the target explicitly (`gh repo view` to confirm owner/name).
- Confirm `setup-dividedby-skills` has already run (CORE labels present, `docs/agents/triage-labels.md` contains the dividedby tiering structure).
- Read the canonical LOOP/NETWORK section from **`dividedby/skills docs/agents/labels.md`** — the pure function in `skills/config/workflow-onboarding/loop-labels.test.py` defines the authoritative install plan from that source.

---

## Step 1 — Detect

Check what already exists on the target:

**Labels — diff directly, do not delegate:**

```
gh label list --repo {owner}/{repo} --limit 100 --json name,color,description \
  --jq 'sort_by(.name)[] | "\(.name)\t\(.color)\t\(.description)"'
```

Compare against the 5 canonical LOOP/NETWORK labels:

| Label | Color | Description |
| --- | --- | --- |
| `workflow-onboarding` | `0052CC` | Onboarding this repo to a proposal-loop workflow |
| `source:agent-research` | `5319E7` | Filed by the apply-agent-research loop |
| `source:architecture-review` | `5319E7` | Filed by the improve-codebase-architecture loop |
| `source:staleness-review` | `5319E7` | Filed by the staleness-review loop |
| `source:skill-audit` | `5319E7` | Filed by the skill-divergence-audit loop |

For each: **create** if absent, **update** if color or description has drifted, **skip** if correct.

**Installed-skills snapshot:**

Check if `docs/agents/installed-skills.md` exists in the target. Mark **create** if absent, **skip** if present.

Condense findings to a state summary; do not dump raw output.

---

## Step 2 — Draft the plan

From the detect report, produce a per-concern action list.

### Concern A — LOOP/NETWORK labels

One action per label: **create**, **update**, or **skip**. Do not plan any CHANNELS labels (`skill-request`, `skill-promotion`, `awaiting-corroboration`) — those are hub-only and must not appear on the target.

### Concern B — `docs/agents/installed-skills.md`

- **create** if absent: seed from `dividedby/skills docs/agents/installed-skills.md`. Adapt any repo-specific references (the preamble refers to this repo's own skills — update or note that the target maintainer should refresh it to reflect their own global install). The target maintainer refreshes it via:

  ```
  ls ~/.claude/skills/
  python3 -m json.tool ~/.claude/plugins/installed_plugins.json
  claude --version   # for built-in CLI skills
  ```

- **skip** if already present.

This is a local file write in the target clone, not a network mutation — surface it in the plan so the user can approve.

---

## Step 3 — Report and confirm (HITL gate — mandatory)

**Show the full plan before any network mutation or file write.**

Present it as a structured list, grouped by concern (A–B), with one line per action showing posture (create / update / skip) and a brief what/why.

**Do not proceed until the user types explicit confirmation** (e.g. "go", "approved", "yes"). A non-response or an ambiguous reply is not approval.

This gate is non-negotiable — this skill mutates someone's repo over the network.

---

## Step 4 — Execute

Execute the approved plan concern by concern.

**A — LOOP/NETWORK labels:**

For each **create**:
```
gh label create "<name>" --color "<hex>" --description "<desc>" --repo {owner}/{repo}
```

For each **update**:
```
gh label edit "<name>" --color "<hex>" --description "<desc>" --repo {owner}/{repo}
```

Use `--force` on `gh label create` to make it idempotent (creates or updates):
```
gh label create "<name>" --color "<hex>" --description "<desc>" --repo {owner}/{repo} --force
```

Do not create CHANNELS labels. If the plan somehow includes `skill-request`, `skill-promotion`, or `awaiting-corroboration`, stop and surface it — those are out of scope.

**B — `docs/agents/installed-skills.md`:**

Read `dividedby/skills docs/agents/installed-skills.md`. Adapt the preamble to reference the target repo. Write to `docs/agents/installed-skills.md` in the target clone. Note in a code comment or the seeded doc that the maintainer should refresh the skill lists to match their own global install using the commands in the Refreshing section.

---

## Step 5 — Verify

After execution:

- Re-run the label list and confirm all 5 LOOP/NETWORK labels are present with correct color and description.
- Confirm CHANNELS labels are absent.
- Confirm `docs/agents/installed-skills.md` exists in the target.

Report a short summary: what was created, what was updated, what was skipped. Surface any drift — do not silently leave it.

---

## Idempotency guarantee

Re-running this skill on a fully-set-up repo must produce no mutations. Every action check uses the current live state. "Skip" should be the dominant outcome on a second pass.
