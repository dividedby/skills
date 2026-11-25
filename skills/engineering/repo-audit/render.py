"""Build the repo-audit report page from findings.json and page-extra.json.

    render.py [--check] [--template FILE] [-o PAGE.html] FINDINGS_JSON EXTRA_JSON

The page's markup is template.html, read at run time: its `<!-- repeat: name -->`
blocks are cloned once per item and its `{{TOKEN}}` placeholders filled. What
the page says comes from two files. findings.json (evals/findings.schema.json)
supplies everything computed: the header's commit and branch, the verdict pill,
the blockers, the scorecard and coverage tables, the finding rows and their
order, the "Since the last run" section. page-extra.json
(page-extra.schema.json) supplies what only the main session writes: the
prose, the plan, the fleet-standards rows, extra tables, screenshots, mockups,
research. Verdicts and severities are copied from findings.json, never worked
out here.

Escaping: every string from findings.json, and the plain `text` fields of
page-extra.json, is HTML-escaped. `prose` fields are trusted inline HTML, parsed
and held to an allowlist of tags and attributes; other tags, event handlers,
unsafe link schemes, `url()` and literal colours are
errors in them. A screenshot is read from its `path` (relative to the
page-extra.json folder) and embedded as a `data:` URI; it is not resized.

The page is built in memory and written only when it is whole: no `{{TOKEN}}`
or repeat marker left, every `#link` has an id, ids are unique and tags are
balanced. `--check` builds and writes nothing. Both inputs are checked against
their schemas with the validator in evals/findings_check.py, loaded by path
when first needed.

Exit 0: page written (or inputs and page valid under --check). Exit 1: the
inputs or the page are invalid; one message per line on stderr, nothing
written. Exit 2: usage, or a file is missing, not UTF-8 or not JSON.
Standard library only. The published page still goes through scrub.py.
"""

from __future__ import annotations

import argparse
import base64
import html
import importlib.util
import json
import re
import sys
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable, ClassVar

HERE = Path(__file__).resolve().parent
DEFAULT_TEMPLATE = HERE / "template.html"
FINDINGS_SCHEMA = HERE / "evals" / "findings.schema.json"
EXTRA_SCHEMA = HERE / "page-extra.schema.json"
CHECKER = HERE / "evals" / "findings_check.py"

DASH = "—"
CHECK = "✓"

# Rubric order is page order; titles are rubric.md's Areas table (a test compares them).
AREAS: dict[str, str] = {
    "code-quality": "Code quality",
    "architecture": "Architecture",
    "tech-stack": "Tech stack, dependencies and supply chain",
    "tests": "Tests",
    "security": "Security",
    "privacy": "Privacy",
    "data-integrity": "Data integrity",
    "performance": "Performance",
    "accessibility": "Accessibility",
    "content-branding": "Content, copy and branding",
    "usability": "Usability and flows",
    "feature-completeness": "Feature completeness vs docs",
    "repo-hygiene": "Repo organisation, docs and hygiene",
    "ops-release": "Ops, release and observability",
    "external-facts": "External facts",
    "agent-readiness": "Agent readiness",
}
DESIGN_AREAS = ("accessibility", "content-branding", "usability")

# severity -> (CSS class, label, sort rank)
SEVERITIES = {
    "blocker": ("blocker", "BLOCKER", 0),
    "high": ("hi", "HIGH", 1),
    "med": ("med", "MED", 2),
    "low": ("low", "LOW", 3),
}
# verdict -> (CSS class, label)
VERDICTS = {
    "not_ready": ("not-ready", "Not ready"),
    "ready_with_fixes": ("fixes", "Ready with fixes"),
    "ready": ("ready", "Ready"),
    "not_assessed": ("not-assessed", "Not assessed"),
}
# fleet-standards result -> (CSS class, label)
RESULTS = {
    "pass": ("pass", "PASS"),
    "fail": ("fail", "FAIL"),
    "na": ("na", "N/A"),
    "unchecked": ("unchecked", "NOT CHECKED"),
}
REPORT_ONLY = {"OK": ("pass", "OK"), "FLAG": ("unchecked", "FLAG")}
SINCE_GROUPS = [
    ("new", "New"),
    ("fixed", "Fixed"),
    ("still_open", "Still open"),
    ("not_rechecked", "Not re-checked"),
    ("not_reraised", "Not re-raised"),
]
MAX_MOCKUPS = 3
IMAGE_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}

# What the page contains, for the test that compares it with template.html.
SECTION_IDS = frozenset(
    {
        "scorecard",
        "plan",
        "since",
        "standards",
        "rules",
        "coverage",
        "measurements",
        "screens",
        "mockups",
        "research",
        "checked",
    }
)
REPEATS = frozenset(
    {
        "nav-link",
        "blocker-item",
        "evidence-table",
        "evidence-head",
        "evidence-row",
        "evidence-cell",
        "plan-item",
        "since-item",
        "area-section",
        "finding-row",
        "standard-row",
        "screenshot",
        "mockup",
        "mockup-note",
        "research-source",
        "verified-item",
        "corrected-item",
        "merged-item",
        "disputed-item",
        "unverified-item",
    }
)
TOKENS = frozenset(
    {
        "PROJECT",
        "SCOPE_REPO",
        "SCOPE_BRANCH",
        "SCOPE_COMMIT",
        "SCOPE_DATE",
        "SUMMARY_LEDE",
        "METHOD_NOTE",
        "NAV_ID",
        "NAV_LABEL",
        "VERDICT_CLASS",
        "OVERALL_VERDICT",
        "OVERALL_TEXT",
        "FINDING_ID",
        "BLOCKER_NAME",
        "AREA_NAME",
        "TABLE_CAPTION",
        "HEAD_CELL",
        "CELL",
        "PLAN_INTRO",
        "NOW_WHEN",
        "NEXT_WHEN",
        "LATER_WHEN",
        "ITEM_TEXT",
        "EFFORT",
        "SINCE_INTRO",
        "SINCE_STATE",
        "SINCE_KEY",
        "SINCE_NOTE",
        "AREA_ID",
        "AREA_TITLE",
        "AREA_INTRO",
        "SEV_CLASS",
        "SEVERITY",
        "FINDING",
        "ALSO_REPORTED_BY",
        "EVIDENCE",
        "FIX",
        "STANDARDS_INTRO",
        "STANDARD_ID",
        "STANDARD_REQUIREMENT",
        "STANDARD_SOURCE",
        "RESULT_CLASS",
        "RESULT_LABEL",
        "STANDARD_EVIDENCE",
        "STANDARD_FIX",
        "RULES_INTRO",
        "COVERAGE_INTRO",
        "MEASUREMENTS_INTRO",
        "SCREENS_INTRO",
        "IMG_ALT",
        "IMG_NAME",
        "IMG_CAPTION",
        "MOCKUPS_INTRO",
        "MOCKUP_TITLE",
        "MOCKUP_CONTEXT",
        "MOCKUP_WIDTH",
        "MOCKUP_HTML",
        "MOCKUP_NOTE",
        "RESEARCH_INTRO",
        "SOURCE_TOPIC",
        "SOURCE_SUMMARY",
        "SOURCE_URL",
        "SOURCE_TITLE",
        "RESEARCH_GAPS",
        "VERIFIED_ITEM",
        "CORRECTED_ITEM",
        "MERGED_ITEM",
        "DISPUTED_ITEM",
        "UNVERIFIED_ITEM",
    }
)

