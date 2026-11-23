"""Generate the repo-audit eval fixtures: five small synthetic git repos.

Each fixture plants the same four defects (a hard-coded secret, a stale dated
constant, a README command that does not exist, a duplicate file); the shapes
differ. The output is deterministic: running the generator twice gives the same
commit and tree SHAs. Nothing is written inside this repo; the caller names the
output directory.

Run: python3 fixtures.py <outdir> [--only single-script,docs-only]
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

FIXTURES = ["single-script", "docs-only", "workspace", "static-site", "unknown-type"]
MARKER = ".eval-fixture-root"

# A file is its text and whether it is executable.
File = tuple[str, bool]
# A commit is its message and the files it adds or changes.
Commit = tuple[str, dict[str, File]]

# 2026-01-15T12:00:00Z; each commit is one minute after the last.
_BASE_EPOCH = 1768478400

# The token is assembled at runtime so that no committed file holds a literal
# that a secret scanner would flag. The body is mixed-case alphanumeric so that
# gitleaks' entropy check accepts it.
_TOKEN_BODY = "aB3dE5fG7hI9jK1lM3nO5pQ7rS9tU1vW3xY5"
assert len(_TOKEN_BODY) == 36


class FixtureError(Exception):
    pass


def fake_token() -> str:
    """A fake GitHub personal access token. Not a credential for anything."""
    return "g" + "hp_" + _TOKEN_BODY


def _file(text: str, exe: bool = False) -> File:
    return (text, exe)


# ---------------------------------------------------------------- single-script

_TOOL_PY = '''\
#!/usr/bin/env python3
"""Summarise an invoice CSV and apply the payment processor fee."""

import argparse
import csv
import sys

# Payment processor fee schedule. The percentages are valid until this date.
RATES_VALID_UNTIL = "2019-12-31"
FEE_PERCENT = 2.9
FEE_FIXED_CENTS = 30


def load_rows(path):
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle))


def fee(amount_cents):
    return round(amount_cents * FEE_PERCENT / 100) + FEE_FIXED_CENTS


def summarise(rows):
    gross = sum(int(row["amount_cents"]) for row in rows)
    fees = sum(fee(int(row["amount_cents"])) for row in rows)
    return {"count": len(rows), "gross_cents": gross, "fee_cents": fees}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", help="invoice CSV with an amount_cents column")
    args = parser.parse_args(argv)
    summary = summarise(load_rows(args.csv_path))
    for name, value in summary.items():
        print(f"{name}: {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''

_SS_README_1 = """\
# invoice-summary

A single script that totals an invoice CSV and the processor fees on it.

## Usage

    python3 tool.py invoices.csv

The CSV needs an `amount_cents` column.
"""

_SS_README_2 = (
    _SS_README_1
    + """
## Reports

Run `make report` to write the monthly summary to `report.txt`.
"""
)


def _single_script() -> list[Commit]:
    return [
        (
            "Add invoice summary script",
            {"tool.py": _file(_TOOL_PY, True), "README.md": _file(_SS_README_1)},
        ),
        (
            "Add upload settings",
            {
                "config.ini": _file(
                    f"[upload]\nhost = files.example.invalid\ntoken = {fake_token()}\n"
                )
            },
        ),
        ("Document the report command", {"README.md": _file(_SS_README_2)}),
        ("Keep a copy of the previous script", {"tool.orig.py": _file(_TOOL_PY, True)}),
    ]


# -------------------------------------------------------------------- docs-only

_DOCS_README = """\
# Team handbook

How the team works: onboarding, setup and the review process.

- [Guide](docs/guide.md)
- [Setup](docs/setup.md)
- [Contributing](CONTRIBUTING.md)

## Exports

Run `./bin/export --all` to build the handbook as one PDF.
"""

_DOCS_GUIDE = """\
# Guide

## Onboarding

1. Request access to the shared drive.
2. Read the setup page.
3. Pair with a teammate on a first change.

## Reviews

Every change gets one review. Reviews happen within two working days.
"""

_DOCS_SETUP = """\
# Setup

1. Install the editor of your choice.
2. Clone the handbook.
3. Open `docs/guide.md` and follow the onboarding steps.

Uploads go to the shared drive with the token in `config/settings.yaml`.
"""

_DOCS_CONTRIBUTING = """\
# Contributing

