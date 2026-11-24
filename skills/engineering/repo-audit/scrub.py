"""Scrub the files a repo-audit run publishes of local and personal details.

    scrub.py [--check] [--json] [--literal NAME] [--hostname NAME] [--no-auto] FILE...

Every file is read as UTF-8 text and rewritten in place: each match becomes a
category placeholder such as `[redacted:home-path]`, then the file is scanned
again and the exit code is 1 when anything is left. `--check` only reports (no
writes, exit 1 on any match). Exit 2, with a message on stderr and
nothing written: a file is missing or is not UTF-8 text.
The summary carries counts and category names, never a matched value, so it can
go straight into the run log. Standard library only.

Categories, each deliberately narrow so the floor has few false positives:

  home-path     /Users/<name>/..., /home/<name>/... (a bare /home/<name>
                only when <name> is the current user), C:\\Users\\<name>\\...,
                and the $HOME value.
  scratch-path  /private/tmp/..., /tmp/claude-..., /var/folders/..., the
                $TMPDIR value. A bare /tmp/x is left alone: it is too common
                in docs to be a signal.
  username      the current user and any --literal name, whole word, any case.
  hostname      this machine's name and any --hostname name, plus private
                suffixes (.local, .lan, .internal, .home.arpa, .corp).
  ip            IPv4 and IPv6 except loopback, unspecified, multicast,
                reserved and the documentation ranges (192.0.2.0/24,
                198.51.100.0/24, 203.0.113.0/24, 2001:db8::/32). A private
                IPv4 is always flagged; any other dotted quad is skipped when
                a version marker (v, version, ==, >=, <=, ~=, ^, or python,
                oid, openssl, java, ruby, php, chrome, firefox, safari
                and a space) comes right before it, so `v1.2.3.4` survives
                and `1.2.3.4` alone does not. A dotted quad right after a
                browser user-agent product and a slash (Chrome, Chromium,
                CriOS, Firefox, FxiOS, Safari, AppleWebKit, Version, Edg,
                Edge, OPR, Mozilla, HeadlessChrome) is a version and stays,
                private range included; `https://host/1.2.3.4` does not.
  account-id    the 12 digits of an AWS ARN; the value of an account_id-style
                key (12 to 14 digits or 32 hex).
  token         GitHub, GitLab, Anthropic, OpenAI-style, Stripe live, npm,
                Slack, AWS and Google key prefixes, JWTs, `Bearer <token>`, PEM private key blocks.
  email         any address except noreply, `git@`, example.com/org/net,
                .invalid, .test, .example and `@2x.png` style file names.
  geo           a number with 4 or more decimals under a lat/lng/latitude/
                longitude key, a latitude, longitude pair (in range) under a
                coords/location/geo-style key, or such a pair standing alone
                (the whole line or cell, backticked, quoted or in brackets
                of its own), or a pair in running text with a location word
                (at, near, nearby, around, located, location, pin, map, gps,
                address, coordinates, lat/lng, place, home, office, site,
                city, ...) no more than two words before it:
                `pin at 41.8781, -87.6298`. Pairs chained to a cued pair with
                `,`, `;`, and, to or or are cued too, and a chain is judged
                whole. Degree notation with hemisphere letters
                (`41.8781° N, 87.6298° W`) is caught anywhere. Stays:
                - a cued pair or chain followed by a unit (ms, s, px, %, kb,
                  mb, ...), which makes it a measurement; a short unit counts
                  only when no word follows (`min walk` does not). A bare x
                  is no unit: a multiplier is written attached, `1.5x`;
                - a cued pair followed by a third number
                  (`0.95, 0.87, 0.77`);
                - a pair, or a whole chain, whose values are all below 1 in
                  absolute value (`CLS at 0.0012, 0.0034`): that square is
                  open ocean around 0, 0 with no land or address. Applies to
                  every pair rule, not to a single `lat: 0.5` value. A pair
                  with one value of 1 or more is still caught
                  (`at 0.3365, 6.7273`);
                - pairs inside SVG paths and points, CSS functions, JSON
                  arrays, and sentences with no cue
                  (`time 12.3456, 78.9012 seconds`).
                Phone numbers are not scanned: no rule was precise enough.

This is a floor. It matches shapes, so prose with no cue (a place named in a
sentence, a coordinate with no location word) passes it; the Stage 6 demo-data
read in SKILL.md is what covers those.

`data:` URIs (the page's embedded screenshots) are skipped whole.
"""

