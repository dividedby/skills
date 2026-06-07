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

    Returns one of:

    - ``"apply"`` — eligible: an in-major bump on an owned file with verify
      available, and (if a verify result is in) verify passed.
    - ``"unverified: no verify command"`` — no verify command at all; the whole
      audit drops to recommendations.
    - ``"recommended: cross-major"`` — a major gap; never auto-applied.
    - ``"recommended: eol jump"`` — a past-EOL pin; the upgrade carries migration
      risk, so it stays a recommendation even when the gap reads in-major.
    - ``"recommended: not owned"`` — the pinned file is not ours to mutate.
    - ``"recommended: none"`` — nothing to bump (gap ``none``/``unknown``).
    - ``"recommended (verify failed)"`` — was eligible, but the per-bump verify
      failed, so the bump was reverted and downgraded.

    Precedence is deliberate. Absence of a verify command disables apply globally,
    so it is decided first. Then the never-apply ceilings (cross-major, EOL) — an
    EOL pin is a recommendation even if its gap happens to be in-major, because the
    safe path runs *through* the EOL'd major's migration. Ownership and an
    applicable gap come next; the verify result is read last.
    """
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