Open a pull request. Keep a page to one topic. Link new pages from the README.
"""


def _docs_only() -> list[Commit]:
    return [
        (
            "Add handbook pages",
            {
                "README.md": _file(_DOCS_README.split("## Exports")[0].rstrip() + "\n"),
                "docs/guide.md": _file(_DOCS_GUIDE),
                "CONTRIBUTING.md": _file(_DOCS_CONTRIBUTING),
            },
        ),
        ("Add setup page", {"docs/setup.md": _file(_DOCS_SETUP)}),
        (
            "Add settings",
            {
                "config/settings.yaml": _file(
                    f"upload_host: files.example.invalid\nupload_token: {fake_token()}\n"
                ),
                "config/limits.yaml": _file(
                    "# Partner API quota, per minute. Valid until the date below.\n"
                    "quota_per_minute: 100\n"
                    'quota_valid_until: "2019-12-31"\n'
                ),
            },
        ),
        (
            "Document the export command and keep the old setup page",
            {"README.md": _file(_DOCS_README), "docs/setup-old.md": _file(_DOCS_SETUP)},
        ),
    ]


# -------------------------------------------------------------------- workspace

_PACKAGES = ["core", "utils", "cli"]
_MODULES_PER_PACKAGE = 36

_FORMAT_JS = """\
export function formatAmount(cents) {
  const sign = cents < 0 ? "-" : "";
  const abs = Math.abs(cents);
  const units = Math.floor(abs / 100);
  const rest = String(abs % 100).padStart(2, "0");
  return `${sign}${units}.${rest}`;
}
"""

_WS_README_1 = """\
# ledger-tools

A pnpm workspace with three packages: `core`, `utils` and `cli`.

## Development

    pnpm install
    pnpm -r test
"""

_WS_README_2 = (
    _WS_README_1
    + """
## Reports

Run `pnpm run report` to build the monthly report.
"""
)


def _module(pkg: str, n: int) -> str:
    lines = [f"// {pkg} module {n:02d}"]
    for k in range(4):
        name = f"{pkg}{n:02d}_{k}"
        lines += [
            f"export function {name}(a, b) {{",
            f"  const x = a * {n + k + 1} + b;",
            f"  if (x % {k + 2} === 0) {{",
            f"    return x / {k + 2};",
            "  }",
            f"  return x - {n + 1};",
            "}",
            "",
        ]
    return "\n".join(lines)


def _workspace() -> list[Commit]:
    skeleton: dict[str, File] = {
        "pnpm-workspace.yaml": _file("packages:\n  - packages/*\n"),
        "package.json": _file(
            '{\n  "name": "ledger-tools",\n  "private": true,\n'
            '  "scripts": {\n    "test": "node --test"\n  }\n}\n'
        ),
        "README.md": _file(_WS_README_1),
    }
    modules: dict[str, File] = {}
    for pkg in _PACKAGES:
        skeleton[f"packages/{pkg}/package.json"] = _file(
            f'{{\n  "name": "@ledger/{pkg}",\n  "version": "0.1.0",\n'
            f'  "type": "module",\n  "main": "src/index.js"\n}}\n'
        )
        names = [f"m{n:02d}" for n in range(_MODULES_PER_PACKAGE)]
        skeleton[f"packages/{pkg}/src/index.js"] = _file(
            "".join(f'export * from "./{name}.js";\n' for name in names)
        )
        for n, name in enumerate(names):
            modules[f"packages/{pkg}/src/{name}.js"] = _file(_module(pkg, n))
    return [
        ("Create the workspace and its packages", skeleton),
        ("Add the package modules", modules),
        (
            "Add settings and rates",
            {
                "packages/core/src/config.js": _file(
                    f'export const UPLOAD_TOKEN = "{fake_token()}";\n'
                    'export const UPLOAD_HOST = "files.example.invalid";\n'
                ),
                "packages/utils/src/rates.js": _file(
                    "// Tax rate table for the filing period. Valid until the date below.\n"
                    'export const RATES_VALID_UNTIL = "2019-12-31";\n'
                    "export const RATE_PERCENT = 6.25;\n"
                ),
            },
        ),
        (
            "Share the amount formatter and document the report command",
            {
                "packages/utils/src/format.js": _file(_FORMAT_JS),
                "packages/cli/src/format.js": _file(_FORMAT_JS),
                "README.md": _file(_WS_README_2),
            },
        ),
    ]


# ------------------------------------------------------------------- static-site

_INDEX_HTML = """\
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Fernwood Bakery</title>
    <link rel="stylesheet" href="styles.css" />
  </head>
  <body>
    <header>
      <h1>Fernwood Bakery</h1>
      <nav><a href="index.html">Home</a> <a href="about.html">About</a></nav>
    </header>
    <main>
      <section class="hero">
        <h2>Fresh bread every morning</h2>
        <p>Baked from 5 a.m. Come early for the sourdough.</p>
      </section>
      <p class="note">Closed on public holidays.</p>
      <p>Prices: <span id="price"></span></p>
    </main>
    <script src="js/pricing.js"></script>
  </body>