from __future__ import annotations

import argparse
import contextlib
import getpass
import ipaddress
import json
import os
import re
import socket
import sys
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

CATEGORIES = [
    "token",
    "email",
    "account-id",
    "home-path",
    "scratch-path",
    "ip",
    "geo",
    "hostname",
    "username",
]

# Auto-detected names this generic would redact ordinary prose.
_GENERIC_NAMES = {
    "root",
    "user",
    "admin",
    "runner",
    "ubuntu",
    "node",
    "docker",
    "localhost",
    "localhost.localdomain",
    "builder",
    "build",
    "ec2-user",
}
_GENERIC_HOME_NAMES = {
    "user",
    "username",
    "you",
    "me",
    "name",
    "example",
    "shared",
    "runner",
}

# Characters that end a path: whitespace, quotes, brackets, separators, globs.
_PATH_STOP = r"""\s"'<>`)\]},;|*?\\"""
_PATH_REST = rf"[^{_PATH_STOP}]*"  # the rest of a path after its root
_PATH_TAIL = rf"(?:/{_PATH_REST})?"  # an optional /... after a known root
_WIN_FIRST = rf"[^{_PATH_STOP}/:]+"  # first Windows segment: also stops at / and :
_WIN_NEXT = rf"[^{_PATH_STOP}]+"
_SEP = r"""[\s"'<>`()\[\]{},;|]"""

_DATA_URI = re.compile(r"""(?<![A-Za-z0-9])(data:[A-Za-z0-9/+.;=_-]*,[^\s"'()<>]*)""")

_PRIVATE_V4 = [
    ipaddress.ip_network(n)
    for n in (
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "169.254.0.0/16",
        "100.64.0.0/10",
    )
]
_DOC_V4 = [
    ipaddress.ip_network(n)
    for n in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24")
]
_DOC_V6 = ipaddress.ip_network("2001:db8::/32")

_VERSION_MARK = re.compile(
    r"(?i)(?:\bv|\bversions?|\bver"
    r"|\b(?:python|oid|openssl|java|ruby|php|chrome|firefox|safari)\s"
    r"|==|>=|<=|~=|\^)"
    r"\s*:?\s*$"
)

# A browser user-agent product token right before the number: `Chrome/131.0.0.0`.
# Named products only; a generic `word/` would also spare `https://host/1.2.3.4`.
_UA_PRODUCT = re.compile(
    # The token starts the text or follows whitespace, `(` or `;`, so a
    # `/chrome/` path segment does not count.
    r"(?i)(?<![^\s(;])(?:Chrome|Chromium|CriOS|Firefox|FxiOS|Safari|AppleWebKit"
    r"|Version|Edg|Edge|OPR|Mozilla|HeadlessChrome)/$"
)