AREA_TEMPLATE_ID = "{{AREA_ID}}"
MAX_MESSAGE = 160


class RenderError(Exception):
    """The inputs or the page are invalid; `errors` holds one message per line."""

    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


class InputError(Exception):
    """A file could not be read: missing, not UTF-8 or not JSON."""


# --------------------------------------------------------------- the template


@dataclass
class Repeat:
    name: str
    children: list[Any] = field(default_factory=list)  # str | Repeat


@dataclass
class Section:
    id: str
    nodes: list[Any]


@dataclass
class Template:
    head: list[Any]
    sections: list[Section]
    tail: str
    table_node: Repeat  # the generic evidence-table, cloned wherever a table goes


_REPEAT_RE = re.compile(r"<!--\s*(/?)repeat(?::\s*([\w-]+))?\s*-->")
_TOKEN_RE = re.compile(r"\{\{([A-Z][A-Z_]*)\}\}")
_H2_ID_RE = re.compile(r'<h2 id="([^"]*)"')
_TAIL_RE = re.compile(r"</div>\s*<script>")


def _strip_header(text: str) -> str:
    """Drop the leading comment (the human notes on editing the markup)."""
    stripped = text.lstrip()
    if stripped.startswith("<!--") and not _REPEAT_RE.match(stripped):
        end = stripped.find("-->")
        if end == -1:
            raise RenderError(["template: the header comment is not closed"])
        return stripped[end + 3 :].lstrip("\n")
    return text


def _close_of_div(text: str, start: int) -> int:
    """Index of the `</div>` that closes the div whose open tag ends at `start`."""
    depth = 1
    for m in re.finditer(r"<div\b|</div>", text[start:]):
        depth += 1 if m.group(0) != "</div>" else -1
        if depth == 0:
            return start + m.start()
    raise RenderError(["template: a div is not closed"])


def _mockup_token(text: str) -> str:
    """Replace the sample inside `.mk` with the MOCKUP_HTML token."""
    m = re.search(r'<div class="mk">', text)
    if not m:
        raise RenderError(['template: no `<div class="mk">` mockup frame'])
    return text[: m.end()] + "{{MOCKUP_HTML}}" + text[_close_of_div(text, m.end()) :]


def parse_repeats(text: str) -> list[Any]:
    """Nest the text by its repeat markers: strings and Repeat nodes."""
    root: list[Any] = []
    stack: list[Any] = [("", root)]
    pos = 0
    for m in _REPEAT_RE.finditer(text):
        if m.start() > pos:
            stack[-1][1].append(text[pos : m.start()])
        pos = m.end()
        if m.group(1):
            if len(stack) == 1:
                raise RenderError(["template: a /repeat marker has no opener"])
            name, kids = stack.pop()
            stack[-1][1].append(Repeat(name, kids))
        elif m.group(2):
            stack.append((m.group(2), []))
        else:
            raise RenderError(["template: a repeat marker has no name"])
    if len(stack) != 1:
        raise RenderError([f"template: repeat `{stack[-1][0]}` is not closed"])
    if pos < len(text):
        root.append(text[pos:])
    return root


def load_template(text: str) -> Template:
    """Split template.html into the head, one Section per h2 and the closing tail."""
    nodes = parse_repeats(_mockup_token(_strip_header(text)))
    head: list[Any] = []
    sections: list[Section] = []
    cur = head
    for node in nodes:
        if isinstance(node, Repeat):
            if node.name == "area-section":
                sections.append(Section(AREA_TEMPLATE_ID, node.children))
                cur = []  # the whitespace after it belongs to nothing
            else:
                cur.append(node)
            continue
        for i, part in enumerate(re.split(r"(?=<h2 )", node)):
            if i == 0:
                cur.append(part)
            else:
                m = _H2_ID_RE.match(part)
                if not m:
                    raise RenderError(["template: an h2 has no id"])
                sections.append(Section(m.group(1), [part]))
                cur = sections[-1].nodes
    if not sections or not isinstance(sections[-1].nodes[-1], str):
        raise RenderError(["template: the last section does not end in text"])
    last = sections[-1].nodes[-1]
    m = _TAIL_RE.search(last)
    if not m:
        raise RenderError(["template: no `</div>` then `<script>` after the sections"])
    sections[-1].nodes[-1] = last[: m.start()]
    tail = last[m.start() :]
    table = next(
        (
            n
            for s in sections
            if s.id == "scorecard"
            for n in s.nodes
            if _is(n, "evidence-table")
        ),
        None,
    )
    if table is None:
        raise RenderError(["template: the scorecard has no evidence-table block"])
    return Template(head, sections, tail, table)


def _is(node: Any, name: str) -> bool:
    return isinstance(node, Repeat) and node.name == name


def template_inventory(text: str) -> dict[str, Any]:
    """Tokens, repeat names and section ids the template carries (for the drift test)."""
    body = _mockup_token(_strip_header(text))
    names = {m.group(2) for m in _REPEAT_RE.finditer(body) if m.group(2)}
    ids = {m.group(1) for m in _H2_ID_RE.finditer(body)} - {AREA_TEMPLATE_ID}
    return {
        "tokens": set(_TOKEN_RE.findall(body)),
        "repeats": names,
        "sections": ids,
    }


# ---------------------------------------------------------------- expansion


@dataclass
class Item:
    tokens: dict[str, str]
    children: dict[str, list[Item]] = field(default_factory=dict)
    extra: dict[str, str] = field(default_factory=dict)


Hook = Callable[[str, Item], str]