</html>
"""

_ABOUT_HTML = """\
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>About - Fernwood Bakery</title>
    <link rel="stylesheet" href="styles.css" />
  </head>
  <body>
    <header>
      <h1>About</h1>
      <nav><a href="index.html">Home</a> <a href="about.html">About</a></nav>
    </header>
    <main>
      <p>A family bakery since 1987.</p>
    </main>
  </body>
</html>
"""

_STYLES_CSS = """\
:root {
  --bg: #ffffff;
  --fg: #1a1a1a;
}

body {
  margin: 0;
  font: 16px/1.5 system-ui, sans-serif;
  color: var(--fg);
  background: var(--bg);
}

header,
main {
  padding: 1rem;
}

nav a {
  margin-right: 1rem;
}

.hero {
  width: 480px;
  padding: 1rem;
  border: 1px solid #cccccc;
}

.note {
  color: #b5b5b5;
  background: #ffffff;
}
"""

_PRICING_JS = """\
// Price list. Valid until the date below.
const RATES_VALID_UNTIL = "2019-12-31";
const LOAF_PRICE = 4.5;

document.getElementById("price").textContent = `Loaf $${LOAF_PRICE.toFixed(2)}`;
"""

_SITE_README_1 = """\
# fernwood-bakery

The static site for Fernwood Bakery. Open `index.html` in a browser.
"""

_SITE_README_2 = (
    _SITE_README_1
    + """
## Build

Run `npm run build` to produce the minified site in `dist/`.
"""
)


def _static_site() -> list[Commit]:
    return [
        (
            "Add the home page and styles",
            {
                "index.html": _file(_INDEX_HTML),
                "styles.css": _file(_STYLES_CSS),
                "README.md": _file(_SITE_README_1),
            },
        ),
        ("Add the price list", {"js/pricing.js": _file(_PRICING_JS)}),
        (
            "Add site settings",
            {
                "js/config.js": _file(
                    "window.SITE_CONFIG = {\n"
                    '  uploadHost: "files.example.invalid",\n'
                    f'  uploadToken: "{fake_token()}",\n'
                    "};\n"
                )
            },
        ),
        (
            "Add the about page, keep the old copy and document the build",
            {
                "about.html": _file(_ABOUT_HTML),
                "about-old.html": _file(_ABOUT_HTML),
                "README.md": _file(_SITE_README_2),
            },
        ),
    ]


# ----------------------------------------------------------------- unknown-type
# A Verilog design with a testbench. No entry in types.md matches: there is no
# manifest, executable, server, infra or UI signal, and it has tracked source,
# so it is not a docs, config or data repo.

_ALU_V = """\
module alu (
    input  wire [7:0] a,
    input  wire [7:0] b,
    input  wire [1:0] op,
    output reg  [7:0] y
);
    always @(*) begin
        case (op)
            2'b00: y = a + b;
            2'b01: y = a - b;
            2'b10: y = a & b;
            default: y = a | b;
        endcase
    end
endmodule
"""

_COUNTER_V = """\
module counter (
    input  wire       clk,
    input  wire       rst,
    output reg  [7:0] count
);
    always @(posedge clk) begin
        if (rst) count <= 8'd0;
        else     count <= count + 8'd1;
    end
endmodule
"""

_PARAMS_VH = """\
// Clock calibration. The vendor approved this value until the date below.
`define CLOCK_MHZ 48
`define CALIBRATION_VALID_UNTIL "2019-12-31"
"""

_ALU_TB_V = """\
module alu_tb;
    reg  [7:0] a, b;
    reg  [1:0] op;
    wire [7:0] y;
    alu dut (.a(a), .b(b), .op(op), .y(y));
    initial begin
        a = 8'd3; b = 8'd4; op = 2'b00;
        #1 if (y !== 8'd7) $display("FAIL add");
        op = 2'b01;
        #1 if (y !== 8'hFF) $display("FAIL sub");
        $finish;
    end
endmodule
"""

_RTL_MAKEFILE = """\
SRC = rtl/alu.v rtl/counter.v

sim: $(SRC) tb/alu_tb.v
\tiverilog -o sim.out -I rtl $(SRC) tb/alu_tb.v
\tvvp sim.out

clean:
\trm -f sim.out
"""

_RTL_README_1 = """\
# tiny-alu

An 8-bit ALU and a counter in Verilog, with a testbench.

## Simulate

    make sim
"""

_RTL_README_2 = (
    _RTL_README_1
    + """
## Synthesis