# Geo in running text: a location word, up to two words, then the pair. A unit
# after the pair means it is a measurement (`12.3456, 78.9012 ms`), not a place.
_GEO_CUES = (
    "at|near|nearby|around|located|location|pin|pinned|map|gps|address"
    "|coordinates|coordinate|coords|place|home|office|hq|headquarters|site|city"
    "|(?:lat|latitude)/(?:lng|lon|long|longitude)|lat|lng|lon|latitude|longitude"
    "|latlng|latlon"
)
# Matched case-insensitively; `µ` is the micro sign, `μ` the Greek mu. A unit
# counts only when whitespace, the end of the text or `.,;:!?)` follows it.
_GEO_UNITS = (
    "ms|msec|msecs|millisecond|milliseconds|usec|usecs|µs|μs|microsecond"
    "|microseconds|nsec|nsecs|nanosecond|nanoseconds|second|seconds|minute"
    "|minutes|hour|hours|day|days|px|dpi|fps|hz|khz|mhz|ghz|byte|bytes|kb|mb|gb"
    "|tb|pb|kib|mib|gib|tib|bps|kbps|mbps|gbps"
)
# Short or word-like units: also must not be followed by a word (`x marks`,
# `min walk`, `pt Reyes`, `em dash`), which would make them part of a sentence.
_GEO_UNITS_SHORT = "s|sec|secs|us|ns|min|mins|h|hr|hrs|b|pt|em|rem|dp|deg"
_UNIT_END = r"(?=\s|$|[.,;:!?)])"
# After the pair: `%`, or a unit as above.
_GEO_UNIT_AFTER = (
    rf"(?![ \t]*(?:%|(?:{_GEO_UNITS}){_UNIT_END}"
    rf"|(?:{_GEO_UNITS_SHORT}){_UNIT_END}(?![.,;:!?)]*[ \t]*[A-Za-z])))"
)


@dataclass
class Context:
    """Run-specific literals. Built from the environment unless disabled."""

    home: list[str] = field(default_factory=list)
    tmp: list[str] = field(default_factory=list)
    usernames: list[str] = field(default_factory=list)
    hostnames: list[str] = field(default_factory=list)


def auto_context(env: dict[str, str] | None = None) -> Context:
    """The current user, host, $HOME and $TMPDIR, read from the environment."""
    e = os.environ if env is None else env
    ctx = Context()
    home = (e.get("HOME") or e.get("USERPROFILE") or "").rstrip("/\\")
    if len(home) >= 5:
        ctx.home.append(home)
    tmp = (e.get("TMPDIR") or "").rstrip("/\\")
    if len(tmp) >= 5 and tmp not in ("/tmp", "/var/tmp"):
        ctx.tmp.append(tmp)
    names = [e.get("USER"), e.get("LOGNAME"), e.get("USERNAME")]
    with contextlib.suppress(KeyError, OSError, ImportError):  # no passwd entry
        names.append(getpass.getuser())
    for n in names:
        if n and len(n) >= 3 and n.lower() not in _GENERIC_NAMES:
            ctx.usernames.append(n)
    try:
        host = socket.gethostname()
    except OSError:
        host = ""
    for h in (host, host.split(".")[0]):
        if len(h) >= 3 and h.lower() not in _GENERIC_NAMES:
            ctx.hostnames.append(h)
    return ctx


Accept = Callable[["re.Match[str]"], bool]


@dataclass
class Rule:
    category: str
    regex: re.Pattern[str]
    group: int = 0  # the group replaced; 0 is the whole match
    accept: Accept | None = None


def _alt(values: Iterable[str]) -> str | None:
    vals = sorted({v for v in values if v}, key=len, reverse=True)
    return "|".join(re.escape(v) for v in vals) if vals else None


# --- validators ------------------------------------------------------------


def _home_ok(ctx: Context) -> Accept:
    users = {u.lower() for u in ctx.usernames}

    def accept(m: re.Match[str]) -> bool:
        name = m.group("name").lower()
        if name in _GENERIC_HOME_NAMES:
            return False
        # /home/<x> alone is a common web route; deeper paths and the
        # current user's own folder are not.
        if m.group("root") == "/home" and not m.group("tail"):
            return name in users
        return True

    return accept


