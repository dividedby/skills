"""Tests for the proposal-loop harness CLI.

The publish seam is the #117/#211 drift surface — the same invalid-JSON bug,
hand-fixed twice. These tests pin the parse-and-file behavior so a future harness
edit cannot silently regress it: a missing/garbled ``<output>`` must fail loudly,
a multi-line ``<body>`` must survive the JSONL round-trip intact, and a blocked
parse must NEVER shell out to ``gh``. ``gh`` and the env are mocked; we test the
logic, not the network.
"""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import cli  # noqa: E402  (after sys.path bootstrap)


def _run(argv):
    out = io.StringIO()
    with redirect_stdout(out):
        code = cli.main(argv, out=out)
    return code, out.getvalue()


class ExtractBlockTest(unittest.TestCase):
    def test_returns_inner_text(self):
        self.assertEqual(cli.extract_block("a<body>\nhi\n</body>b", "body"), "hi")

    def test_returns_none_when_absent(self):
        self.assertIsNone(cli.extract_block("nothing here", "output"))

    def test_takes_the_last_block(self):
        text = "<output>first</output> ... <output>second</output>"
        self.assertEqual(cli.extract_block(text, "output"), "second")

    def test_preserves_multiline_body(self):
        body = "Line one\n\n```py\ncode()\n```\nLine two"
        self.assertEqual(cli.extract_block(f"<body>\n{body}\n</body>", "body"), body)

    def test_design_tension_section_survives_round_trip(self):
        """A <body-1> block with a Design-tension markdown section (headings,
        blank lines, multiple paragraphs) must survive extract_block verbatim.
        Guards against future parse tightening that strips heading-containing bodies."""
        body = (
            "deepening: widen the publish-seam parser\n\n"
            "The current parser handles only `<body-N>` tags; nested structures\n"
            "are silently dropped.\n\n"
            "### Design tension\n\n"
            "**Single-pass extraction vs. robustness to nested markup.**\n"
            "Under single-pass extraction the parser stays minimal and fast but\n"
            "rejects bodies that contain tag-like strings; any markdown heading\n"
            "that resembles an XML tag would be silently stripped.\n\n"
            "**Spec-compliant XML parsing vs. stdlib portability.**\n"
            "A full XML parser handles arbitrary nesting but adds a dependency\n"
            "and fails on bodies that are not well-formed XML; every unescaped\n"
            "`<` in a code fence becomes a parse error.\n\n"
            "The decision that must be resolved at triage: does the body contract\n"
            "permit heading-containing markdown, and if so, which parsing strategy\n"
            "is the right tradeoff — single-pass regex with an escaping convention,\n"
            "or a more permissive heuristic that accepts real-world agent output?"
        )
        self.assertEqual(cli.extract_block(f"<body-1>\n{body}\n</body-1>", "body-1"), body)


class ParseOutputTest(unittest.TestCase):
    def test_parses_clean_json(self):
        out = cli.parse_output('<output>{"status": "skipped", "reason": "quiet"}</output>')
        self.assertEqual(out["status"], "skipped")

    def test_strips_a_json_fence(self):
        block = '<output>\n```json\n{"status": "skipped"}\n```\n</output>'
        self.assertEqual(cli.parse_output(block)["status"], "skipped")

    def test_raises_on_missing_block(self):
        with self.assertRaises(ValueError):
            cli.parse_output("the agent forgot to emit anything")

    def test_raises_on_garbled_json(self):
        with self.assertRaises(ValueError):
            cli.parse_output('<output>{"status": "proposed",,}</output>')