Run `make synth` to synthesise the design for the target board.
"""
)


def _unknown_type() -> list[Commit]:
    return [
        (
            "Add the ALU and its testbench",
            {
                "rtl/alu.v": _file(_ALU_V),
                "tb/alu_tb.v": _file(_ALU_TB_V),
                "Makefile": _file(_RTL_MAKEFILE),
                "README.md": _file(_RTL_README_1),
            },
        ),
        ("Add the counter", {"rtl/counter.v": _file(_COUNTER_V)}),
        (
            "Add clock parameters and flash settings",
            {
                "rtl/params.vh": _file(_PARAMS_VH),
                "flash.cfg": _file(
                    f"[flash]\nhost = files.example.invalid\nupload_token = {fake_token()}\n"
                ),
            },
        ),
        (
            "Document synthesis and keep the previous ALU",
            {"rtl/alu_old.v": _file(_ALU_V), "README.md": _file(_RTL_README_2)},
        ),
    ]


_BUILDERS = {
    "single-script": _single_script,
    "docs-only": _docs_only,
    "workspace": _workspace,
    "static-site": _static_site,
    "unknown-type": _unknown_type,
}


# ---------------------------------------------------------------------- git
# Commits are written with `git fast-import`, which takes author, committer and
# time from the stream. That keeps the SHAs fixed and needs three git processes
# per fixture instead of two per commit.


def _git_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_CONFIG_SYSTEM=os.devnull,
        GIT_CONFIG_NOSYSTEM="1",
    )
    return env


def _git(repo: Path, *args: str, stdin: bytes | None = None) -> None:
    cmd = ["git", "-c", "core.autocrlf=false", "-C", str(repo), *args]
    proc = subprocess.run(
        cmd, check=False, env=_git_env(), input=stdin, capture_output=True
    )
    if proc.returncode != 0:
        raise FixtureError(
            f"git {' '.join(args)} failed in {repo}: {proc.stderr.decode().strip()}"
        )


def _stream(commits: list[Commit]) -> bytes:
    out = bytearray()

    def data(raw: bytes) -> None:
        out.extend(b"data %d\n" % len(raw) + raw + b"\n")

    who = b"Fixture <fixture@example.invalid>"
    for minute, (message, files) in enumerate(commits):
        stamp = b"%d +0000" % (_BASE_EPOCH + 60 * minute)
        out.extend(b"commit refs/heads/main\n")
        out.extend(b"author " + who + b" " + stamp + b"\n")
        out.extend(b"committer " + who + b" " + stamp + b"\n")
        data(message.encode())
        for rel in sorted(files):
            text, exe = files[rel]
            mode = b"100755" if exe else b"100644"
            out.extend(b"M " + mode + b" inline " + rel.encode() + b"\n")
            data(text.encode())
    return bytes(out)


def _build(repo: Path, commits: list[Commit]) -> None:
    repo.mkdir(parents=True)
    _git(repo, "init", "-q", "--template=", "-b", "main")
    _git(repo, "fast-import", "--quiet", stdin=_stream(commits))
    _git(repo, "reset", "-q", "--hard")


def _prepare_outdir(outdir: Path) -> None:
    if (outdir / ".git").exists():
        raise FixtureError(
            f"{outdir} is a git repo; refusing to write fixtures into it"
        )
    if outdir.exists():
        if not outdir.is_dir():
            raise FixtureError(f"{outdir} is not a directory")
        if any(outdir.iterdir()) and not (outdir / MARKER).exists():
            raise FixtureError(
                f"{outdir} is not empty and has no {MARKER} marker; refusing to delete anything in it"
            )
    else:
        outdir.mkdir(parents=True)
    (outdir / MARKER).write_text("created by fixtures.py\n", encoding="utf-8")


def generate(outdir, only: list[str] | None = None) -> dict[str, Path]:
    """Create the fixtures under outdir, replacing any earlier copy.

    Returns the fixture name to repo path. Refuses a non-empty outdir that this
    generator did not create (no marker file).
    """
    outdir = Path(outdir)
    names = list(only) if only else list(FIXTURES)
    unknown = [n for n in names if n not in _BUILDERS]
    if unknown:
        raise FixtureError(f"unknown fixture(s): {', '.join(unknown)}")
    _prepare_outdir(outdir)

    def make(name: str) -> Path:
        repo = outdir / name
        if repo.exists():
            shutil.rmtree(repo)
        _build(repo, _BUILDERS[name]())
        return repo

    # Each fixture is its own repo, so they build in parallel (git spawns dominate).
    with ThreadPoolExecutor(max_workers=len(names)) as pool:
        return dict(zip(names, pool.map(make, names)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    parser.add_argument("outdir")
    parser.add_argument("--only", help="comma-separated fixture names")
    args = parser.parse_args(argv)
    only = [n for n in args.only.split(",") if n] if args.only else None
    try:
        made = generate(args.outdir, only)
    except FixtureError as err:
        print(f"error: {err}", file=sys.stderr)
        return 2
    for name, path in made.items():
        print(f"{name}\t{path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