def _ipv4_ok(m: re.Match[str]) -> bool:
    try:
        ip = ipaddress.IPv4Address(m.group(1))
    except ValueError:
        return False
    if ip.is_loopback or ip.is_unspecified or ip.is_multicast or ip.is_reserved:
        return False
    if any(ip in n for n in _DOC_V4):
        return False
    if _UA_PRODUCT.search(m.string[max(0, m.start(1) - 20) : m.start(1)]):
        return False
    if any(ip in n for n in _PRIVATE_V4):
        return True
    before = m.string[max(0, m.start(1) - 16) : m.start(1)]
    before = before.rsplit("\n", 1)[-1]
    return not _VERSION_MARK.search(before)


def _ipv6_ok(m: re.Match[str]) -> bool:
    text = m.group(0)
    if text.count(":") < 2 or not any(len(g) >= 3 for g in text.split(":")):
        return False
    try:
        ip = ipaddress.IPv6Address(text)
    except ValueError:
        return False
    return not (ip.is_loopback or ip.is_unspecified or ip.is_multicast or ip in _DOC_V6)


_NOREPLY_LOCAL = {"noreply", "no-reply", "donotreply", "do-not-reply", "git"}
_SAFE_DOMAINS = {"example.com", "example.org", "example.net"}


def _email_ok(m: re.Match[str]) -> bool:
    local, _, domain = m.group(0).rpartition("@")
    domain = domain.lower()
    if local.lower() in _NOREPLY_LOCAL:
        return False
    if domain.endswith("users.noreply.github.com"):
        return False
    if domain in _SAFE_DOMAINS or any(domain.endswith("." + d) for d in _SAFE_DOMAINS):
        return False
    if domain.rsplit(".", 1)[-1] in ("invalid", "test", "example", "localhost"):
        return False
    return not re.match(r"\d+x\.", domain)  # icon@2x.png


def _not_null_island(group: int) -> Accept:
    """Accept a run of lat, lng pairs only if one pair has a value of 1 or more.

    A pair with both values below 1 in absolute value is open ocean around
    0, 0 (no land, no address), and in practice a pair of metrics or scores."""

    def accept(m: re.Match[str]) -> bool:
        nums = [abs(float(n)) for n in re.findall(r"\d+(?:\.\d+)?", m.group(group))]
        return any(a >= 1 or b >= 1 for a, b in zip(nums[::2], nums[1::2]))

    return accept


def _has_digit(m: re.Match[str]) -> bool:
    return any(c.isdigit() for c in m.group("body"))


# --- rules -----------------------------------------------------------------