class ParseDigestTest(unittest.TestCase):
    def test_takes_last_result_event_whole(self):
        lines = [
            json.dumps({"type": "assistant", "text": "thinking"}),
            json.dumps({"type": "result", "result": "stale", "total_cost_usd": 0.1}),
            json.dumps({"type": "result", "result": "line1\nline2", "total_cost_usd": 0.42,
                        "duration_ms": 1234, "num_turns": 7}),
        ]
        d = cli.parse_digest(lines)
        self.assertEqual(d["result"], "line1\nline2")
        self.assertEqual(d["total_cost_usd"], 0.42)
        self.assertEqual(d["num_turns"], 7)

    def test_skips_non_json_lines(self):
        lines = ["not json at all", json.dumps({"type": "result", "result": "ok"})]
        self.assertEqual(cli.parse_digest(lines)["result"], "ok")

    def test_no_result_event_yields_na(self):
        d = cli.parse_digest([json.dumps({"type": "assistant"})])
        self.assertEqual(d["result"], "")
        self.assertEqual(d["total_cost_usd"], "n/a")
        self.assertEqual(d["error"], "no-result")

    def test_is_error_result_event_flags_error(self):
        """A completed-but-failed run (is_error: true) carries the error class,
        even though the cost fields are real numbers, not n/a (#531 item 3)."""
        lines = [json.dumps({
            "type": "result", "result": "boom", "total_cost_usd": 0.05,
            "duration_ms": 500, "num_turns": 1, "is_error": True,
        })]
        d = cli.parse_digest(lines)
        self.assertEqual(d["error"], "is_error")
        self.assertEqual(d["total_cost_usd"], 0.05)

    def test_clean_result_event_has_no_error(self):
        lines = [json.dumps({"type": "result", "result": "ok", "total_cost_usd": 0.1})]
        self.assertIsNone(cli.parse_digest(lines)["error"])

    def test_cost_line_format(self):
        d = {"total_cost_usd": 0.42, "duration_ms": 1234, "num_turns": 7}
        self.assertEqual(cli.cost_line(d), "total_cost_usd=0.42  duration_ms=1234  num_turns=7")

    def test_cost_line_clean_run_byte_identical_with_explicit_no_error(self):
        """A digest with error=None (the normal clean-run shape) must produce the
        exact pre-#531 line — no consumer-visible format change on the happy path."""
        d = {"total_cost_usd": 0.42, "duration_ms": 1234, "num_turns": 7, "error": None}
        self.assertEqual(cli.cost_line(d), "total_cost_usd=0.42  duration_ms=1234  num_turns=7")

    def test_cost_line_prepends_error_field_when_present(self):
        d = {"total_cost_usd": "n/a", "duration_ms": "n/a", "num_turns": "n/a", "error": "no-result"}
        self.assertEqual(
            cli.cost_line(d),
            "error=no-result  total_cost_usd=n/a  duration_ms=n/a  num_turns=n/a",
        )


class DigestCommandTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.jsonl = os.path.join(self.dir, "agent.jsonl")
        self.result = os.path.join(self.dir, "agent.log")
        self.cost = os.path.join(self.dir, "agent.cost")

    def _write(self, lines):
        with open(self.jsonl, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))

    def test_writes_result_and_cost_files(self):
        self._write([
            "some npm noise on stdout",
            json.dumps({"type": "result", "result": "<output>\n{}\n</output>",
                        "total_cost_usd": 0.5, "duration_ms": 10, "num_turns": 2}),
        ])
        code, _ = _run(["digest", "--jsonl", self.jsonl,
                        "--result-out", self.result, "--cost-out", self.cost])
        self.assertEqual(code, 0)
        with open(self.result) as fh:
            self.assertIn("<output>", fh.read())
        with open(self.cost) as fh:
            self.assertEqual(fh.read().strip(), "total_cost_usd=0.5  duration_ms=10  num_turns=2")

    def test_missing_jsonl_is_best_effort(self):
        code, _ = _run(["digest", "--jsonl", os.path.join(self.dir, "nope.jsonl"),
                        "--result-out", self.result, "--cost-out", self.cost])
        self.assertEqual(code, 0)
        with open(self.cost) as fh:
            line = fh.read().strip()
        self.assertEqual(line, "error=no-result  total_cost_usd=n/a  duration_ms=n/a  num_turns=n/a")

    def test_crashed_run_no_result_event_carries_error_fingerprint(self):
        """A run with a JSONL log but no `result` event (e.g. it was killed
        mid-stream) must be distinguishable from a cheap clean run in the cost
        line the cross-repo cost hub scrapes (#531 item 3)."""
        self._write(["some npm noise on stdout", json.dumps({"type": "assistant", "text": "..."})])
        code, _ = _run(["digest", "--jsonl", self.jsonl,
                        "--result-out", self.result, "--cost-out", self.cost])
        self.assertEqual(code, 0)
        with open(self.cost) as fh:
            line = fh.read().strip()
        self.assertEqual(line, "error=no-result  total_cost_usd=n/a  duration_ms=n/a  num_turns=n/a")

    def test_clean_run_cost_line_is_byte_identical_to_pre_error_field_format(self):
        """The happy path's cost line must be unchanged by the #531 error-class
        addition — COST_SURFACE's parser is unaffected on a normal run."""
        self._write([
            json.dumps({"type": "result", "result": "<output>\n{}\n</output>",
                        "total_cost_usd": 0.5, "duration_ms": 10, "num_turns": 2}),
        ])
        code, _ = _run(["digest", "--jsonl", self.jsonl,
                        "--result-out", self.result, "--cost-out", self.cost])
        self.assertEqual(code, 0)
        with open(self.cost) as fh:
            self.assertEqual(fh.read().strip(), "total_cost_usd=0.5  duration_ms=10  num_turns=2")


class PublishCommandTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.log = os.path.join(self.dir, "agent.log")
        self.summary = os.path.join(self.dir, "summary.md")
        self.output = os.path.join(self.dir, "gh_output")

    def _log(self, text):
        with open(self.log, "w", encoding="utf-8") as fh:
            fh.write(text)

    def _publish(self, extra=None):
        argv = ["publish", "--log", self.log, "--label", "source:architecture-review",
                "--heading", "Architecture review", "--summary-file", self.summary,
                "--output-file", self.output, "--repo", "owner/name"]
        return _run(argv + (extra or []))

    def test_proposed_creates_one_labeled_issue(self):
        self._log(
            '<output>\n{"status": "proposed", "title": "deepening: x",'
            ' "oneLineSummary": "do x", "candidatesConsidered": ["x", "y"]}\n</output>\n'
            "<body>\nFull body with `code` and \"quotes\".\n</body>\n"
        )
        with mock.patch("cli.subprocess.run") as run:
            run.side_effect = [
                SimpleNamespace(returncode=0),  # label create
                SimpleNamespace(returncode=0, stdout="https://x/issues/1\n"),  # issue create
            ]
            code, out = self._publish()
        self.assertEqual(code, 0)
        create = run.call_args_list[-1].args[0]
        self.assertEqual(create[:3], ["gh", "issue", "create"])
        self.assertIn("source:architecture-review", create)
        self.assertIn("owner/name", create)
        with open(self.output) as fh:
            gh_out = fh.read()
        self.assertIn("issue_url=https://x/issues/1", gh_out)
        self.assertIn("issue_urls=https://x/issues/1", gh_out)
        with open(self.summary) as fh:
            s = fh.read()
        self.assertIn("https://x/issues/1 — do x", s)
        self.assertIn("- x", s)

    def test_extra_labels_ensured_and_applied_at_filing(self):
        # #668: needs-triage + a category label are applied at filing time, and
        # each is ensured (gh label create) BEFORE the issue create so an unknown
        # label in the target repo can't hard-fail the filing.
        self._log(
            '<output>\n{"status": "proposed", "title": "deepening: x",'
            ' "oneLineSummary": "do x", "candidatesConsidered": ["x"]}\n</output>\n'
            "<body>\nBody.\n</body>\n"
        )
        with mock.patch("cli.subprocess.run") as run:
            run.side_effect = [
                SimpleNamespace(returncode=0),  # ensure provenance label
                SimpleNamespace(returncode=0),  # ensure needs-triage
                SimpleNamespace(returncode=0),  # ensure chore
                SimpleNamespace(returncode=0, stdout="https://x/issues/9\n"),  # issue create
            ]
            code, _ = self._publish(["--extra-label", "needs-triage", "--extra-label", "chore"])
        self.assertEqual(code, 0)
        create = run.call_args_list[-1].args[0]
        self.assertEqual(create[:3], ["gh", "issue", "create"])
        for want in ("source:architecture-review", "needs-triage", "chore"):
            self.assertIn(want, create)
        # both extra labels were ensured via `gh label create` before the create
        ensured = {c.args[0][3] for c in run.call_args_list
                   if c.args[0][:3] == ["gh", "label", "create"]}
        self.assertTrue({"needs-triage", "chore"} <= ensured)

    def test_proposed_body_round_trips_unescaped(self):
        """The whole point of the <body> split: raw markdown reaches gh verbatim."""
        body = 'Has "quotes", a newline,\nand ```fences```.'
        self._log(
            '<output>\n{"status": "proposed", "title": "t",'
            ' "oneLineSummary": "s", "candidatesConsidered": ["c"]}\n</output>\n'
            f"<body>\n{body}\n</body>\n"
        )
        captured = {}

        def fake_run(cmd, **kw):
            if cmd[:3] == ["gh", "issue", "create"]:
                path = cmd[cmd.index("--body-file") + 1]
                with open(path, encoding="utf-8") as fh:
                    captured["body"] = fh.read()
                return SimpleNamespace(returncode=0, stdout="url\n")
            return SimpleNamespace(returncode=0)

        with mock.patch("cli.subprocess.run", side_effect=fake_run):
            code, _ = self._publish()
        self.assertEqual(code, 0)
        self.assertEqual(captured["body"], body)

    def test_staleness_report_with_table_pipes_round_trips(self):
        """A staleness-review body — code fences, unescaped quotes, AND a markdown
        table whose cells are delimited by `|` pipes — must reach gh verbatim. The
        pipes are the staleness-specific hazard: they'd be a JSON-escaping nightmare
        inside the <output> string, which is exactly why the body rides the raw
        <body> seam instead (see harness/prompts/staleness-audit.md)."""
        body = (
            "Scanned the Node toolchain pins in this repo.\n\n"
            "| target | file | current | latest | gap | action |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            '| node | `.nvmrc` | "18" | unverified | unverified | bump to "latest" |\n'
            "| node | `package.json` | >=18 | unverified | unverified | review |\n\n"
            "```sh\nnode --version\n```\n\n"
            "Every `action` is a recommendation — no apply path on this loop."
        )
        self._log(
            '<output>\n{"status": "proposed", "title": "staleness-review: Node pins",'
            ' "oneLineSummary": "2 findings", "candidatesConsidered": ["nvmrc", "engines"]}\n</output>\n'
            f"<body>\n{body}\n</body>\n"
        )
        captured = {}

        def fake_run(cmd, **kw):
            if cmd[:3] == ["gh", "issue", "create"]:
                path = cmd[cmd.index("--body-file") + 1]
                with open(path, encoding="utf-8") as fh:
                    captured["body"] = fh.read()
                return SimpleNamespace(returncode=0, stdout="https://x/issues/9\n")
            return SimpleNamespace(returncode=0)

        with mock.patch("cli.subprocess.run", side_effect=fake_run):
            code, _ = self._publish(["--label", "source:staleness-review"])
        self.assertEqual(code, 0)
        self.assertEqual(captured["body"], body)
        self.assertIn("| target | file |", captured["body"])

    def _multi_log(self, n):
        proposals = [
            {"title": f"deepening: p{i}", "oneLineSummary": f"summary {i}"}
            for i in range(1, n + 1)
        ]
        bodies = "\n".join(f"<body-{i}>\nBody {i} text.\n</body-{i}>" for i in range(1, n + 1))
        self._log(
            "<output>\n"
            + json.dumps(
                {"status": "proposed", "proposals": proposals, "candidatesConsidered": ["c"]}
            )
            + "\n</output>\n"
            + bodies
            + "\n"
        )

    def _fake_gh(self, captured):
        def fake_run(cmd, **kw):
            if cmd[:3] == ["gh", "issue", "create"]:
                path = cmd[cmd.index("--body-file") + 1]
                with open(path, encoding="utf-8") as fh:
                    captured.append({"title": cmd[cmd.index("--title") + 1], "body": fh.read()})
                return SimpleNamespace(returncode=0, stdout=f"https://x/issues/{len(captured)}\n")
            return SimpleNamespace(returncode=0)

        return fake_run

    def test_multi_proposal_files_each_with_matching_body(self):
        # Regression coverage for title/body pairing across N>1 proposals is
        # independent of the per-run cap value; raise it locally so this test
        # keeps exercising multi-proposal filing even though MAX_PROPOSALS=1.
        self._multi_log(2)
        captured = []
        with mock.patch.object(cli, "MAX_PROPOSALS", 2), mock.patch(
            "cli.subprocess.run", side_effect=self._fake_gh(captured)
        ):
            code, out = self._publish()
        self.assertEqual(code, 0)
        self.assertEqual(len(captured), 2)
        self.assertEqual(captured[1]["title"], "deepening: p2")
        self.assertEqual(captured[1]["body"], "Body 2 text.")
        with open(self.output) as fh:
            gh_out = fh.read()
        self.assertIn("issue_url=https://x/issues/1", gh_out)
        self.assertIn(
            "issue_urls=https://x/issues/1,https://x/issues/2", gh_out
        )
        with open(self.summary) as fh:
            s = fh.read()
        self.assertIn("**Created (2):**", s)
        self.assertIn("https://x/issues/2 — summary 2", s)

    def test_more_than_cap_truncates_to_max(self):
        self._multi_log(7)
        captured = []
        with mock.patch("cli.subprocess.run", side_effect=self._fake_gh(captured)):
            code, out = self._publish()
        self.assertEqual(code, 0)
        self.assertEqual(len(captured), cli.MAX_PROPOSALS)
        self.assertIn("WARNING: 7 proposals emitted", out)
        with open(self.summary) as fh:
            self.assertIn("**Truncated:**", fh.read())

    def test_multi_proposal_missing_body_block_fails_loudly(self):
        self._log(
            "<output>\n"
            + json.dumps(
                {
                    "status": "proposed",
                    "proposals": [
                        {"title": "p1", "oneLineSummary": "s1"},
                        {"title": "p2", "oneLineSummary": "s2"},
                    ],
                    "candidatesConsidered": ["c"],
                }
            )
            + "\n</output>\n<body-1>\nonly one body\n</body-1>\n"
        )
        with mock.patch("cli.subprocess.run") as run:
            code, _ = self._publish()
        self.assertEqual(code, 1)
        run.assert_not_called()

    def test_empty_proposals_array_fails_loudly(self):
        self._log('<output>\n{"status": "proposed", "proposals": []}\n</output>\n')
        with mock.patch("cli.subprocess.run") as run:
            code, _ = self._publish()
        self.assertEqual(code, 1)
        run.assert_not_called()

    def test_skipped_files_nothing_and_summarises(self):
        self._log('<output>\n{"status": "skipped", "reason": "all quiet"}\n</output>\n')
        with mock.patch("cli.subprocess.run") as run:
            code, out = self._publish()
        self.assertEqual(code, 0)
        run.assert_not_called()
        self.assertIn("SKIPPED: all quiet", out)
        with open(self.summary) as fh:
            self.assertIn("Skipped", fh.read())

    def test_missing_output_block_fails_loudly(self):
        self._log("the agent crashed and emitted only prose")
        with mock.patch("cli.subprocess.run") as run:
            code, _ = self._publish()
        self.assertEqual(code, 1)
        run.assert_not_called()
        self.assertFalse(os.path.exists(self.summary))

    def test_garbled_json_fails_loudly(self):
        # Double-comma (,,) is NOT fully repaired in one pass, and there are no
        # <body-N> blocks to salvage — asserts the fail-loud floor.
        self._log('<output>\n{"status": "proposed",,}\n</output>\n')
        with mock.patch("cli.subprocess.run") as run:
            code, _ = self._publish()
        self.assertEqual(code, 1)
        run.assert_not_called()

    def test_repairs_trailing_comma_with_warning(self):
        """Single trailing comma is repaired; a ::warning:: goes to stderr."""
        self._log('<output>{"status":"skipped","reason":"x",}</output>')
        with mock.patch("cli.subprocess.run"):
            with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
                code, out = self._publish()
        self.assertEqual(code, 0)
        self.assertIn("SKIPPED: x", out)
        self.assertIn("::warning::", err.getvalue())
        self.assertIn("deterministic repair", err.getvalue())

    def test_repairs_real_delimiter_failure(self):
        """A raw newline inside a JSON string (produces Expecting ',' delimiter) is repaired."""
        # Build JSON with a raw embedded newline in the reason field.
        raw = '{"status":"skipped","reason":"line one\nline two"}'
        self._log(f"<output>{raw}</output>")
        with mock.patch("cli.subprocess.run"):
            with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
                code, out = self._publish()
        self.assertEqual(code, 0)
        self.assertIn("::warning::", err.getvalue())

    def test_valid_unusual_json_untouched(self):
        """A VALID <output> whose string value contains ', }' and an escaped newline
        round-trips unchanged — the repair must never corrupt valid JSON."""
        payload = {"status": "skipped", "reason": "foo, } and \\n bar"}
        raw_json = json.dumps(payload)
        self._log(f"<output>{raw_json}</output>")
        with mock.patch("cli.subprocess.run"):
            with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
                code, out = self._publish()
        # Must parse cleanly with no repair warning.
        self.assertEqual(code, 0)
        self.assertEqual(err.getvalue(), "")
        self.assertIn("SKIPPED: foo, } and", out)

    def test_irreparable_output_salvages_bodies(self):
        """Genuine garbage <output> + present <body-N> blocks → exit 0, 2 issues filed."""
        # Salvage-path multi-body handling is independent of the per-run cap
        # value; raise it locally so this regression guard still exercises
        # >1 salvaged proposal even though MAX_PROPOSALS=1.
        self._log(
            "<output>not json {[</output>\n"
            "<body-1>\n# First proposal\nBody one.\n</body-1>\n"
            "<body-2>\n# Second proposal\nBody two.\n</body-2>\n"
        )
        captured = []
        with mock.patch.object(cli, "MAX_PROPOSALS", 2), mock.patch(
            "cli.subprocess.run", side_effect=self._fake_gh(captured)
        ):
            with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
                code, out = self._publish()
        self.assertEqual(code, 0)
        self.assertEqual(len(captured), 2)
        self.assertTrue(captured[0]["title"].startswith("recovered: "))
        self.assertTrue(captured[1]["title"].startswith("recovered: "))
        self.assertIn("salvaged", err.getvalue())
        self.assertIn("::warning::", err.getvalue())

    def test_no_output_and_no_bodies_still_fails_loudly(self):
        """Garbage <output> + zero <body-N> blocks → exit 1, no issue filed."""
        self._log("<output>not json {[</output>\n")
        with mock.patch("cli.subprocess.run") as run:
            code, _ = self._publish()
        self.assertEqual(code, 1)
        run.assert_not_called()

    def test_unknown_status_fails_loudly(self):
        self._log('<output>\n{"status": "maybe"}\n</output>\n')
        with mock.patch("cli.subprocess.run") as run:
            code, _ = self._publish()
        self.assertEqual(code, 1)
        run.assert_not_called()

    def test_proposed_without_body_fails_loudly(self):
        self._log(
            '<output>\n{"status": "proposed", "title": "t",'
            ' "oneLineSummary": "s", "candidatesConsidered": ["c"]}\n</output>\n'
        )
        with mock.patch("cli.subprocess.run") as run:
            code, _ = self._publish()
        self.assertEqual(code, 1)
        run.assert_not_called()

    def _publish_dedup(self, extra=None):
        """Like _publish but passes --dedup-open."""
        argv = ["publish", "--log", self.log, "--label", "source:changelog-health",
                "--heading", "Changelog health", "--summary-file", self.summary,
                "--output-file", self.output, "--repo", "owner/name", "--dedup-open"]
        return _run(argv + (extra or []))

    def test_dedup_open_skips_when_advisory_exists(self):
        """--dedup-open + open advisory → no issue create, exit 0, summary says 'already open'."""
        self._log('<output>\n{"status": "proposed", "title": "t", "oneLineSummary": "s"}\n</output>\n'
                  "<body>\nbody text\n</body>\n")
        calls = []

        def fake_run(cmd, **kw):
            calls.append(cmd)
            if cmd[:3] == ["gh", "issue", "list"]:
                return SimpleNamespace(returncode=0, stdout='[{"url":"https://github.com/owner/name/issues/1"}]')
            return SimpleNamespace(returncode=0, stdout="")

        with mock.patch("cli.subprocess.run", side_effect=fake_run):
            code, out = self._publish_dedup()

        self.assertEqual(code, 0)
        self.assertIn("SKIPPED", out)
        self.assertIn("already open", out)
        # No issue create call
        create_calls = [c for c in calls if c[:3] == ["gh", "issue", "create"]]
        self.assertEqual(create_calls, [])
        with open(self.summary) as fh:
            self.assertIn("already open", fh.read())

    def test_dedup_open_proceeds_when_none_open(self):
        """--dedup-open + no open advisory → label ensure + issue create proceed normally."""
        self._log('<output>\n{"status": "proposed", "title": "t", "oneLineSummary": "s"}\n</output>\n'
                  "<body>\nbody text\n</body>\n")

        def fake_run(cmd, **kw):
            if cmd[:3] == ["gh", "issue", "list"]:
                return SimpleNamespace(returncode=0, stdout="[]")
            if cmd[:3] == ["gh", "issue", "create"]:
                return SimpleNamespace(returncode=0, stdout="https://github.com/owner/name/issues/2\n")
            return SimpleNamespace(returncode=0, stdout="")

        with mock.patch("cli.subprocess.run", side_effect=fake_run):
            code, out = self._publish_dedup()

        self.assertEqual(code, 0)
        self.assertIn("Published", out)

    def test_no_dedup_open_flag_skips_list_call(self):
        """Without --dedup-open, gh issue list is never called (regression guard)."""
        self._log('<output>\n{"status": "skipped", "reason": "all quiet"}\n</output>\n')
        calls = []

        def fake_run(cmd, **kw):
            calls.append(cmd)
            return SimpleNamespace(returncode=0, stdout="")

        with mock.patch("cli.subprocess.run", side_effect=fake_run):
            code, out = self._publish()

        self.assertEqual(code, 0)
        list_calls = [c for c in calls if c[:3] == ["gh", "issue", "list"]]
        self.assertEqual(list_calls, [])

    def test_gh_failure_during_create_issue_exits_cleanly(self):
        """A gh CalledProcessError (auth expiry, rate limit, …) during issue
        filing must route through the ``::error::`` exit path, not an uncaught
        traceback (#525)."""
        self._log(
            '<output>\n{"status": "proposed", "title": "t",'
            ' "oneLineSummary": "s", "candidatesConsidered": ["c"]}\n</output>\n'
            "<body>\nbody text\n</body>\n"
        )

        def fake_run(cmd, **kw):
            if cmd[:3] == ["gh", "issue", "create"]:
                raise cli.subprocess.CalledProcessError(
                    1, cmd, output="", stderr="HTTP 401: Bad credentials"
                )
            return SimpleNamespace(returncode=0)

        with mock.patch("cli.subprocess.run", side_effect=fake_run):
            with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
                code, out = self._publish()
        self.assertEqual(code, 1)
        self.assertIn("::error::", err.getvalue())
        self.assertIn("Bad credentials", err.getvalue())

    def test_gh_failure_during_dedup_lookup_exits_cleanly(self):
        """Same, but for the --dedup-open `gh issue list` call (_find_open)."""
        self._log(
            '<output>\n{"status": "proposed", "title": "t", "oneLineSummary": "s"}\n</output>\n'
            "<body>\nbody text\n</body>\n"
        )

        def fake_run(cmd, **kw):
            if cmd[:3] == ["gh", "issue", "list"]:
                raise cli.subprocess.CalledProcessError(1, cmd, output="", stderr="rate limited")
            return SimpleNamespace(returncode=0)

        with mock.patch("cli.subprocess.run", side_effect=fake_run):
            with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
                code, out = self._publish_dedup()
        self.assertEqual(code, 1)
        self.assertIn("::error::", err.getvalue())
        self.assertIn("rate limited", err.getvalue())


