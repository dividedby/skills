"""Sanitizer guard: the pure decision that blocks private-repo content from
reaching this repo's PUBLIC issue tracker.

Used by the gap-scanner run-book, which reads private repos but files
generalized proposals here. The no-private-code rule is enforced mechanically
here, not by prompt discipline. This module never touches the tracker; the
run-book gates on the returned decision.

Known limitations (the guard is necessary, not sufficient):
- It catches *structural* leak signals (markers, fenced code, file paths, import
  lines). It cannot judge whether free prose names something private — a bare
  private identifier like ``calculateChargebackFee`` passes. So the run-book must
  always supply the configured ``private_markers``, and prose discipline still
  matters for identifiers the markers don't cover.
- The file-path signal also matches public URLs with an extension
  (``…/patterns.html``), so a body that cites sources can be over-blocked. The
  caller (#20) decides how to cite sources without tripping it.
"""

import re

_CODE_FENCE = re.compile(r"```")
# A path-like token: at least one directory separator and a file extension.
_FILE_PATH = re.compile(r"\b[\w.-]+/[\w./-]*\.[A-Za-z0-9]{1,6}\b")
# A pasted import/require statement (start of any line).
_IMPORT_LINE = re.compile(
    r"^\s*(import\s|from\s+[\w.]+\s+import\s|.*\brequire\s*\()",
    re.MULTILINE,
)


def _allow():
    return {"allowed": True, "reason": None}


def _block(reason):
    return {"allowed": False, "reason": reason}


def check(body, private_markers=()):
    """Return ``{"allowed": True, "reason": None}`` to permit filing ``body``,
    or ``{"allowed": False, "reason": <str>}`` to block it.

    ``private_markers`` is an iterable of strings (e.g. private repo or owner
    names) the run-book knows are sensitive; any occurrence blocks. Beyond that,
    generic leak signals (pasted code, file paths, import lines) block, while a
    body that only describes a need in the abstract is allowed.
    """
    lowered = body.lower()
    for marker in private_markers:
        if marker.lower() in lowered:
            return _block(f"names a private marker: {marker}")
    if _CODE_FENCE.search(body):
        return _block("contains a fenced code block (possible pasted code)")
    if _FILE_PATH.search(body):
        return _block("quotes a file path (possible private source reference)")
    if _IMPORT_LINE.search(body):
        return _block("contains an import/require line (possible pasted code)")
    return _allow()