def _wide(markup: str, item: Item) -> str:
    """A table with more than four columns gets class wide, whatever the template had."""
    cls = (
        '<table class="wide">'
        if len(item.children.get("evidence-head", [])) > 4
        else "<table>"
    )
    return re.sub(r'<table(?: class="wide")?>', cls, markup, count=1)


def _finding_row(markup: str, item: Item) -> str:
    return re.sub(r'\s*<span class="src">Also reported by:\s*</span>', "", markup)


def _standard_row(markup: str, item: Item) -> str:
    return re.sub(r'<span class="sev\s*"></span>', "", markup)


def _area_section(markup: str, item: Item) -> str:
    """Extra tables go after the intro, before the finding table."""
    tables = item.extra.get("tables", "")
    if not tables:
        return markup
    marker = '<div class="tablewrap">'
    at = markup.find(marker)
    return markup if at == -1 else markup[:at] + tables + markup[at:]


_HOOKS: dict[str, Hook] = {
    "evidence-table": _wide,
    "finding-row": _finding_row,
    "standard-row": _standard_row,
}


def expand(
    nodes: list[Any], item: Item, inherited: dict[str, str] | None = None
) -> str:
    """Fill the nodes once for item: its tokens, then each child block per child item.

    A name that occurs several times among the nodes (plan-item, once per phase) takes
    its items from `name#k` for the k-th occurrence, else from `name`. A token no item
    supplies is left in place, and the output check fails on it.
    """
    scope = {**(inherited or {}), **item.tokens}
    out: list[str] = []
    seen: dict[str, int] = {}
    for node in nodes:
        if isinstance(node, str):
            out.append(_TOKEN_RE.sub(lambda m: scope.get(m.group(1), m.group(0)), node))
            continue
        k = seen.get(node.name, 0)
        seen[node.name] = k + 1
        kids = item.children.get(f"{node.name}#{k}", item.children.get(node.name, []))
        hook = _HOOKS.get(node.name)
        for child in kids:
            piece = expand(node.children, child, scope)
            out.append(hook(piece, child) if hook else piece)
    return "".join(out)


def table_item(caption: str, head: list[str], rows: list[list[str]]) -> Item:
    """One evidence-table. Caption and head are plain text; cells are ready HTML."""
    return Item(
        {"TABLE_CAPTION": esc(caption)},
        {
            "evidence-head": [Item({"HEAD_CELL": esc(h)}) for h in head],
            "evidence-row": [
                Item({}, {"evidence-cell": [Item({"CELL": c}) for c in row]})
                for row in rows
            ],
        },
    )


def esc(value: Any) -> str:
    """Escape data for text or an attribute. A double brace is written as character
    references, so a value can never read as a template token."""
    return html.escape(str(value), quote=True).replace("{{", "&#123;&#123;")


# ------------------------------------------------------- trusted markup rules

# Tags the prose and the mockup frames (snippets.html) use. Anything else is refused:
# no script, style, iframe, object, embed, base, form, input, img, link or meta.
_ALLOWED_TAGS = frozenset(
    re.findall(
        r"[\w-]+",
        "a abbr b blockquote br code del div em h3 h4 h5 h6 hr i kbd li mark ol p pre s small "
        "span strong sub sup table tbody td tfoot th thead tr u ul "
        "svg g path rect circle ellipse line polyline polygon text tspan",
    )
)
_SVG_TAGS = frozenset(
    re.findall(
        r"[\w-]+", "svg g path rect circle ellipse line polyline polygon text tspan"
    )
)
_GLOBAL_ATTRS = frozenset({"class", "id", "style", "title", "role", "lang", "dir"})
_TAG_ATTRS = {
    "a": {"href"},
    "td": {"colspan", "rowspan"},
    "th": {"colspan", "rowspan", "scope"},
}
_SVG_ATTRS = frozenset(
    re.findall(
        r"[\w-]+",
        "viewbox width height x y cx cy r rx ry x1 y1 x2 y2 d points transform fill fill-rule "
        "stroke stroke-width stroke-linecap stroke-linejoin stroke-dasharray opacity "
        "font-size text-anchor focusable",
    )
)
_COLOUR_ATTRS = frozenset(
    re.findall(
        r"[\w-]+", "fill stroke color bgcolor stop-color flood-color lighting-color"
    )
)
_URL_SCHEMES = frozenset({"http", "https", "mailto"})
_COLOUR_VALUE_RE = re.compile(
    r"#[0-9a-f]{3,8}\b|\b(?:rgb|rgba|hsl|hsla|hwb|lab|lch|oklab|oklch|color|color-mix)\(",
    re.IGNORECASE,
)
_VAR_RE = re.compile(r"var\(\s*--[\w-]+\s*(?:,([^()]*))?\)", re.IGNORECASE)
# CSS named colours; `currentColor`, `none`, `transparent` and `inherit` are not literal.
_NAMED_COLOURS = frozenset(
    re.findall(
        r"\w+",
        "aliceblue antiquewhite aqua aquamarine azure beige bisque black blanchedalmond blue blueviolet brown "
        "burlywood cadetblue chartreuse chocolate coral cornflowerblue cornsilk crimson cyan darkblue darkcyan "
        "darkgoldenrod darkgray darkgreen darkgrey darkkhaki darkmagenta darkolivegreen darkorange darkorchid "
        "darkred darksalmon darkseagreen darkslateblue darkslategray darkslategrey darkturquoise darkviolet "
        "deeppink deepskyblue dimgray dimgrey dodgerblue firebrick floralwhite forestgreen fuchsia gainsboro "
        "ghostwhite gold goldenrod gray green greenyellow grey honeydew hotpink indianred indigo ivory khaki "
        "lavender lavenderblush lawngreen lemonchiffon lightblue lightcoral lightcyan lightgoldenrodyellow "
        "lightgray lightgreen lightgrey lightpink lightsalmon lightseagreen lightskyblue lightslategray "
        "lightslategrey lightsteelblue lightyellow lime limegreen linen magenta maroon mediumaquamarine "
        "mediumblue mediumorchid mediumpurple mediumseagreen mediumslateblue mediumspringgreen mediumturquoise "
        "mediumvioletred midnightblue mintcream mistyrose moccasin navajowhite navy oldlace olive olivedrab "
        "orange orangered orchid palegoldenrod palegreen paleturquoise palevioletred papayawhip peachpuff peru "
        "pink plum powderblue purple rebeccapurple red rosybrown royalblue saddlebrown salmon sandybrown "
        "seagreen seashell sienna silver skyblue slateblue slategray slategrey snow springgreen steelblue tan "
        "teal thistle tomato turquoise violet wheat white whitesmoke yellow yellowgreen",
    )
)
_NON_COLOUR_PROPS = ("font", "content", "grid", "counter", "animation", "transition")