class CountUntriagedTest(unittest.TestCase):
    def test_builds_expected_gh_command(self):
        with mock.patch("cli.subprocess.run") as run:
            run.return_value = SimpleNamespace(returncode=0, stdout="[]")
            cli._count_untriaged("source:agent-research", "owner/name", 3)
        cmd = run.call_args.args[0]
        self.assertEqual(cmd[:3], ["gh", "issue", "list"])
        self.assertEqual(cmd.count("--label"), 2)
        self.assertIn("source:agent-research", cmd)
        self.assertIn("needs-triage", cmd)
        self.assertIn("--state", cmd)
        self.assertIn("open", cmd)
        self.assertIn("--limit", cmd)
        self.assertIn("3", cmd)
        self.assertIn("--json", cmd)
        self.assertIn("number", cmd)
        self.assertIn("--repo", cmd)
        self.assertIn("owner/name", cmd)

    def test_counts_returned_items(self):
        with mock.patch("cli.subprocess.run") as run:
            run.return_value = SimpleNamespace(
                returncode=0, stdout=json.dumps([{"number": 1}, {"number": 2}])
            )
            count = cli._count_untriaged("source:agent-research", "owner/name", 3)
        self.assertEqual(count, 2)


class BacklogCheckCommandTest(unittest.TestCase):
    """The backlog throttle: skip a run when the loop's own provenance-labeled
    backlog is already >= BACKLOG_THRESHOLD issues still needs-triage."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.summary = os.path.join(self.dir, "summary.md")
        self.output = os.path.join(self.dir, "gh_output")

    def _check(self, extra=None):
        argv = [
            "backlog-check", "--label", "source:agent-research",
            "--heading", "Apply agent research", "--summary-file", self.summary,
            "--output-file", self.output, "--repo", "owner/name",
        ]
        return _run(argv + (extra or []))

    def test_full_backlog_skips_and_summarises(self):
        with mock.patch("cli.subprocess.run") as run:
            run.return_value = SimpleNamespace(
                returncode=0, stdout=json.dumps([{"number": 1}, {"number": 2}, {"number": 3}])
            )
            code, out = self._check()
        self.assertEqual(code, 0)
        with open(self.output) as fh:
            self.assertIn("backlog_full=true", fh.read())
        with open(self.summary) as fh:
            s = fh.read()
        self.assertIn("backlog full", s.lower())
        self.assertIn("BACKLOG FULL", out)

    def test_below_threshold_proceeds_with_no_skip_summary(self):
        """Boundary: 2 open issues is below the threshold of 3 -> proceed."""
        with mock.patch("cli.subprocess.run") as run:
            run.return_value = SimpleNamespace(
                returncode=0, stdout=json.dumps([{"number": 1}, {"number": 2}])
            )
            code, out = self._check()
        self.assertEqual(code, 0)
        with open(self.output) as fh:
            self.assertIn("backlog_full=false", fh.read())
        self.assertFalse(os.path.exists(self.summary))

    def test_gh_failure_fails_open(self):
        """A gh lookup failure must never block a run — fail open (#543)."""
        with mock.patch("cli.subprocess.run") as run:
            run.side_effect = cli.subprocess.CalledProcessError(
                1, ["gh", "issue", "list"], output="", stderr="rate limited"
            )
            with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
                code, out = self._check()
        self.assertEqual(code, 0)
        with open(self.output) as fh:
            self.assertIn("backlog_full=false", fh.read())
        self.assertIn("::warning::", err.getvalue())


class FetchRubricCommandTest(unittest.TestCase):
    """Clone-first (--source-dir, no network call, #525)."""

    def setUp(self):
        self.out_dir = tempfile.mkdtemp()
        self.source_dir = tempfile.mkdtemp()
        self.rubric_dir = os.path.join(
            self.source_dir, "skills", "engineering", "codebase-design"
        )
        os.makedirs(self.rubric_dir)

    def _write_source(self, lang=b"lang content", deepening=b"deepening content"):
        with open(os.path.join(self.rubric_dir, "SKILL.md"), "wb") as fh:
            fh.write(lang)
        with open(os.path.join(self.rubric_dir, "DEEPENING.md"), "wb") as fh:
            fh.write(deepening)

    def _run_fetch(self):
        return _run([
            "fetch-rubric", "--out-dir", self.out_dir, "--source-dir", self.source_dir,
        ])

    def test_both_files_written_on_success(self):
        self._write_source()
        code, out = self._run_fetch()
        self.assertEqual(code, 0)
        lang = os.path.join(self.out_dir, "depth-LANGUAGE.md")
        deep = os.path.join(self.out_dir, "depth-DEEPENING.md")
        with open(lang, "rb") as fh:
            self.assertEqual(fh.read(), b"lang content")
        with open(deep, "rb") as fh:
            self.assertEqual(fh.read(), b"deepening content")
        self.assertIn("Fetched depth-LANGUAGE.md", out)
        self.assertIn("Fetched depth-DEEPENING.md", out)

    def test_hard_fail_when_source_missing_entirely(self):
        # rubric_dir exists but is empty — neither source file present.
        code, out = self._run_fetch()
        self.assertEqual(code, 1)
        self.assertFalse(os.path.exists(os.path.join(self.out_dir, "depth-LANGUAGE.md")))
        self.assertFalse(os.path.exists(os.path.join(self.out_dir, "depth-DEEPENING.md")))

    def test_hard_fail_reports_actionable_path(self):
        with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
            code, out = self._run_fetch()
        self.assertEqual(code, 1)
        self.assertIn("::error::", err.getvalue())
        self.assertIn(self.rubric_dir, err.getvalue())

    def test_hard_fail_on_second_file_missing(self):
        """First file present, second absent — must still fail loud (exit 1);
        depth-LANGUAGE.md is already written by the time the second file's
        absence is discovered, so it legitimately remains on disk."""
        with open(os.path.join(self.rubric_dir, "SKILL.md"), "wb") as fh:
            fh.write(b"lang content")
        code, out = self._run_fetch()
        self.assertEqual(code, 1)
        self.assertTrue(os.path.exists(os.path.join(self.out_dir, "depth-LANGUAGE.md")))
        self.assertFalse(os.path.exists(os.path.join(self.out_dir, "depth-DEEPENING.md")))


if __name__ == "__main__":
    unittest.main()
