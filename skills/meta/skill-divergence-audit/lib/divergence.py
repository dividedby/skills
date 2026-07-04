"""Divergence classifier: pure functions that diff our published skills against
Matt Pocock's repo and the agent-research KB, and classify each gap.

Called by the ``skill-divergence-audit`` skill (via ``cli.py``). All inputs are
plain data structures (dicts/lists); nothing here touches the network, the
filesystem, or any tracker. This is the deterministic core unit-tested by
``divergence.test.py``.

## Classify categories

``MISSING_HERE``
    Matt or the KB describes a practice/skill we have no equivalent for.
    The highest-value finding: we may want to adopt, adapt, or intentionally
    decide not to.

``OUTDATED_HERE``
    We have a skill that covers the same surface, but our version appears
    behind Matt's or the KB's — a named concept or pillar is absent.

``DIVERGED``
    We have a skill covering the same surface but our guidance directly
    contradicts Matt's or the KB's on a named point.  Rare; needs human
    judgment to resolve.

``NO_UPSTREAM_EQUIVALENT``
    We have a skill that has no analogue in Matt's repo or the KB.  Not a
    problem by itself, but worth knowing — surface so the maintainer can
    confirm it is intentional.

``ALIGNED``
    Same surface, no meaningful gap.  Reported only in a verbose dump; not
    proposed to the tracker.
"""

CATEGORIES = frozenset(
    ["MISSING_HERE", "OUTDATED_HERE", "DIVERGED", "NO_UPSTREAM_EQUIVALENT", "ALIGNED"]
)

# Only these categories are worth proposing as issues.
PROPOSAL_CATEGORIES = frozenset(["MISSING_HERE", "OUTDATED_HERE", "DIVERGED"])

# Mirrors CONTEXT.md's "Upstream soft-dependencies" list (the mattpocock/skills
# side only — ADR 0024): skills we deliberately deleted here and lean on
# upstream for instead. Pass 2 must not flag these MISSING_HERE on every run —
# that's not a gap, it's the intended posture. Keep this in sync with
# CONTEXT.md by hand; this module stays filesystem-free (pure, unit-tested)
# so it cannot read CONTEXT.md itself.
SOFT_DEPENDENCY_SKILLS = frozenset(
    [
        "codebase-design",
        "domain-modeling",
        "writing-great-skills",
        "diagnosing-bugs",
        "prototype",
        "to-prd",
        "to-issues",
        "tdd",
        "implement",
        "grilling",
        "grill-with-docs",
    ]
)


def classify_skill(our_skill, upstream_skills):
    """Classify a single *our* skill against the upstream skill set.

    ``our_skill`` is a dict with at minimum:
        ``name``        — the skill slug (str)
        ``pillars``     — a frozenset/set/list of named concept-pillars the
                          skill covers (e.g. {"scan", "classify", "render"})
        ``contradicts`` — optional set/list of upstream pillar names our skill
                          explicitly opposes.  When the intersection of
                          ``contradicts`` and the matched upstream's pillars is
                          non-empty, the skill is classified as ``DIVERGED``
                          (highest-priority signal, takes precedence over
                          OUTDATED_HERE / ALIGNED).

    ``upstream_skills`` is a list of dicts with the same shape, drawn from
    Matt's repo and/or the agent-research KB (source field identifies which).

    Returns one of the CATEGORIES strings.
    """
    our_name = our_skill["name"].lower()
    our_pillars = set(p.lower() for p in our_skill.get("pillars", []))
    our_contradicts = set(p.lower() for p in our_skill.get("contradicts", []))

    matches = [
        s for s in upstream_skills
        if s["name"].lower() == our_name
    ]

    if not matches:
        return "NO_UPSTREAM_EQUIVALENT"

    # At least one upstream match exists.
    upstream_pillars = set()
    for m in matches:
        upstream_pillars.update(p.lower() for p in m.get("pillars", []))

    # DIVERGED takes highest precedence: our skill explicitly contradicts a
    # named upstream pillar.
    if our_contradicts & upstream_pillars:
        return "DIVERGED"

    if not upstream_pillars:
        # Upstream exists but declares no pillars — treat as aligned.
        return "ALIGNED"

    missing_pillars = upstream_pillars - our_pillars
    if not missing_pillars:
        return "ALIGNED"

    # We're missing at least one pillar the upstream covers.
    return "OUTDATED_HERE"


def classify_upstream(upstream_skill, our_skills):
    """Classify a single *upstream* skill against our published skill set.

    Returns ``"MISSING_HERE"`` when we have no skill with a matching name, or
    ``"ALIGNED"`` / ``"OUTDATED_HERE"`` when a local match exists (delegates
    to ``classify_skill``).
    """
    up_name = upstream_skill["name"].lower()
    our_match = next(
        (s for s in our_skills if s["name"].lower() == up_name), None
    )
    if our_match is None:
        return "MISSING_HERE"
    return classify_skill(our_match, [upstream_skill])