def build_rules(ctx: Context) -> list[Rule]:
    rules: list[Rule] = []

    def add(
        cat: str,
        pattern: str,
        group: int = 0,
        accept: Accept | None = None,
    ):
        rules.append(Rule(cat, re.compile(pattern), group, accept))

    # token. PEM first so its body is not read as anything else.
    pem = "-----BEGIN [A-Z ]*PRIVATE KEY-----"
    add("token", pem + r"[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----")
    add("token", pem)
    add("token", r"(?<![A-Za-z0-9])gh[pousr]_[A-Za-z0-9]{30,}")
    add("token", r"(?<![A-Za-z0-9])github_pat_[A-Za-z0-9_]{22,}")
    add("token", r"(?<![A-Za-z0-9])sk-ant-[A-Za-z0-9_-]{20,}")
    add(
        "token",
        r"(?<![A-Za-z0-9])sk-(?P<body>(?:proj-|svcacct-)?[A-Za-z0-9_-]{20,})",
        accept=_has_digit,
    )
    add("token", r"(?<![A-Za-z0-9])glpat-[A-Za-z0-9_-]{20,}")
    add("token", r"(?<![A-Za-z0-9])(?:sk|rk)_live_[A-Za-z0-9]{20,}")
    add("token", r"(?<![A-Za-z0-9])npm_[A-Za-z0-9]{36}(?![A-Za-z0-9])")
    add("token", r"(?<![A-Za-z0-9])xox[abprs]-[A-Za-z0-9-]{10,}")
    add("token", r"(?<![A-Z0-9])(?:AKIA|ASIA)[0-9A-Z]{16}(?![A-Z0-9])")
    add("token", r"(?<![A-Za-z0-9])AIza[0-9A-Za-z_-]{35}")
    add(
        "token",
        r"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
    )
    add(
        "token",
        r"(?i)\bbearer\s+(?P<body>[A-Za-z0-9._~+/=-]{20,})",
        group=1,
        accept=_has_digit,
    )

    # email
    add(
        "email",
        r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}",
        accept=_email_ok,
    )

    # account-id
    add("account-id", r"\barn:aws[a-z-]*:[a-z0-9-]*:[a-z0-9-]*:(\d{12})(?=:)", group=1)
    add(
        "account-id",
        r"""(?i)\b(?:aws[_-]?)?account[_-]?id\b["']?\s*[:=]\s*["']?(\d{12,14}|[0-9a-f]{32})\b""",
        group=1,
    )

    # home-path
    home_alt = _alt(ctx.home)
    add(
        "home-path",
        rf"(?<![\w.~-])(?P<root>/Users|/home)/(?P<name>[A-Za-z0-9._-]+)(?P<tail>{_PATH_TAIL})",
        accept=_home_ok(ctx),
    )
    add(
        "home-path",
        rf"(?<![A-Za-z0-9])[A-Za-z]:\\{{1,2}}Users\\{{1,2}}{_WIN_FIRST}(?:\\{{1,2}}{_WIN_NEXT})*",
    )
    if home_alt:
        add(
            "home-path",
            rf"(?<![A-Za-z0-9_.-])(?:{home_alt})(?![A-Za-z0-9_.-]){_PATH_TAIL}",
        )

    # scratch-path
    tmp_alt = _alt(ctx.tmp)
    add("scratch-path", rf"(?<![\w.-])/private/tmp(?![A-Za-z0-9_.-]){_PATH_TAIL}")
    add("scratch-path", rf"(?<![\w.-])/tmp/claude-{_PATH_REST}")
    add("scratch-path", rf"(?<![\w.-])(?:/private)?/var/folders/{_PATH_REST}")
    if tmp_alt:
        add(
            "scratch-path",
            rf"(?<![A-Za-z0-9_.-])(?:{tmp_alt})(?![A-Za-z0-9_.-]){_PATH_TAIL}",
        )

    # ip
    add("ip", r"(?<![\w.])(\d{1,3}(?:\.\d{1,3}){3})(?![\w]|\.\d)", accept=_ipv4_ok)
    add("ip", r"(?<![\w:.])[0-9A-Fa-f:]{3,}(?![\w:])", accept=_ipv6_ok)

    # geo
    lat = r"-?(?:90|[1-8]?\d)\.\d{4,}"
    lon = r"-?(?:180|1[0-7]\d|[1-9]?\d)\.\d{4,}"
    core = rf"{lat}\s*,\s*{lon}"
    pair = rf"(?<![\d.])({core})(?!\d|\.\d)"
    # A pair, then any number of further pairs joined by `,`, `;`, and, to or or.
    # The chain is maximal, so a unit after its last pair cannot cut it short.
    sep = r"(?:\s*[,;]\s*|\s+(?:and|to|or)\s+)"
    chain = rf"(?<![\d.])({core}(?:{sep}{core})*)(?!\d|\.\d)(?!{sep}{core})"
    keys = r"coords?|coordinates|geo|geopoint|gps|latlng|latlon|location|position|centre|center|marker"
    add(
        "geo",
        rf"""(?i)\b(?:{keys})\b["']?\s*[:=]\s*[\[({{]?\s*{pair}""",
        group=1,
        accept=_not_null_island(1),
    )
    # Standing alone: the line or cell holds the pair and nothing else.
    add(
        "geo",
        rf"""(?m)(?:^[ \t]*|(?<=[`"'>|])[ \t]*|(?<![\w\])\-.])\([ \t]*){pair}"""
        r"""(?=[ \t]*(?:[`"'<|)]|[.,;:!?]*[ \t]*$))""",
        group=1,
        accept=_not_null_island(1),
    )
    # In a sentence: a location cue, at most two words, then the pair. A `:` or
    # `=` may follow the cue directly (`GPS: ...`).
    add(
        "geo",
        rf"(?i)(?<![\w-])(?:{_GEO_CUES})(?![\w-])(?:[ \t]+[A-Za-z']+){{0,2}}(?:[ \t]+|[ \t]*[:=][ \t]*){chain}"
        rf"{_GEO_UNIT_AFTER}"
        r"(?![ \t]*,[ \t]*-?\d)"  # a third number: not a lat, lng pair
        r"(?![ \t]+-?\d+(?:\.\d+)?[ \t]*,)",  # not the start of an SVG points list
        group=1,
        accept=_not_null_island(1),
    )
    # Degree notation with hemisphere letters needs no cue: `41.8781° N, 87.6298° W`.
    lat_d = r"(?:90|[1-8]?\d)\.\d{2,}"
    lon_d = r"(?:180|1[0-7]\d|[1-9]?\d)\.\d{2,}"
    add(
        "geo",
        rf"(?<![\d.])({lat_d}[ ]?°?[ ]?[NS](?![A-Za-z])[ ]?,?[ ]?{lon_d}[ ]?°?[ ]?[EW](?![A-Za-z]))",
        group=1,
        accept=_not_null_island(1),
    )
    add(
        "geo",
        r"""(?i)\b(?:lat|latitude|lng|lon|long|longitude)\b["']?\s*[:=]\s*["']?(-?\d{1,3}\.\d{4,})""",
        group=1,
    )

    # hostname: suffixes, then literals
    add(
        "hostname",
        r"(?i)(?<![./\w@-])[a-z0-9][a-z0-9-]*(?:\.[a-z0-9-]+)*\.(?:local|lan|internal|home\.arpa|corp)(?![A-Za-z0-9-]|\.[A-Za-z0-9])",
    )
    host_alt = _alt(ctx.hostnames)
    if host_alt:
        add("hostname", rf"(?i)(?<![A-Za-z0-9])(?:{host_alt})(?![A-Za-z0-9])")
    user_alt = _alt(ctx.usernames)
    if user_alt:
        add("username", rf"(?i)(?<![A-Za-z0-9])(?:{user_alt})(?![A-Za-z0-9])")
    return rules


