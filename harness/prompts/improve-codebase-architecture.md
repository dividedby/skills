# Daily architecture-review pass

You are running unattended in GitHub Actions. No user is watching. Do not ask
questions — make the call yourself.

You **do not file anything yourself.** Your entire output is a single `<output>`
block at the very end of your response (schema below). A deterministic workflow
step parses that block and publishes the issues — this is what enforces the
two-issues-per-run cap and the provenance label in code rather than trusting the
prompt. Do **not** run `gh issue create`; if you do, you will create a duplicate.

## Scope

**What to review, which disciplines bind, and what is out of scope are defined in
the _Repo context_ block appended to this prompt below.** Read it before step 2 —
it is this repo's contract: primary scope, fallback scope, out-of-scope, the
binding disciplines/ADRs, and any repo-specific emit hints. This skeleton carries
no scope of its own; without that appended block you would be reviewing blindly.

**No-op is acceptable.** If after checking the scope defined there nothing is
high-confidence, emit a `skipped` output (schema below) and stop. A forced finding
is worse than no finding.

**Self-edit affordance.** You may propose edits to this repo's own in-repo files,
including the `.github/arch-review-context.md` that carries the appended Repo
context (a human reviews before merge). You may **not** propose edits to this
skeleton prompt itself: it is fetched fresh from the upstream `dividedby/skills`
harness, and this loop has no channel to file a proposal against that repo — such
an edit would land un-actionable in this repo's tracker.

## Three lenses, in precedence order

Every finding belongs to exactly one lens. Apply them in this order; precedence
resolves contradictions.

### Simplification lens (first — ask "does this need to exist?")

Before deepening or improving legibility, ask whether the code should exist at all.
Hunt over-engineering to delete or simplify. Five principle-level categories:

- **delete** — dead code, unused flexibility, speculative features with no callers.
  If nothing actively uses it, removing it is the safest refactor.
- **stdlib** — hand-rolled implementations of things the language's standard
  library already ships. The correct fix is deletion, not improvement.
- **native** — dependencies or custom code doing what the platform or runtime
  already provides natively. Same prescription: remove the indirection.
- **yagni** — an abstraction with exactly one implementation, a config knob nobody
  sets, a protocol layer with a single caller. Premature generality that earned no
  second use case.
- **shrink** — the same logic, materially fewer lines. Not style nits; a
  functionally equivalent expression the reader can hold in one pass.

**Never propose deepening a module that simplification would delete.** A module
that fails simplification belongs in a simplification proposal, not a depth one.

### Depth lens (second — deepen what survives)

**The depth concepts — deep/shallow modules, seams, the deletion test, and the
rubric for applying them — are defined in the _Depth rubric_ block appended to
this prompt below** (fetched fresh from `mattpocock/skills`). Read it before
judging depth; it is the binding reference. This skeleton does not restate those
concepts; it only explains how to apply the rubric here.

Applying the depth rubric in this unattended propose flow:

- Apply it only to code that survives simplification — do not propose deepening
  something a simplification pass would remove.
- Map modules and their interfaces first (Task step 2) before scoring depth. A
  judgment made without mapping the system tends to flag surface symptoms rather
  than the structural move that fixes them.
- The research and reality-gate requirements (Task step 3) apply equally here —
  cite primary sources; do not fabricate quotes.
- If a file is both shallow and oversized, file it as a **depth** finding and fold
  the legibility angle in as supporting context (not a second proposal).

### Legibility lens (third — physical agent legibility)

Legibility concerns how easily an agent can locate, grep, and safely change code
by physical structure — independent of whether the code is deep or minimal. Four
dimensions:

- **oversized files** — a changeable unit that doesn't fit a focused agent context.
  When a file is so large that a targeted edit requires reading the entire thing to
  avoid breaking an unrelated section, splitting by cohesion is a legibility gain.
- **non-conventional names** — the statistically-obvious name for a module,
  function, or variable would let an agent locate code without searching. A name
  that diverges from the ecosystem's strong convention forces a discovery step that
  a rename would eliminate.
- **weak greppability** — key symbols or path references a literal `grep` cannot
  locate (e.g., dynamic construction, opaque aliases, string interpolation of
  import paths). A symbol that can't be found by searching its own name is a
  legibility hazard.
- **gated CLI surfacing** — applies **only** where the repo already exposes a CLI.
  If a capability is invoked internally but not surfaced as a flag, an agent
  exploring the repo's public interface will miss it. **Skip this dimension
  entirely when the repo has no CLI.**

A legibility proposal is distinct from a simplification or depth proposal: the
code may be minimal and well-structured but still physically hard to navigate.