def diff(our_skills, upstream_skills):
    """Compute all divergences between our skill set and the upstream set.

    Each input is a list of skill dicts with at minimum ``name`` and
    optionally ``pillars``.  ``upstream_skills`` may contain entries from
    Matt's repo and from the agent-research KB (distinguished by a ``source``
    field on each dict, e.g. ``"matt"`` or ``"kb"``).

    Returns a list of divergence dicts, each containing:
        ``name``      — the skill name
        ``category``  — one of CATEGORIES
        ``detail``    — a human-readable string explaining the finding
        ``source``    — ``"ours"``, ``"matt"``, ``"kb"``, or ``"both"``
                        (where the finding originates)
        ``pillars``   — list of pillar names relevant to the finding (may be empty)
    """
    results = []
    our_names = {s["name"].lower() for s in our_skills}
    upstream_names = {s["name"].lower() for s in upstream_skills}

    # Pass 1: classify each of our skills.
    for skill in our_skills:
        name = skill["name"]
        category = classify_skill(skill, upstream_skills)
        if category == "NO_UPSTREAM_EQUIVALENT":
            detail = f"{name!r} exists in our catalog but has no equivalent upstream"
            source = "ours"
            pillars = []
        elif category == "ALIGNED":
            detail = f"{name!r} is aligned with upstream"
            source = "both"
            pillars = []
        elif category == "DIVERGED":
            our_contradicts = set(p.lower() for p in skill.get("contradicts", []))
            upstream_pillars = set()
            for m in upstream_skills:
                if m["name"].lower() == name.lower():
                    upstream_pillars.update(p.lower() for p in m.get("pillars", []))
            conflicting = sorted(our_contradicts & upstream_pillars)
            detail = (
                f"{name!r} directly contradicts upstream pillar(s): "
                + ", ".join(repr(p) for p in conflicting)
            )
            source = "both"
            pillars = conflicting
        else:
            # OUTDATED_HERE
            our_pillars = set(p.lower() for p in skill.get("pillars", []))
            upstream_pillars = set()
            for m in upstream_skills:
                if m["name"].lower() == name.lower():
                    upstream_pillars.update(p.lower() for p in m.get("pillars", []))
            missing = sorted(upstream_pillars - our_pillars)
            detail = (
                f"{name!r} is missing pillar(s) that upstream covers: "
                + ", ".join(repr(p) for p in missing)
            )
            source = "both"
            pillars = missing
        results.append(
            {
                "name": name,
                "category": category,
                "detail": detail,
                "source": source,
                "pillars": pillars,
            }
        )

    # Pass 2: upstream skills we lack entirely.
    for skill in upstream_skills:
        name = skill["name"]
        if name.lower() in SOFT_DEPENDENCY_SKILLS:
            continue  # deliberately deleted; soft-depended on, not a gap (CONTEXT.md)
        if name.lower() not in our_names:
            src = skill.get("source", "upstream")
            results.append(
                {
                    "name": name,
                    "category": "MISSING_HERE",
                    "detail": (
                        f"{name!r} exists upstream ({src}) but we have no equivalent"
                    ),
                    "source": src,
                    "pillars": list(skill.get("pillars", [])),
                }
            )

    return results


def render_report(divergences, *, include_aligned=False):
    """Render a markdown findings report from a list of divergence dicts.

    ``include_aligned=False`` (the default) omits ALIGNED rows — they add no
    actionable signal to a normal run.

    Returns a string of markdown.
    """
    if not divergences:
        return "## Skill Divergence Report\n\nNo divergences found.\n"

    rows = [d for d in divergences if include_aligned or d["category"] != "ALIGNED"]
    if not rows:
        return "## Skill Divergence Report\n\nAll skills are aligned. No gaps found.\n"

    lines = ["## Skill Divergence Report", ""]
    lines.append("| skill | category | detail | source |")
    lines.append("|---|---|---|---|")
    for d in sorted(rows, key=lambda r: (r["category"], r["name"])):
        name = d["name"]
        cat = d["category"]
        detail = d["detail"].replace("|", "\\|")
        src = d["source"]
        lines.append(f"| {name} | {cat} | {detail} | {src} |")
    lines.append("")
    return "\n".join(lines)


def to_candidates(divergences):
    """Convert divergence dicts to proposal-gate candidates.

    Only PROPOSAL_CATEGORIES are eligible.  Each candidate carries:
        ``dedup_key``  — stable kebab slug: ``divergence-<category-slug>-<name>``
        ``priority``   — int (MISSING_HERE=3, OUTDATED_HERE=2, DIVERGED=4)
        ``name``       — skill name (pass-through for the caller's filing step)
        ``category``   — the classify category
        ``detail``     — the human detail string

    Returns a list sorted by priority descending (ties by dedup_key).
    """
    PRIORITY = {"MISSING_HERE": 3, "OUTDATED_HERE": 2, "DIVERGED": 4}
    CAT_SLUG = {
        "MISSING_HERE": "missing",
        "OUTDATED_HERE": "outdated",
        "DIVERGED": "diverged",
    }
    candidates = []
    for d in divergences:
        cat = d["category"]
        if cat not in PROPOSAL_CATEGORIES:
            continue
        slug = d["name"].lower().replace(" ", "-").replace("_", "-")
        dedup_key = f"divergence-{CAT_SLUG[cat]}-{slug}"
        candidates.append(
            {
                "dedup_key": dedup_key,
                "priority": PRIORITY[cat],
                "name": d["name"],
                "category": cat,
                "detail": d["detail"],
                "pillars": d.get("pillars", []),
            }
        )
    candidates.sort(key=lambda c: (-c["priority"], c["dedup_key"]))
    return candidates
