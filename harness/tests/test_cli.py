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

    def test_cost_line_format(self):
        d = {"total_cost_usd": 0.42, "duration_ms": 1234, "num_turns": 7}
        self.assertEqual(cli.cost_line(d), "total_cost_usd=0.42  duration_ms=1234  num_turns=7")


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
            self.assertIn("total_cost_usd=n/a", fh.read())


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
            self.assertIn("issue_url=https://x/issues/1", fh.read())
        with open(self.summary) as fh:
            s = fh.read()
        self.assertIn("**Created:** https://x/issues/1", s)
        self.assertIn("- x", s)

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
        self._log('<output>\n{"status": "proposed",,}\n</output>\n')
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


if __name__ == "__main__":
    unittest.main()
