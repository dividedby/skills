"""Version-gap classifier: the pure decision at the spine of the staleness audit.

Given a pinned `current` version and an upstream `latest`, classify the gap as
``major | minor | patch | none | unknown``. The classification must not depend on
model judgment — the audit ranks and (later slices) gates auto-apply on it — so it
lives here as executable code, not prose the agent re-derives each run (ADR 0004:
pure, Python stdlib, table-driven tests, never registered in plugin.json).

Pure: inputs in, decision out. No I/O, no web, no file access. The skill prose
owns scanning files and rendering the report; this module owns only the gap math.
"""

import re

# A leading version core: major[.minor[.patch]], tolerating a `v` prefix, a
# range operator (>=, ^, ~, etc.), and an `x`/`*` wildcard segment (read as 0).
_VERSION_RE = re.compile(r"^[^\d]*?(\d+)(?:\.(\d+|[xX*]))?(?:\.(\d+|[xX*]))?")


def parse_version(raw):
    """Parse a pin string into a ``(major, minor, patch)`` int tuple.

    Tolerates the shapes toolchain pins actually take — bare majors (``18``),
    partials (``18.17``), a ``v`` prefix, range operators (``>=18``, ``^18.17.0``),
    and ``x``/``*`` wildcards (read as 0). Returns ``None`` when no numeric version
    can be found (codenames like ``lts/iron``, empty, junk).
    """
    if not isinstance(raw, str):
        return None
    m = _VERSION_RE.match(raw.strip())
    if not m:
        return None

    def seg(value):
        if value is None or value in ("x", "X", "*"):
            return 0
        return int(value)

    return (int(m.group(1)), seg(m.group(2)), seg(m.group(3)))


def classify(current, latest):
    """Classify the gap between a pinned ``current`` and upstream ``latest``.

    Returns ``"unknown"`` when either side is unparseable, ``"none"`` when current
    is at or ahead of latest, else the highest-order segment that differs:
    ``"major"`` > ``"minor"`` > ``"patch"``.
    """
    cur = parse_version(current)
    lat = parse_version(latest)
    if cur is None or lat is None:
        return "unknown"
    if cur >= lat:
        return "none"
    if cur[0] != lat[0]:
        return "major"
    if cur[1] != lat[1]:
        return "minor"
    return "patch"