def _placeholder(category: str) -> str:
    return f"[redacted:{category}]"


def _apply(rule: Rule, text: str, counts: dict[str, int]) -> str:
    placeholder = _placeholder(rule.category)

    def repl(m: re.Match[str]) -> str:
        if rule.accept is not None and not rule.accept(m):
            return m.group(0)
        counts[rule.category] = counts.get(rule.category, 0) + 1
        if rule.group == 0:
            return placeholder
        match_start = m.start(0)
        group_start = m.start(rule.group) - match_start
        group_end = m.end(rule.group) - match_start
        matched = m.group(0)
        return matched[:group_start] + placeholder + matched[group_end:]

    return rule.regex.sub(repl, text)


def scrub_text(
    text: str, ctx: Context, rules: list[Rule] | None = None
) -> tuple[str, dict[str, int]]:
    """Return the scrubbed text and the count removed per category.

    `rules` is `build_rules(ctx)`; pass it to reuse one build across calls."""
    if rules is None:
        rules = build_rules(ctx)
    counts: dict[str, int] = {}
    parts = _DATA_URI.split(text)  # odd indexes are data: URIs, left as they are
    for i in range(0, len(parts), 2):
        seg = parts[i]
        for rule in rules:
            seg = _apply(rule, seg, counts)
        parts[i] = seg
    return "".join(parts), counts


def scan_text(
    text: str, ctx: Context, rules: list[Rule] | None = None
) -> dict[str, int]:
    """Count what a scrub would remove, without changing anything."""
    return scrub_text(text, ctx, rules)[1]