def _literal_colour(value: str) -> bool:
    """A hex, colour function or named colour; `var(--x)` is a token, its fallback is not."""
    previous = None
    while previous != value:  # innermost var() first; keep only the fallback
        previous = value
        value = _VAR_RE.sub(lambda m: " " + (m.group(1) or "") + " ", value)
    if _COLOUR_VALUE_RE.search(value):
        return True
    return any(w in _NAMED_COLOURS for w in re.findall(r"[a-z]+", value.lower()))


def _url_problem(value: str) -> str | None:
    """Why a link target is refused, or None. Whitespace and control characters are
    dropped first, as a browser does, so `java\tscript:` is `javascript:`."""
    value = re.sub(r"[\x00-\x20\x7f]+", "", value).lower().replace("\\", "/")
    if value.startswith("#"):
        return None
    if value.startswith("//"):  # `\\host` and `/\host` too: browsers read `\` as `/`
        return "a protocol-relative URL"
    m = re.match(r"([a-z][a-z0-9+.-]*):", value)
    if m is None:
        return None  # a relative path
    return None if m.group(1) in _URL_SCHEMES else f"a {m.group(1)}: URL"


def _style_problems(value: str) -> list[str]:
    if re.search(r"url\s*\(|@import|expression\s*\(|\\|/\*", value, re.IGNORECASE):
        return ["url(), a backslash escape or a comment in a style attribute"]
    # image-set() and cross-fade() fetch a quoted URL with no url() around it.
    if re.search(r"image-set\s*\(|cross-fade\s*\(|element\s*\(", value, re.IGNORECASE):
        return [
            "an image function (image-set, cross-fade, element) in a style attribute"
        ]
    for decl in value.split(";"):
        prop, _, val = decl.partition(":")
        if not prop.strip().lower().startswith(_NON_COLOUR_PROPS) and _literal_colour(
            val
        ):
            return ["a literal colour in a style attribute (use a var(--...) token)"]
    return []


