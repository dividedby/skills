"""EOL-pastness: the date-vs-today decision, in code rather than model judgment.

The validate station fetches a toolchain major's end-of-life *date* from upstream.
Whether that date is *past* is then a deterministic comparison against today — and
it must stay in code: a model asked "is this past EOL?" anchors on the vintage of
the data it read and gets it wrong (the #129 fixture caught exactly this — Node 18's
2025-04-30 EOL read as "not yet" though it is past). So the decision lives here as a
pure, table-driven-tested helper (ADR 0004), alongside `version_gap` and `rank`.

Pure: a date in, a bool out. The skill prose owns fetching the EOL date from
upstream; this module owns only the comparison.
"""

import datetime


def is_past_eol(eol_date, today=None):
    """Return ``True`` when ``eol_date`` is strictly before ``today``.

    ``eol_date`` is an ISO ``YYYY-MM-DD`` string or a ``datetime.date``. The EOL
    date is the last supported day, so a pin is "past EOL" only the day *after* it
    (strict ``<``). ``today`` defaults to the real current date.

    An unknown or unparseable EOL — ``None``, ``""``, ``"unverified"`` — returns
    ``False``: absent web data must never manufacture urgency (mirrors how `rank`
    treats a missing ``eol_passed``).
    """
    if today is None:
        today = datetime.date.today()
    if isinstance(eol_date, datetime.date):
        return eol_date < today
    if not isinstance(eol_date, str):
        return False
    try:
        return datetime.date.fromisoformat(eol_date.strip()) < today
    except ValueError:
        return False