# --- CLI -------------------------------------------------------------------


class InputError(Exception):
    """A file cannot be read as text. The message never holds file content."""


def _read(path: Path) -> str:
    try:
        return path.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        raise InputError(f"{path.name}: not UTF-8 text, not scanned") from None
    except OSError as exc:
        raise InputError(f"{path.name}: {exc.strerror}") from None


@dataclass
class FileResult:
    file: str  # relative to the folder the files share
    removed: dict[str, int]
    remaining: dict[str, int]


@dataclass
class RunResult:
    mode: str  # "check" or "scrub"
    files: list[FileResult]

    @property
    def removed(self) -> int:
        return sum(sum(f.removed.values()) for f in self.files)

    @property
    def remaining(self) -> int:
        return sum(sum(f.remaining.values()) for f in self.files)

    @property
    def check(self) -> str:
        return "pass" if self.remaining == 0 else "fail"

    def to_json(self) -> dict:
        return {
            "mode": self.mode,
            "files": [asdict(f) for f in self.files],
            "removed": self.removed,
            "remaining": self.remaining,
            "check": self.check,
        }


def run(paths: list[Path], ctx: Context, check_only: bool) -> RunResult:
    base = Path(os.path.commonpath([str(p.resolve().parent) for p in paths]))
    rules = build_rules(ctx)
    files: list[FileResult] = []
    texts = [_read(path) for path in paths]  # every file is readable before any write
    for path, text in zip(paths, texts):
        if check_only:
            removed: dict[str, int] = {}
            remaining = scan_text(text, ctx, rules)
        else:
            new, removed = scrub_text(text, ctx, rules)
            if new != text:
                path.write_bytes(new.encode("utf-8"))
            remaining = scan_text(_read(path), ctx, rules)
        files.append(
            FileResult(str(path.resolve().relative_to(base)), removed, remaining)
        )
    return RunResult("check" if check_only else "scrub", files)


def _by_category(counts: dict[str, int]) -> str:
    items = [f"{c} {counts[c]}" for c in CATEGORIES if counts.get(c)]
    return ", ".join(items) if items else "none"


def format_text(result: RunResult) -> str:
    """Run-log shaped rows: categories list what was removed (what was found
    in check mode)."""
    rows = [("file", "removed", "remaining", "by category")]
    for f in result.files:
        shown = f.removed or f.remaining
        rows.append(
            (
                f.file,
                str(sum(f.removed.values())),
                str(sum(f.remaining.values())),
                _by_category(shown),
            )
        )
    rows.append(("total", str(result.removed), str(result.remaining), ""))
    widths = [max(len(r[i]) for r in rows) for i in range(3)]
    lines = [
        " | ".join(r[i].ljust(widths[i]) for i in range(3)) + " | " + r[3] for r in rows
    ]
    lines.append(f"check | {result.check}")
    return "\n".join(line.rstrip() for line in lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Scrub published files in place.")
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument(
        "--check", action="store_true", help="report only; exit 1 on any match"
    )
    ap.add_argument("--json", action="store_true", help="print the summary as JSON")
    ap.add_argument(
        "--literal",
        action="append",
        default=[],
        metavar="NAME",
        help="extra username to redact",
    )
    ap.add_argument(
        "--hostname",
        action="append",
        default=[],
        metavar="NAME",
        help="extra hostname to redact",
    )
    ap.add_argument(
        "--no-auto",
        action="store_true",
        help="skip the current user, host, $HOME and $TMPDIR",
    )
    args = ap.parse_args(argv)

    ctx = Context() if args.no_auto else auto_context()
    ctx.usernames += [n for n in args.literal if n]
    ctx.hostnames += [n for n in args.hostname if n]
    try:
        result = run(args.files, ctx, args.check)
    except InputError as exc:
        print(f"scrub: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result.to_json(), indent=2) if args.json else format_text(result))
    return 0 if result.check == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