class _Markup(HTMLParser):
    """Walk trusted prose with the HTML parser, so attribute names and values are
    what a browser sees: unquoted, entity-encoded and `<tag/attr=...>` forms included."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.problems: list[str] = []

    def add(self, problem: str) -> None:
        if problem not in self.problems:
            self.problems.append(problem)

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        for name, _ in attrs:
            if name.startswith("on"):
                self.add(f"an event-handler attribute ({name[:20]})")
        if tag not in _ALLOWED_TAGS:
            self.add(f"a <{tag[:20]}> tag is not allowed")
            return
        allowed = _GLOBAL_ATTRS | _TAG_ATTRS.get(tag, set())
        if tag in _SVG_TAGS:
            allowed = allowed | _SVG_ATTRS
        for name, raw in attrs:
            value = raw or ""
            if name.startswith("on"):
                continue  # reported above
            if name == "srcset":
                self.add("a srcset attribute is not allowed")
            elif name == "style":
                for problem in _style_problems(value):
                    self.add(problem)
            elif name in (
                "href",
                "src",
                "xlink:href",
                "action",
                "formaction",
                "poster",
                "srcset",
            ):
                problem = _url_problem(value) if name != "srcset" else "a srcset"
                if name not in allowed:
                    self.add(f"the `{name}` attribute is not allowed on <{tag}>")
                elif problem:
                    self.add(f"{problem} is not allowed in {name}")
            elif name in _COLOUR_ATTRS and _literal_colour(
                re.sub(r"url\(#[\w-]+\)", "", value)
            ):
                self.add(f"a literal colour in {name} (use a var(--...) token)")
            elif name not in allowed and not name.startswith(("aria-", "data-")):
                self.add(f"the `{name[:20]}` attribute is not allowed on <{tag}>")

    def handle_startendtag(self, tag: str, attrs: Any) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if tag not in _ALLOWED_TAGS:
            self.add(f"a </{tag[:20]}> tag is not allowed")

    def handle_data(self, data: str) -> None:
        if re.search(r"<[a-zA-Z/!?]", data):
            self.add("a stray `<` that starts no tag")

    def handle_comment(self, data: str) -> None:
        self.add("an HTML comment is not allowed")

    def handle_decl(self, decl: str) -> None:
        self.add("a declaration is not allowed")

    def handle_pi(self, data: str) -> None:
        self.add("a processing instruction is not allowed")

    def unknown_decl(self, data: str) -> None:
        self.add("a CDATA or conditional section is not allowed")


def markup_problems(markup: str) -> list[str]:
    """Why a trusted string may not go into the page; empty when it may."""
    parser = _Markup()
    parser.feed(markup)
    if parser.rawdata.strip():  # the parser holds back a tag that never ends
        parser.add("an unterminated tag")
    parser.close()
    return parser.problems


# ----------------------------------------------------------- the output check


class _Structure(HTMLParser):
    VOID: ClassVar[set[str]] = {
        "area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
        "source", "track", "wbr",
    }  # fmt: skip

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.ids: list[str] = []
        self.hrefs: list[str] = []
        self.errors: list[str] = []

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        for name, value in attrs:
            if name == "id" and value is not None:
                self.ids.append(value)
            elif name == "href" and value and value.startswith("#") and len(value) > 1:
                self.hrefs.append(value[1:])
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag: str, attrs: Any) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.stack.pop()

    def handle_endtag(self, tag: str) -> None:
        if tag in self.VOID:
            return
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(
                f"unbalanced tags: </{tag}> closes <{self.stack[-1] if self.stack else 'nothing'}>"
            )
            if tag in self.stack:
                while self.stack.pop() != tag:
                    pass
            return
        self.stack.pop()


def check_output(page: str) -> list[str]:
    """Problems that make a built page unfit to ship; empty when it is whole."""
    errors: list[str] = []
    left = sorted(set(re.findall(r"\{\{[A-Z_@]+\}\}", page)))
    if left:
        errors.append("unfilled tokens left in the page: " + ", ".join(left))
    if re.search(r"<!--\s*/?repeat\b", page):
        errors.append("a repeat marker is left in the page")
    parser = _Structure()
    parser.feed(page)
    parser.close()
    errors += parser.errors[:5]
    if parser.stack:
        errors.append("unclosed tags: " + ", ".join(parser.stack[:5]))
    seen = set()
    for ident in parser.ids:
        if ident in seen:
            errors.append(f"duplicate id `{ident}`")
        seen.add(ident)
    for target in sorted(set(parser.hrefs) - seen):
        errors.append(f"dangling link #{target}")
    return errors


# ------------------------------------------------------------------- building


def _fact(profile: list[dict[str, Any]], name: str) -> str | None:
    for row in profile:
        if str(row.get("fact", "")).strip().lower() == name:
            return str(row.get("value"))
    return None


def _natural(text: str) -> list[Any]:
    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", text)]


def _evidence(value: Any) -> str:
    return "; ".join(str(v) for v in value) if isinstance(value, list) else str(value)


def _pill(verdict: str) -> str:
    cls, label = VERDICTS[verdict]
    return f'<span class="pill {cls}">{label}</span>'


def _link(ident: str) -> str:
    return f'<a href="#{esc(ident)}">{esc(ident)}</a>'


class _Build:
    def __init__(
        self, findings: dict[str, Any], extra: dict[str, Any], tpl: Template, base: Path
    ):
        self.f = findings
        self.x = extra
        self.tpl = tpl
        self.base = base
        self.errors: list[str] = []
        self.intros: dict[str, str] = extra["intros"]
        self.card: dict[str, Any] = findings["scorecard"]
        self.card_areas = {r["area"]: r for r in self.card["areas"]}
        self.cov_areas = {r["area"]: r for r in findings["coverage"]}
        self.by_id = {f["id"]: f for f in findings["findings"]}
        self.rows: dict[str, list[dict[str, Any]]] = {a: [] for a in AREAS}
        for f in findings["findings"]:
            if not f["id"].startswith("fs-"):
                self.rows[f["area"]].append(f)
        for rows in self.rows.values():
            rows.sort(key=lambda f: (SEVERITIES[f["severity"]][2], _natural(f["id"])))
        self.standards: list[dict[str, Any]] = extra["standards"]["rows"]

    def err(self, message: str) -> None:
        self.errors.append(message)

    def prose(self, value: str, where: str) -> str:
        for problem in markup_problems(value):
            self.err(f"{where}: {problem}")
        return value.replace("{{", "&#123;&#123;")

    # -- consistency

    def depth_errors(self) -> None:
        """At quick depth, an applicable area of an unlaunched lens must read Not assessed (depth)."""
        depth = (_fact(self.f["profile"], "depth") or "").strip().lower()
        if depth != "quick":
            return
        owner = _load_checker().AREA_OWNER
        launched = {r["lens"] for r in self.f["lens_coverage"]}
        for area, row in self.card_areas.items():
            lens = owner.get(area)
            if (
                lens is None
                or lens in launched
                or row.get("applies") is not True
                or row.get("verdict") == "not_assessed"
            ):
                continue
            self.err(
                f"scorecard.areas: `{area}` belongs to the `{lens}` lens, which a "
                f"quick run does not launch; it must read Not assessed with the "
                f'reason "Depth: quick run, `{lens}` lens not launched", '
                f"not `{row.get('verdict')}`"
            )

    # -- selection

    def area_ids(self) -> list[str]:
        """Areas with a section: a finding row, or an intro written for it."""
        out = []
        for area in AREAS:
            has_rows, intro = bool(self.rows[area]), area in self.intros
            verdict = self.card_areas.get(area, {}).get("verdict")
            if intro and verdict == "not_assessed":
                self.err(f"intros.{area}: a Not-assessed area has no section")
            elif has_rows or intro:
                out.append(area)
                if not intro:
                    self.err(f"intros.{area}: the area has findings but no intro")
        return out

    # -- sections

    def head(self, nav: list[Item]) -> Item:
        profile = self.f["profile"]
        commit, branch = _fact(profile, "commit"), _fact(profile, "branch")
        for name, value in (("commit", commit), ("branch", branch)):
            if not value:
                self.err(f"findings.json: no `{name}` row in the profile")
        project = esc(self.x["project"])
        return Item(
            {
                "PROJECT": project,
                "SCOPE_REPO": esc(self.x["repo"]),
                "SCOPE_BRANCH": esc(branch or ""),
                "SCOPE_COMMIT": esc((commit or "")[:7]),
                "SCOPE_DATE": esc(self.x["scope_date"]),
                "SUMMARY_LEDE": self.prose(self.x["lede"], "lede"),
                "METHOD_NOTE": self.prose(self.x["method_note"], "method_note"),
            },
            {"nav-link": nav},
        )

    def scorecard(self, area_sections: list[str]) -> Item:
        overall = self.card["overall"]
        blockers = []
        for ident in self.card["blockers"]:
            found = self.by_id.get(ident)
            if not found:
                self.err(f"scorecard.blockers: no finding `{ident}`")
                continue
            blockers.append(
                Item(
                    {
                        "FINDING_ID": esc(ident),
                        "BLOCKER_NAME": esc(found["title"]),
                        "AREA_NAME": esc(AREAS[found["area"]]),
                    }
                )
            )
        rows = []
        for area, title in AREAS.items():
            row = self.card_areas.get(area)
            if row is None:
                self.err(f"scorecard.areas: no row for `{area}`")
                continue
            name = (
                f'<a href="#{area}">{esc(title)}</a>'
                if area in area_sections
                else esc(title)
            )
            rows.append([name, *self._verdict_cells(row)])
        tables = [
            table_item(
                "Verdict per area", ["Area", "Verdict", "Top finding", "Link"], rows
            )
        ]
        if self.card["packages"]:
            pkg = [
                [esc(p["package"]), esc(p.get("type", DASH)), *self._verdict_cells(p)]
                for p in self.card["packages"]
            ]
            tables.append(
                table_item(
                    "Verdict per package",
                    ["Package", "Type", "Verdict", "Top finding", "Link"],
                    pkg,
                )
            )
        cls, label = VERDICTS[overall]
        return Item(
            {
                "VERDICT_CLASS": cls,
                "OVERALL_VERDICT": label,
                "OVERALL_TEXT": self.prose(self.x["overall_text"], "overall_text"),
            },
            {"blocker-item": blockers, "evidence-table": tables},
        )

    def _verdict_cells(self, row: dict[str, Any]) -> list[str]:
        """Verdict pill, top finding and link cells of a scorecard area or package row."""
        verdict = row["verdict"]
        top = row.get("top_finding")
        if verdict == "not_assessed":
            return [_pill(verdict), esc(row.get("not_assessed_reason") or DASH), DASH]
        if not top:
            return [_pill(verdict), DASH, DASH]
        found = self.by_id.get(top)
        if not found:
            self.err(f"scorecard: top_finding `{top}` is not a finding")
            return [_pill(verdict), DASH, DASH]
        return [_pill(verdict), esc(found["title"]), _link(top)]

    def plan(self) -> Item:
        plan = self.x["plan"]
        now_ids = {i["finding"] for i in plan["now"]["items"]}
        for ident in self.card["blockers"]:
            if ident not in now_ids:
                self.err(f"plan: Blocker `{ident}` is not in Now")
        tokens = {"PLAN_INTRO": self.prose(self.intros["plan"], "intros.plan")}
        children = {}
        for k, phase in enumerate(("now", "next", "later")):
            tokens[f"{phase.upper()}_WHEN"] = self.prose(
                plan[phase]["when"], f"plan.{phase}.when"
            )
            children[f"plan-item#{k}"] = [
                Item(
                    {
                        "ITEM_TEXT": self.prose(
                            i["text"], f"plan.{phase}.items[{n}].text"
                        ),
                        "EFFORT": esc(i["effort"]),
                        "FINDING_ID": esc(i["finding"]),
                    }
                )
                for n, i in enumerate(plan[phase]["items"])
            ]
        return Item(tokens, children)

    def since(self) -> Item | None:
        if "diff" not in self.f:
            if self.x.get("since_notes"):
                self.err("since_notes: findings.json has no `diff`")
            return None
        diff = self.f["diff"]
        extra_intro = self.intros.get("since")
        if diff is None:
            if not extra_intro:
                self.err("intros.since: required when `diff` is null (say why)")
            return Item(
                {"SINCE_INTRO": self.prose(extra_intro or "", "intros.since")},
                {"since-item": []},
            )
        url = diff["previous_url"]
        if not re.match(r"https?://\S+$", url):
            self.err("diff.previous_url: not an http(s) URL")
        counts = ", ".join(
            f"{len(diff[k])} {label.lower()}" for k, label in SINCE_GROUPS
        )
        intro = f'Compared with <a href="{esc(url)}">the previous run</a>: {counts}.'
        if extra_intro:
            intro += " " + self.prose(extra_intro, "intros.since")
        notes = {}
        for n in self.x.get("since_notes", []):
            if not any(n["key"] in diff[k] for k, _ in SINCE_GROUPS):
                self.err(f"since_notes: key `{n['key'][:60]}` is not in `diff`")
            notes[n["key"]] = self.prose(n["note"], "since_notes")
        key_ids = {f["key"]: f["id"] for f in self.f["findings"]}
        items = []
        for group, label in SINCE_GROUPS:
            for key in diff[group]:
                items.append(
                    Item(
                        {
                            "SINCE_STATE": label,
                            "SINCE_KEY": esc(key),
                            "SINCE_NOTE": notes.get(key)
                            or self._since_note(group, key, key_ids),
                        }
                    )
                )
        return Item({"SINCE_INTRO": intro}, {"since-item": items})

    def _since_note(self, group: str, key: str, key_ids: dict[str, str]) -> str:
        if key in key_ids:
            return _link(key_ids[key])
        if group == "not_rechecked":
            reason = self.card_areas.get(key.split(":", 1)[0], {}).get(
                "not_assessed_reason"
            )
            return esc(reason or "")
        if group == "not_reraised":
            return (
                "nothing changed under its path, or the commits could not be compared"
            )
        return ""

    def area(self, area: str, tables: list[Item]) -> Item:
        rows = []
        for f in self.rows[area]:
            cls, label, _ = SEVERITIES[f["severity"]]
            rows.append(
                Item(
                    {
                        "FINDING_ID": esc(f["id"]),
                        "SEV_CLASS": cls,
                        "SEVERITY": label,
                        "FINDING": esc(f["title"]),
                        "ALSO_REPORTED_BY": esc(", ".join(f["also_reported_by"])),
                        "EVIDENCE": esc(_evidence(f["evidence"])),
                        "FIX": esc(f["fix"]),
                        "EFFORT": esc(f["effort"]),
                    }
                )
            )
        rendered = "".join(
            expand([self.tpl.table_node], Item({}, {"evidence-table": [t]}))
            for t in tables
        )
        return Item(
            {
                "AREA_ID": area,
                "AREA_TITLE": esc(AREAS[area]),
                "AREA_INTRO": self.prose(self.intros.get(area, ""), f"intros.{area}"),
            },
            {"finding-row": rows},
            {"tables": rendered},
        )

    def standards_section(self) -> Item:
        rows, seen = [], set()
        for n, r in enumerate(self.standards):
            where = f"standards.rows[{n}]"
            if r["id"] in seen:
                self.err(f"{where}: duplicate id `{r['id']}`")
            seen.add(r["id"])
            cls, label = (
                REPORT_ONLY[r["label"]] if "label" in r else RESULTS[r["result"]]
            )
            if "label" in r and cls != RESULTS[r["result"]][0]:
                self.err(
                    f"{where}: label {r['label']} does not fit result {r['result']}"
                )
            needs_severity = r["result"] == "fail" or r.get("label") == "FLAG"
            sev = r.get("severity")
            if needs_severity != bool(sev):
                self.err(
                    f"{where}: severity {'is required' if needs_severity else 'is only for fail and FLAG rows'}"
                )
            sev_cls, sev_label = (
                (SEVERITIES[sev][0], SEVERITIES[sev][1]) if sev else ("", "")
            )
            if r["result"] == "fail":
                fs = self.by_id.get(f"fs-{r['id']}")
                if fs is None:
                    self.err(f"{where}: a fail row has no finding `fs-{r['id']}`")
                elif sev and fs["severity"] != sev:
                    self.err(
                        f"{where}: severity {sev} differs from finding `fs-{r['id']}` ({fs['severity']})"
                    )
            rows.append(
                Item(
                    {
                        "STANDARD_ID": esc(r["id"]),
                        "STANDARD_REQUIREMENT": self.prose(
                            r["requirement"], f"{where}.requirement"
                        ),
                        "STANDARD_SOURCE": self.prose(r["source"], f"{where}.source"),
                        "RESULT_CLASS": cls,
                        "RESULT_LABEL": label,
                        "SEV_CLASS": sev_cls,
                        "SEVERITY": sev_label,
                        "STANDARD_EVIDENCE": self.prose(
                            r.get("evidence") or DASH, f"{where}.evidence"
                        ),
                        "STANDARD_FIX": self.prose(
                            r.get("fix") or DASH, f"{where}.fix"
                        ),
                    }
                )
            )
        results = {r["id"]: r["result"] for r in self.standards}
        for f in self.f["findings"]:
            if not f["id"].startswith("fs-"):
                continue
            if f["id"][3:] not in results:
                self.err(f"finding `{f['id']}` has no row in standards.rows")
            elif results[f["id"][3:]] != "fail":
                self.err(f"finding `{f['id']}` has a standards row that is not a fail")
        return Item(
            {
                "STANDARDS_INTRO": self.prose(
                    self.intros["standards"], "intros.standards"
                )
            },
            {"standard-row": rows},
        )

    def extra_tables(self, section: str) -> list[Item]:
        out = []
        for n, t in enumerate(self.x.get("tables", [])):
            if t["section"] != section:
                continue
            where = f"tables[{n}]"
            cells = []
            for row in t["rows"]:
                if len(row) != len(t["head"]):
                    self.err(
                        f"{where}: a row has {len(row)} cells, the head {len(t['head'])}"
                    )
                cells.append([self.prose(c, where) for c in row])
            out.append(table_item(t["caption"], t["head"], cells))
        return out

    def coverage(self) -> Item:
        rows = []
        for area, title in AREAS.items():
            cov, card = self.cov_areas.get(area), self.card_areas.get(area)
            if cov is None or card is None:
                self.err(f"coverage: no row for `{area}`")
                continue
            reason = cov["not_assessed_reason"]
            skipped = "; ".join(
                f"{s['method']}: {s['reason']}" for s in cov["skipped_methods"]
            )
            unassessed = bool(reason) or card["verdict"] == "not_assessed"
            rows.append(
                [esc(title)]
                + [
                    CHECK if cov[m] else DASH
                    for m in ("read", "ran", "measured", "browsed")
                ]
                + ["yes" if unassessed else DASH, esc(reason or skipped or DASH)]
            )
        heads = ["Area", "Read", "Ran", "Measured", "Browsed", "Not assessed", "Reason"]
        tables = [table_item("Coverage per area", heads, rows)]
        lens = [
            [esc(r["lens"]), esc(r["read"]), esc(r["chosen_by"])]
            for r in self.f["lens_coverage"]
        ]
        tables.append(
            table_item("Coverage per lens", ["Lens", "Read", "How chosen"], lens)
        )
        return Item(
            {"COVERAGE_INTRO": self.prose(self.intros["coverage"], "intros.coverage")},
            {"evidence-table": tables},
        )

    def screens(self) -> Item | None:
        shots = self.x.get("screens", [])
        if not shots:
            if "screens" in self.intros:
                self.err("intros.screens: given with no screens")
            if "No captures" not in self.x["method_note"]:
                self.err(
                    "method_note: no screens, so it must say `No captures: <reason>`"
                )
            return None
        if "screens" not in self.intros:
            self.err("intros.screens: required when there are screens")
        items = []
        for n, s in enumerate(shots):
            items.append(
                Item(
                    {
                        "IMG_ALT": esc(s["alt"]),
                        "IMG_NAME": self._data_uri(s["path"], f"screens[{n}]"),
                        "IMG_CAPTION": self.prose(
                            s["caption"], f"screens[{n}].caption"
                        ),
                    }
                )
            )
        return Item(
            {
                "SCREENS_INTRO": self.prose(
                    self.intros.get("screens", ""), "intros.screens"
                )
            },
            {"screenshot": items},
        )

    def _data_uri(self, path: str, where: str) -> str:
        mime = IMAGE_TYPES.get(Path(path).suffix.lower())
        if mime is None:
            self.err(
                f"{where}: `{Path(path).suffix}` is not a .jpg, .png or .webp image"
            )
            return ""
        try:
            data = (self.base / path).read_bytes()
        except OSError:
            self.err(f"{where}: cannot read the image file")
            return ""
        return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"

    def mockups(self) -> Item | None:
        shown = self.x.get("mockups", [])
        if not shown:
            if "mockups" in self.intros:
                self.err("intros.mockups: given with no mockups")
            say = self.intros.get("screens", "") + self.x["method_note"]
            if "No mockups" not in say:
                self.err(
                    "no mockups: intros.screens or method_note must say `No mockups: <reason>`"
                )
            return None
        if "mockups" not in self.intros:
            self.err("intros.mockups: required when there are mockups")
        if len(shown) > MAX_MOCKUPS:
            self.err(f"mockups: {len(shown)} given, at most {MAX_MOCKUPS}")
        if not any(
            f["area"] in DESIGN_AREAS and f["severity"] in ("blocker", "high")
            for f in self.f["findings"]
        ):
            self.err(
                "mockups: only when the design lens reported a High or Blocker finding"
            )
        items = []
        for n, m in enumerate(shown):
            where = f"mockups[{n}]"
            items.append(
                Item(
                    {
                        "MOCKUP_TITLE": esc(m["title"]),
                        "MOCKUP_CONTEXT": self.prose(m["context"], f"{where}.context"),
                        "MOCKUP_WIDTH": esc(m["width"]),
                        "MOCKUP_HTML": self.prose(m["html"], f"{where}.html"),
                    },
                    {
                        "mockup-note": [
                            Item({"MOCKUP_NOTE": self.prose(t, f"{where}.notes")})
                            for t in m["notes"]
                        ]
                    },
                )
            )
        return Item(
            {
                "MOCKUPS_INTRO": self.prose(
                    self.intros.get("mockups", ""), "intros.mockups"
                )
            },
            {"mockup": items},
        )

    def research(self) -> Item | None:
        res = self.x.get("research")
        if res is None:
            if "research" in self.intros:
                self.err("intros.research: given with no `research`")
            return None
        if "research" not in self.intros:
            self.err("intros.research: required with `research`")
        sources = [
            Item(
                {
                    "SOURCE_TOPIC": esc(s["topic"]),
                    "SOURCE_SUMMARY": self.prose(s["summary"], "research.sources"),
                    "SOURCE_URL": esc(s["url"]),
                    "SOURCE_TITLE": esc(s["title"]),
                }
            )
            for s in res["sources"]
        ]
        return Item(
            {
                "RESEARCH_INTRO": self.prose(
                    self.intros.get("research", ""), "intros.research"
                ),
                "RESEARCH_GAPS": self.prose(res.get("gaps", ""), "research.gaps"),
            },
            {"research-source": sources},
        )

    def checked(self) -> Item | None:
        lists = self.x.get("checked", {})
        if not any(
            lists.get(k)
            for k in ("verified", "corrected", "merged", "disputed", "unverified")
        ):
            return None
        return Item(
            {},
            {
                f"{k}-item": [
                    Item({f"{k.upper()}_ITEM": self.prose(t, f"checked.{k}")})
                    for t in lists.get(k, [])
                ]
                for k in ("verified", "corrected", "merged", "disputed", "unverified")
            },
        )

    def measurements(self) -> Item | None:
        tables = self.extra_tables("measurements")
        if "measurements" not in self.intros:
            if tables:
                self.err("intros.measurements: required with measurement tables")
            return None
        return Item(
            {
                "MEASUREMENTS_INTRO": self.prose(
                    self.intros["measurements"], "intros.measurements"
                )
            },
            {"evidence-table": tables},
        )


_PRUNES = [
    # a heading whose list came out empty, then any empty list
    re.compile(r'<h3>[^<]*</h3>\s*<ul class="tight">\s*</ul>'),
    re.compile(r'<ul class="tight">\s*</ul>'),
    re.compile(r"<p[^>]*>\s*</p>"),
    # a table with no body rows
    re.compile(
        r'<div class="tablewrap">(?:(?!<div class="tablewrap">).)*?<tbody>\s*</tbody>\s*</table>\s*</div>',
        re.DOTALL,
    ),
]


def _prune(markup: str) -> str:
    for pattern in _PRUNES:
        markup = pattern.sub("", markup)
    return markup


def _drop_nav(markup: str, section: str) -> str:
    return re.sub(rf'\s*<a href="#{re.escape(section)}">[^<]*</a>', "", markup, count=1)


def build_page(
    findings: dict[str, Any], extra: dict[str, Any], template: str, base: Path
) -> str:
    """The finished page. Raises RenderError listing every problem found."""
    tpl = load_template(template)
    b = _Build(findings, extra, tpl, base)
    b.depth_errors()
    area_ids = b.area_ids()
    area_tables = {a: b.extra_tables(a) for a in AREAS}
    for a, tables in area_tables.items():
        if tables and a not in area_ids:
            b.err(f"tables: `{a}` has tables but no section (write intros.{a})")
    builders: dict[str, Callable[[], Item | None]] = {
        "scorecard": lambda: b.scorecard(area_ids),
        "plan": b.plan,
        "since": b.since,
        "standards": b.standards_section,
        "rules": lambda: Item(
            {"RULES_INTRO": b.prose(b.intros["rules"], "intros.rules")},
            {"evidence-table": b.extra_tables("rules")},
        ),
        "coverage": b.coverage,
        "measurements": b.measurements,
        "screens": b.screens,
        "mockups": b.mockups,
        "research": b.research,
        "checked": b.checked,
    }
    dropped: list[str] = []
    body: list[str] = []
    for section in tpl.sections:
        if section.id == AREA_TEMPLATE_ID:
            for area in area_ids:
                item = b.area(area, area_tables[area])
                body.append(_prune(_area_section(expand(section.nodes, item), item)))
            continue
        if section.id not in builders:
            raise RenderError(
                [f"template: section `{section.id}` is not one render.py knows"]
            )
        item = builders[section.id]()
        if item is None:
            dropped.append(section.id)
        else:
            piece = expand(section.nodes, item)
            body.append(piece if section.id == "mockups" else _prune(piece))
    nav = [Item({"NAV_ID": a, "NAV_LABEL": esc(AREAS[a])}) for a in area_ids]
    head = expand(tpl.head, b.head(nav))
    for section_id in dropped:
        head = _drop_nav(head, section_id)
    page = head + "".join(body) + tpl.tail
    if not b.errors:
        b.errors += check_output(page)
    if b.errors:
        raise RenderError(b.errors)
    return page


# ------------------------------------------------------------------------ CLI


def _load_checker() -> Any:
    """findings_check.py loaded by path: no sys.path edit, so it works from any cwd
    and under `python3 -I`, and only when a schema check runs."""
    spec = importlib.util.spec_from_file_location("_repo_audit_findings_check", CHECKER)
    if spec is None or spec.loader is None:
        raise InputError(f"cannot load {CHECKER.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError:
        raise InputError(f"cannot read {path.name}")
    except UnicodeDecodeError:
        raise InputError(f"{path.name} is not UTF-8 text")
    except json.JSONDecodeError as exc:
        raise InputError(f"{path.name} is not JSON ({exc.msg}, line {exc.lineno})")


def schema_errors(findings: Any, extra: Any) -> list[str]:
    checker = _load_checker()
    out = []
    for label, doc, schema in (
        ("findings.json", findings, FINDINGS_SCHEMA),
        ("page-extra.json", extra, EXTRA_SCHEMA),
    ):
        schema_doc = _read_json(schema)
        out += [f"{label} {e}"[:MAX_MESSAGE] for e in checker.validate(doc, schema_doc)]
    return out


def render(findings: Any, extra: Any, template: str, base: Path) -> str:
    """Validate both documents, then build the page."""
    errors = schema_errors(findings, extra)
    if errors:
        raise RenderError(errors)
    return build_page(findings, extra, template, base)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build the repo-audit report page.")
    ap.add_argument("findings", type=Path, help="findings.json")
    ap.add_argument("extra", type=Path, help="page-extra.json")
    ap.add_argument("-o", "--output", type=Path, help="where to write the page")
    ap.add_argument(
        "--check", action="store_true", help="build in memory, write nothing"
    )
    ap.add_argument(
        "--template",
        type=Path,
        default=DEFAULT_TEMPLATE,
        help="markup to fill (default: template.html)",
    )
    args = ap.parse_args(argv)
    if not args.check and args.output is None:
        ap.error("-o is required unless --check")
    try:
        findings, extra = _read_json(args.findings), _read_json(args.extra)
        try:
            template = args.template.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            raise InputError(f"cannot read the template {args.template.name}")
        page = render(findings, extra, template, args.extra.resolve().parent)
    except InputError as exc:
        print(f"render: {exc}", file=sys.stderr)
        return 2
    except RenderError as exc:
        for line in exc.errors:
            print(f"render: {line}", file=sys.stderr)
        return 1
    if args.check:
        print("render: ok (nothing written)")
        return 0
    args.output.write_text(page, encoding="utf-8")
    print(f"render: wrote {args.output.name} ({len(page.encode('utf-8')):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
