"""Auto-apply gating: may a finding be auto-applied, and if not, what downgrade?

The apply station bumps safe pins automatically, but *which* bumps qualify must
not depend on model judgment — a cross-major jump or an EOL-driven leap must never
slip into an unattended apply. So the gating decision lives here as executable code
(ADR 0004: pure, Python stdlib, table-driven tests, never registered in
plugin.json), alongside `version_gap`, `rank`, and `eol`.

Pure: a finding's plain flags in, a decision out. No subprocess, no git, no file
I/O. The skill prose owns the apply -> verify -> revert *mechanics* (the agent runs
those with its tools); this module owns only the gate that says whether a given
finding is eligible, and the exact downgrade reason when it is not.
"""

# Gaps that an auto-apply may touch: an in-major bump (patch or minor) keeps the
# pinned major fixed, so it carries no breaking-change migration. A `major` gap is
# a cross-major jump; `none`/`unknown` have nothing safe to apply.
_IN_MAJOR = ("patch", "minor")


def decide(finding):
    """Decide the apply disposition for one finding.

    ``finding`` is a dict carrying:

    - ``gap`` — ``major | minor | patch | none | unknown`` (from `version_gap`).
    - ``eol_passed`` — ``True`` when the pin is past upstream EOL (from `eol`).
    - ``file_owned`` — ``True`` when the pinned file is owned/writable by the repo
      (a vendored or generated pin is not ours to bump).
    - ``verify_available`` — ``True`` when a verify command was discoverable.
    - ``verify_passed`` — after the agent ran the bump+verify: ``True`` kept,
      ``False`` reverted, ``None`` not yet attempted.
    - ``low_confidence`` — ``True`` when the finding came from a best-effort,
      lower-confidence source (a grep over `scripts/`, `README*`, `Makefile` —
      an installer hint, not a declared pin file). The *location* of such a pin
      is a guess, so it is never safe to mutate mechanically.
    - ``is_floor`` — ``True`` when the pin is a constraint the repo *imposes on
      its consumers* (a published floor: `engines`, `devEngines`, the lower bound
      of `requires-python`, peer deps) rather than a version the repo *satisfies*
      for itself (`.nvmrc`, `.tool-versions`, the `go` directive, CI matrix, image
      tags). Raising a floor narrows who may consume the package — a breaking
      change the *consumers* feel and the local verify gate cannot see — so a
      floor is never a mechanical bump in either direction; its remediation is a
      human support-policy call, not an apply.

    Returns one of:

    - ``"apply"`` — eligible: an in-major bump on an owned file with verify
      available, and (if a verify result is in) verify passed.
    - ``"recommended: low confidence (installer)"`` — the finding came from a
      best-effort grep, not a declared pin file; recommend-only, never applied.
    - ``"recommended: floor (consumer-imposed)"`` — the pin is a published floor
      the repo imposes on its consumers; raising it drops support and lowering it
      is a support-policy call, so it is recommend-only in either direction.
    - ``"unverified: no verify command"`` — no verify command at all; the whole
      audit drops to recommendations.
    - ``"recommended: cross-major"`` — a major gap; never auto-applied.
    - ``"recommended: eol jump"`` — a past-EOL pin; the upgrade carries migration
      risk, so it stays a recommendation even when the gap reads in-major.
    - ``"recommended: not owned"`` — the pinned file is not ours to mutate.
    - ``"recommended: none"`` — nothing to bump (gap ``none``/``unknown``).
    - ``"recommended (verify failed)"`` — was eligible, but the per-bump verify
      failed, so the bump was reverted and downgraded.

    Precedence is deliberate. ``low_confidence`` is decided *first* — before even
    the missing-verify global disable — because it distrusts the finding at its
    source: a best-effort grep match has no reliable owned file to mutate, so it is
    never auto-applied no matter how clean its gap, EOL, ownership, or verify state
    look. Surfacing the installer reason ahead of everything else makes that
    source-distrust explicit in the report. ``is_floor`` is decided next, for the
    same shape of reason: it distrusts the *direction* of the bump, not its target.
    A floor's "behind latest" gap is not staleness — raising it sheds consumers —
    so no gap, EOL, ownership, or green verify may ever promote a floor into an
    unattended mutation. Next, absence of a verify command disables apply globally.
    Then the never-apply ceilings (cross-major, EOL) — an EOL pin is a
    recommendation even if its gap happens to be in-major, because the safe path
    runs *through* the EOL'd major's migration. Ownership and an applicable gap
    come next; the verify result is read last.
    """
    if finding.get("low_confidence") is True:
        return "recommended: low confidence (installer)"
    if finding.get("is_floor") is True:
        return "recommended: floor (consumer-imposed)"
    if not finding.get("verify_available"):
        return "unverified: no verify command"
    if finding.get("eol_passed") is True:
        return "recommended: eol jump"
    if finding.get("gap") == "major":
        return "recommended: cross-major"
    if finding.get("gap") not in _IN_MAJOR:
        return "recommended: none"
    if not finding.get("file_owned"):
        return "recommended: not owned"
    if finding.get("verify_passed") is False:
        return "recommended (verify failed)"
    return "apply"
