"""Conservative, deterministic JSON repair for the ``gate`` parse seam.

The body is a **verbatim copy** of ``_repair_json`` in ``harness/cli.py`` (the
publish-seam primitive added by dividedby/skills#367 / ADR 0025). The skill ships
independently of the harness (plugin skill vs. fetched-fresh harness — ADR 0014)
and ``lib/cli.py`` is sibling-import-only, so it cannot import harness code at a
Consumer's runtime. The copy is the deliberate cross-boundary choice (issue #369 /
ADR 0026). A drift guard (``harness/tests/test_repair_json_drift.py``) asserts
this body is byte-identical to the canonical ``_repair_json``; a one-sided edit
fails CI.
"""

import re


def repair_json(block: str) -> str:
    """Conservative, idempotent JSON repair for the common corruption patterns.

    Uses a single quote-state-aware character walk — NOT regex — to avoid
    corrupting valid strings that contain sequences like ``, }``.

    Repairs performed:
    - Outside strings: drops structural trailing commas (a ``,`` whose next
      non-whitespace character is ``}`` or ``]``).
    - Inside strings: escapes lone control characters (raw newline, tab, CR)
      that are not already escaped.
    - Re-strips a residual ````json`` / ````` `` fence if present.
    """
    # Strip any residual fence variants the main strip may have missed.
    stripped = re.sub(r"^\s*```json\s*", "", block, flags=re.MULTILINE)
    stripped = re.sub(r"\s*```\s*$", "", stripped, flags=re.MULTILINE).strip()

    out = []
    in_string = False
    i = 0
    while i < len(stripped):
        ch = stripped[i]
        if in_string:
            if ch == "\\":
                # Consume the escape sequence verbatim (skip the escaped char).
                out.append(ch)
                i += 1
                if i < len(stripped):
                    out.append(stripped[i])
                    i += 1
                continue
            elif ch == '"':
                in_string = False
                out.append(ch)
            elif ch == "\n":
                out.append("\\n")
            elif ch == "\t":
                out.append("\\t")
            elif ch == "\r":
                out.append("\\r")
            else:
                out.append(ch)
        else:
            if ch == '"':
                in_string = True
                out.append(ch)
            elif ch == ",":
                # Look ahead for the next non-whitespace char.
                j = i + 1
                while j < len(stripped) and stripped[j] in " \t\n\r":
                    j += 1
                if j < len(stripped) and stripped[j] in "}]":
                    # Structural trailing comma — drop it.
                    i += 1
                    continue
                else:
                    out.append(ch)
            else:
                out.append(ch)
        i += 1
    return "".join(out)