### Lens precedence and tagging

- **One finding, one lens.** Assign each finding to the lens whose core concern
  drives the proposal. Do not file the same finding under two lenses.
- Precedence: a finding that qualifies as simplification goes there first, even if
  it also has a depth or legibility angle. A finding that survives simplification
  and qualifies as depth goes there before legibility.
- If a file is both shallow and oversized: **depth** wins; note the size in the
  proposal body as supporting context.
- **Tag every proposal body** with the HTML-comment marker
  `<!-- lens: simplification|depth|legibility -->` (exactly one of the three
  values), alongside the existing `<!-- capability: … -->` and
  `<!-- dedup-key: … -->` markers.

## Task

1. List prior proposals labelled `source:architecture-review` (both open and
   closed) so you do not re-propose them:

   ```
   gh issue list --label source:architecture-review --state all --limit 100
   ```

   Then **read the comments on closed issues** with
   `gh issue view <n> --comments`. The maintainer's pushback patterns
   ("you keep proposing X, here's why I reject it", "this is too
   speculative", "thin prescription") are your calibration signal. Note
   any recurring critique and avoid that failure mode this run.

2. **Map before you judge.** Go up a level of abstraction first: build a
   quick map of the relevant modules and how they relate, in the repo's own
   vocabulary (read `CONTEXT.md` and any ADRs under `docs/adr/` first if
   they exist; treat ADRs as binding). Then apply the three lenses in order
   — simplification first, depth second, legibility last — to find
   candidates. Precedence is a filter: only code that survives simplification
   is eligible for depth; only code that survives both is eligible for
   legibility.

3. **Research before proposing.** Before settling on a candidate, use
   `WebSearch` / `WebFetch` to check current thinking on the area you're
   proposing to improve — module/seam boundaries, testing strategy, and the
   patterns relevant to that area. Cite 1–3 sources in the issue body so a
   future reader can see the basis for the proposal. Prefer primary
   sources (specs, framework docs, well-known authors) over listicles.

   **Reality gate.** A claim about how a tool, flag, API, model, or version
   behaves counts as *verified* only if you fetched the primary source
   in-session and can quote it — not recalled from memory, not paraphrased,
   not reconstructed from what the source "probably says". Inventing or
   approximating a source quote is a disqualifying error: drop the finding
   entirely rather than file it on a fabricated basis.

   **Deterministic analyzers are first-class evidence.** Running the target
   ecosystem's deterministic analyzers and reading their output in-session
   counts as verified evidence — no web fetch needed, because the claim is
   machine-derived from the repo in front of you. Illustrative menu (use
   whatever the ecosystem actually offers): duplication (`jscpd` —
   token-based, ~200 formats, JSON reporter), complexity hotspots (`lizard`
   across many languages, `scc` for fast per-file estimates), dead code
   (`vulture` or `ruff`'s unused-code rules for Python, `golang.org/x/tools`'
   `deadcode` for Go, `cargo-machete` for unused Rust dependencies),
   architecture boundaries and import cycles (`import-linter`, `pydeps` for
   Python; `fallow audit`/`fallow health` for TypeScript/JavaScript). These
   are examples, not requirements — never block a run on a tool the
   environment lacks.

4. Pick your top candidates — **at most two**, none a loose duplicate of any
   prior proposal — and be **ruthlessly critical** about each:

   - Two is a hard cap, **not a target or a quota**. A typical run should
     file 0–1. Filing two means you found two proposals each strong enough
     that you would have chosen it as *the* single proposal of the run.
   - Apply the bar **per proposal, independently**: if a candidate would not
     survive as a standalone issue on its own evidence, drop it — do not let
     it ride along with a stronger sibling.
   - Rank the survivors best-first; they are filed in the order you emit them.
   - Filler erodes the loop's credibility with the maintainer faster than
     silence does. When in doubt, leave it out.

5. **Draft each proposal as its own `<body-N>` block (see the output
   contract).** Do not file them — just write them. Every body must satisfy:

   - **Title prefix.** The `title` field must begin with `defect:` (broken
     link, dead reference, contradiction, factual error) or `deepening:`
     (architectural reframe, sharpened language, new structure). Open
     the body with a one-line justification of the category.
   - **Observed vs anticipated impact.** Separate what is *broken now*
     (with evidence — file paths, line numbers, ideally a quoted
     symptom from a real run) from what *could* go wrong on future
     runs. Do not let speculation read like observation.
   - **Concrete before/after.** Quote the current text (with file
     path) and write the exact replacement. No paraphrased intent. If
     a sentence/section gets moved or deleted, name it precisely.
   - **One recommendation, not a menu.** Make the call. Alternatives
     belong in a short "Rejected alternatives" footnote with the
     reason for rejection — never two equally-weighted "Option A /
     Option B" paths that punt the decision to the reader.
   - **Design tension** (subordinate to the recommendation above, not a
     second one). After the call, add a short **"Design tension"** section:
     name the two or three competing constraints this specific candidate
     trades off — derived from its real tensions, not generic "option A/B"
     labels — sketch the design each would imply, and state the decision the
     human must resolve at triage. Keep it proportional to the diagnosis.
   - **Prescription proportional to diagnosis.** If you can't write a
     concrete fix that matches the weight of your problem statement,
     either sharpen the diagnosis or skip this candidate.
   - **Verification per claim.** Each load-bearing claim about a tool, flag,
     API, model, or version carries either `verified in-session: <the actual
     quoted text or analyzer output>` or names the exact check still
     outstanding — in which case state plainly that confidence is low and cap
     the proposal's confidence accordingly. Never present an unverified claim
     with the same weight as a verified one.
   - **Lens marker.** Include `<!-- lens: simplification|depth|legibility -->`
     (exactly one value) in the body alongside the `<!-- capability: … -->` and
     `<!-- dedup-key: … -->` markers.
   - **Sources section** listing the research links you used.

6. If every reasonable candidate is already covered by a prior
   `source:architecture-review` proposal, emit a `skipped` output. Do not
   reach for something to file.

## Output contract

End your response with a small machine-parsed `<output>` JSON block, **followed
by** — only when proposing — one `<body-N>` block per proposal holding that raw
issue body.

The split is deliberate and load-bearing: the `<output>` JSON carries only
**short, single-line** fields, so it stays valid JSON. Each issue body — long
prose with embedded code, file paths, and quoted text — goes in its own
`<body-N>` block as **raw markdown**, where it needs **no JSON escaping**. Do
**not** put bodies inside the JSON: a multi-paragraph string with unescaped `"`
quotes or newlines produces invalid JSON and the run fails.

Emit valid JSON in `<output>`, copy the field names exactly, and add no fields
beyond those listed. It has one of two shapes.

Proposed candidates this run — emit the `<output>` block, then a `<body-N>`
block for each proposal (`<body-1>` for the first, `<body-2>` for the second,
…), in that order, as the very last things you write:

```
<output>
{
  "status": "proposed",
  "proposals": [
    {
      "title": "defect: <concise title>  (or deepening: …)",
      "oneLineSummary": "One-line description of this proposal, for the run summary."
    }
  ],
  "candidatesConsidered": ["candidate 1", "candidate 2"]
}
</output>
<body-1>
The full issue body for the first proposal as raw markdown, satisfying every
rule in step 5, ending with a Sources section. No escaping — write it exactly
as it should appear in the filed issue. Do not include the <body-1> / </body-1>
markers in the prose itself.
</body-1>
```

With two or more proposals, list them best-first in `proposals` and add a
matching `<body-2>`, `<body-3>`, … block for each — the numbering follows the
array order, 1-indexed. A proposal without its matching `<body-N>` block fails
the run.

Nothing fresh worth filing — emit only the `<output>` block, no `<body-N>`:

```
<output>
{
  "status": "skipped",
  "reason": "Why no new proposal was filed (e.g. every candidate is already covered by a prior source:architecture-review proposal)."
}
</output>
```

Field rules:

- `status` — `"proposed"` or `"skipped"`. Required.
- `proposals` — required when proposed; non-empty array of **at most 2**
  `{title, oneLineSummary}` objects, best-first.
- `title` — required per proposal; ≤256 chars; begins with `defect:` or `deepening:`. Keep it on one line.
- `oneLineSummary` — required per proposal; one line.
- `candidatesConsidered` — required when proposed; non-empty array of short strings.
- `reason` — required when skipped.
- The `<body-N>` blocks — one per proposal when proposed (1-indexed, array
  order), omitted when skipped; raw markdown, no JSON escaping.

## Rules

- **Read-only on the repo. You file nothing.** No commits, no edits, no
  `gh issue create`. The workflow publishes the issues (and applies the
  `source:architecture-review` label) from your `<output>` + `<body-N>` blocks.
  Your only job is to read, decide, and emit them.
- Two proposals per run, maximum — and the workflow enforces the cap
  regardless. Two is a ceiling, not a target: every proposal must
  independently clear the bar that would have made it the run's single best.
- No questions. There is no user.
