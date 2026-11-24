"""Self-tests for scrub.py, the repo-audit publish scrub.

Standard library and git only (the eval fixtures are built with git). Secret-
shaped samples are assembled at runtime so no scanner flags this file.

Run: python3 -B skills/engineering/repo-audit/scrub.test.py
"""

from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "evals"))
import fixtures
import scrub

# A fixed context: no environment lookups, so the tests do not depend on who runs them.
CTX = scrub.Context(usernames=["zelda"], hostnames=["zelda-box"])


def categories(text: str, ctx: scrub.Context = CTX) -> dict[str, int]:
    return scrub.scan_text(text, ctx)


GH = "g" + "hp_" + "aB3dE5fG7hI9jK1lM3nO5pQ7rS9tU1vW3xY5"
PEM_HEAD = "-----BEGIN " + "RSA PRIVATE KEY-----"
PEM_FOOT = "-----END " + "RSA PRIVATE KEY-----"

CAUGHT = [
    ("mac home path", "/Users/jdoe/repos/app/x.py:12", "home-path"),
    ("linux home path", "see /home/jdoe/project/run.sh", "home-path"),
    ("windows home path", "C:\\Users\\jdoe\\Documents\\a.txt", "home-path"),
    ("windows path, JSON-escaped", "C:\\\\Users\\\\jdoe\\\\a.txt", "home-path"),
    (
        "scratchpad path",
        "/private/tmp/claude-501/-proj/abc/scratchpad/p.html",
        "scratch-path",
    ),
    ("tmp claude path", "/tmp/claude-501/x/y.json", "scratch-path"),
    ("var folders path", "/var/folders/ab/cd1234/T/tmp9", "scratch-path"),
    ("username literal", "owner: Zelda wrote it", "username"),
    ("hostname literal", "ran on zelda-box today", "hostname"),
    ("private host suffix", "ssh nas.home.arpa and printer.lan", "hostname"),
    ("private ipv4", "gateway 192.168.1.1", "ip"),
    ("public ipv4", "server 93.184.216.34 replied", "ip"),
    ("ip after user@", "ssh deploy@93.184.216.34", "ip"),
    ("ip after user@ with port", "user@93.184.216.34:22", "ip"),
    ("ip after the word node", "node 93.184.216.34 is down", "ip"),
    ("ip after the word build", "on build 93.184.216.34", "ip"),
    ("ip after a tilde", "from ~93.184.216.34", "ip"),
    ("ipv6", "addr fd00:1234:5678::9", "ip"),
    ("aws account in an arn", "arn:aws:iam::123456789012:role/deploy", "account-id"),
    ("account_id key", 'account_id: "0123456789abcdef0123456789abcdef"', "account-id"),
    ("github token", f"token {GH}", "token"),
    ("anthropic key", "key sk-ant-api03-" + "A1b2C3d4E5f6G7h8I9j0K1l2", "token"),
    ("openai-style key", "key sk-proj-" + "A1b2C3d4E5f6G7h8I9j0K1l2", "token"),
    ("slack token", "xox" + "b-1234567890-abcdefghij", "token"),
    ("gitlab token", "glp" + "at-A1b2C3d4E5f6G7h8I9j0", "token"),
    ("stripe live key", "sk_" + "live_A1b2C3d4E5f6G7h8I9j0K1", "token"),
    ("npm token", "np" + "m_" + "A1b2C3d4E5" * 3 + "F6G7h8", "token"),
    ("quoted lat value", '"lat": "41.8781"', "geo"),
    ("aws access key", "AK" + "IA" + "ABCDEFGHIJKLMNOP", "token"),
    ("google key", "AI" + "za" + "A" * 35, "token"),
    ("bearer header", "Authorization: Bearer abcdef0123456789abcdef", "token"),
    ("pem block", f"{PEM_HEAD}\nMIIEabc\n{PEM_FOOT}", "token"),
    ("email", "write to jane.doe@corp-mail.io", "email"),
    ("lat and lng keys", '"lat": 41.8781, "lng": -87.6298', "geo"),
    ("pair alone on a line", "41.8781, -87.6298", "geo"),
    ("pair alone in backticks", "Home is `41.8781, -87.6298`.", "geo"),
    ("pair in its own parentheses", "Home (41.8781, -87.6298) is near", "geo"),
    ("pair under a coords key", '"coords": [41.8781, -87.6298]', "geo"),
    ("pair under a location key", "location: 41.8781,-87.6298 and more", "geo"),
    ("pair after a pin cue", "pin at 41.8781, -87.6298 today", "geo"),
    (
        "pair after a cue, mid-sentence",
        "the office is near 51.5072, -0.1276 in London",
        "geo",
    ),
    ("cued pair ending a sentence", "the house is at 41.8781, -87.6298.", "geo"),
    ("standalone pair with a period", "41.8781, -87.6298.", "geo"),
    ("pair after a GPS label", "GPS: 41.8781, -87.6298", "geo"),
    ("ip in a url path", "https://host/93.184.216.34", "ip"),
    ("private ip after a slash", "see http://nas/192.168.1.5/x", "ip"),
    ("ip after a non-browser name and slash", "Server/93.184.216.34", "ip"),
]

KEPT = [
    ("loopback ipv4", "http://127.0.0.1:8080/ and 127.0.0.1"),
    ("unspecified ipv4", "bind 0.0.0.0"),
    ("documentation ipv4", "192.0.2.1 198.51.100.7 203.0.113.250"),
    ("loopback and documentation ipv6", "::1 and 2001:db8::1"),
    (
        "version string with a marker",
        "pinned v1.2.3.4, version 2.0.0.1, foo==3.4.5.6, bar>=1.2.3.4",
    ),
    ("version with five parts", "release 10.1.2.3.4"),
    ("time of day and mac address", "at 12:30:45 on aa:bb:cc:dd:ee:ff"),
    ("rust and c++ paths", "std::vector and Foo::bar and fe::ad"),
    (
        "noreply emails",
        "noreply@acme.io, no-reply@acme.io, 1+bot@users.noreply.github.com",
    ),
    (
        "example emails",
        "a@example.com b@example.org c@sub.example.net d@host.invalid e@x.test",
    ),
    (
        "git remote and npm pins",
        "git@github.com:org/repo.git and pkg@1.2.3 and icon@2x.png",
    ),
    ("bare tmp path", "scratch in /tmp/work and /tmp"),
    ("web route under /home", "GET /home/settings"),
    ("placeholder user path", "/Users/<name>/x and /Users/you/x and /home/user/x"),
    ("config file names", "settings.local.json and .env.local and a.corp.example.com"),
    ("version-like decimals", "ratio 1.5, 2.5 and 0.12, 0.34"),
    ("svg path", '<path d="M12.3456,45.6789 L13.0001,46.1234Z"/>'),
    ("css bezier", "transition: cubic-bezier(0.4000, 0.0000, 0.2000, 1.0000)"),
    ("css matrix", "transform: matrix(1.0000, 0.0000, 0.0000, 1.0000, 0, 0)"),
    ("pair inside a sentence", "time 12.3456, 78.9012 seconds"),
    ("cued pair with a unit", "measured at 12.3456, 78.9012 ms"),
    ("cued pair with a unit, short", "p95 at 0.1234, 0.5678 s"),
    ("cued pair, unit milliseconds", "Measured at 12.3456, 78.9012 milliseconds"),
    ("cued pair, unit msec", "at 1.2345, 2.3456 msec"),
    ("cued pair, unit bytes", "at 12.3456, 78.9012 bytes"),
    ("cued pair, unit B", "at 1.2345,2.3456 B"),
    ("cued pair, unit Greek mu s", "near 1.2345, 2.3456 μs"),
    ("cued pair, unit micro sign s", "near 1.2345, 2.3456 µs"),
    ("cued pair, unit Mbps", "at 1.2345, 2.3456 Mbps"),
    ("cued pair with a percent", "load near 12.3456, 78.9012%"),
    ("cued svg points", '<polygon points="at 10.1234,20.1234 30.1234,40.1234"/>'),
    (
        "chrome user agent",
        (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36 Edg/131.0.2903.51"
        ),
    ),
    ("private-range version after a ua token", "Firefox/10.0.0.1 Version/17.0.0.0"),
    ("json number array", "[0.1234, 0.5678]"),
    ("json array of arrays", "[[0.1234, 0.5678], [12.3456, 45.6789]]"),
    ("software and oid numbers", "Python 3.12.1.0, OID 1.3.6.1 and OpenSSL 1.1.1.9"),
    ("ci home path", "/home/runner/work/repo/repo/x.py"),
    ("short names", "root cause of the user error"),
    ("plain prose with a long hyphenated word", "sk-circle-fade-in-animation-class"),
]


class DetectionTests(unittest.TestCase):
    def test_each_category_is_caught_and_removed(self):
        for name, text, category in CAUGHT:
            with self.subTest(name):
                self.assertGreaterEqual(categories(text).get(category, 0), 1)
                cleaned, _ = scrub.scrub_text(text, CTX)
                self.assertIn(f"[redacted:{category}]", cleaned)
                self.assertEqual(categories(cleaned), {})

    def test_allowed_forms_are_left_alone(self):
        for name, text in KEPT:
            with self.subTest(name):
                self.assertEqual(categories(text), {})
                self.assertEqual(scrub.scrub_text(text, CTX)[0], text)

    def test_a_secret_is_replaced_whole_and_arn_keeps_its_shape(self):
        cleaned, _ = scrub.scrub_text(f"t={GH};arn:aws:iam::123456789012:role/x", CTX)
        self.assertEqual(
            cleaned, "t=[redacted:token];arn:aws:iam::[redacted:account-id]:role/x"
        )

    def test_data_uris_are_skipped_whole(self):
        uri = "data:image/png;base64,iVBORw0KGgo/Users/jdoe/" + "A" * 200
        page = f'<img src="{uri}"> by /Users/jdoe/x'
        cleaned, counts = scrub.scrub_text(page, CTX)
        self.assertIn(uri, cleaned)
        self.assertEqual(counts, {"home-path": 1})

    def auto_context(self, env: dict[str, str], user: str, host: str) -> scrub.Context:
        # ExitStack: a parenthesised multi-item `with` is not valid on Python 3.9.
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch("getpass.getuser", return_value=user))
            stack.enter_context(mock.patch("socket.gethostname", return_value=host))
            return scrub.auto_context(env)

    def test_environment_values_are_picked_up(self):
        env = {"HOME": "/opt/h/zed", "TMPDIR": "/opt/t/x/", "USER": "zedfoo"}
        ctx = self.auto_context(env, "zedfoo", "zed-box.example.com")
        text = "in /opt/h/zed/proj, cache /opt/t/x/c, by zedfoo on zed-box"
        cleaned, counts = scrub.scrub_text(text, ctx)
        self.assertEqual(
            counts, {"home-path": 1, "scratch-path": 1, "username": 1, "hostname": 1}
        )
        self.assertNotIn("zed", cleaned.replace("[redacted:", ""))

    def test_generic_environment_names_are_not_literals(self):
        env = {"HOME": "/root", "TMPDIR": "/tmp", "USER": "root"}
        ctx = self.auto_context(env, "root", "localhost")
        self.assertEqual((ctx.usernames, ctx.hostnames, ctx.tmp), ([], [], []))


class FileTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def write(self, name: str, text: str) -> Path:
        path = self.dir / name
        path.write_bytes(text.encode("utf-8"))
        return path

    def cli(self, *args: str) -> tuple[int, str]:
        code, out, _ = self.cli_err(*args)
        return code, out

    def cli_err(self, *args: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = scrub.main([*args, "--no-auto", "--literal", "zelda"])
        return code, out.getvalue(), err.getvalue()

    def test_rewrite_in_place_then_check_passes_and_a_second_run_changes_nothing(self):
        page = self.write("page.html", f"<p>/Users/jdoe/x {GH}</p>\r\n")
        log = self.write("run-log.md", "clean\n")
        code, _ = self.cli(str(page), str(log))
        self.assertEqual(code, 0)
        self.assertEqual(
            page.read_bytes(),
            b"<p>[redacted:home-path] [redacted:token]</p>\r\n",
        )
        before = page.read_bytes(), log.read_bytes()
        self.assertEqual(self.cli(str(page), str(log))[0], 0)
        self.assertEqual(self.cli("--check", str(page), str(log))[0], 0)
        self.assertEqual((page.read_bytes(), log.read_bytes()), before)

    def test_check_reports_without_writing_and_fails_on_any_match(self):
        page = self.write("page.html", "at /Users/jdoe/x\n")
        code, out = self.cli("--check", str(page))
        self.assertEqual(code, 1)
        self.assertEqual(page.read_text(), "at /Users/jdoe/x\n")
        self.assertIn("home-path 1", out)
        self.assertIn("check | fail", out)

    def test_the_summary_holds_counts_and_names_never_values(self):
        planted = [
            "/Users/jdoe/secretproj",
            GH,
            "jane.doe@corp-mail.io",
            "93.184.216.34",
        ]
        page = self.write("page.html", " ".join(planted))
        for flags, expected_code in (([], 0), (["--check"], 1), (["--json"], 0)):
            with self.subTest(flags):
                page.write_text(" ".join(planted))
                code, out = self.cli(*flags, str(page))
                self.assertEqual(code, expected_code)
                for value in planted:
                    self.assertNotIn(value, out)
                    self.assertNotIn(value.split("/")[-1], out)

    def test_json_summary_shape(self):
        page = self.write("page.html", "/Users/jdoe/a /Users/jdoe/b 192.168.0.4")
        _, out = self.cli("--json", str(page))
        result = json.loads(out)
        self.assertEqual(result["removed"], 3)
        self.assertEqual(result["remaining"], 0)
        self.assertEqual(result["check"], "pass")
        self.assertEqual(
            result["files"],
            [
                {
                    "file": "page.html",
                    "removed": {"home-path": 2, "ip": 1},
                    "remaining": {},
                }
            ],
        )

    def test_files_in_a_subfolder_are_named_relative_to_the_common_folder(self):
        (self.dir / "lens").mkdir()
        a = self.write("page.html", "x")
        b = self.write("lens/arch.md", "x")
        _, out = self.cli("--json", str(a), str(b))
        self.assertEqual(
            [f["file"] for f in json.loads(out)["files"]], ["page.html", "lens/arch.md"]
        )

    def test_a_file_that_is_not_text_is_refused_without_echoing_content(self):
        path = self.dir / "shot.png"
        path.write_bytes(b"\x89PNG\xff\xfe/Users/jdoe")
        code, out, err = self.cli_err(str(path))
        self.assertEqual(code, 2)
        self.assertIn("not UTF-8 text", err)
        self.assertNotIn("jdoe", out + err)

    def test_a_missing_file_exits_2_with_a_message_on_stderr(self):
        code, out, err = self.cli_err(str(self.dir / "gone.html"))
        self.assertEqual((code, out), (2, ""))
        self.assertIn("gone.html", err)

    def test_an_unreadable_file_leaves_every_other_file_untouched(self):
        first = self.write("a.html", "/Users/jdoe/x")
        bad = self.dir / "b.png"
        bad.write_bytes(b"\xff\xfe")
        last = self.write("c.html", "/Users/jdoe/y")
        for flags in ([], ["--check"]):
            code, _, _ = self.cli_err(*flags, str(first), str(bad), str(last))
            self.assertEqual(code, 2)
            self.assertEqual(first.read_text(), "/Users/jdoe/x")
            self.assertEqual(last.read_text(), "/Users/jdoe/y")


class EvalFixtureTests(unittest.TestCase):
    """The #633 fixtures plant a fake token and use @example.invalid addresses."""

    @classmethod
    def setUpClass(cls):
        tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(tmp.cleanup)
        cls.repos = fixtures.generate(
            Path(tmp.name) / "fx", only=["single-script", "docs-only"]
        )

    def files(self, repo: Path):
        return [p for p in repo.rglob("*") if p.is_file() and ".git" not in p.parts]

    def test_the_planted_token_is_found_wherever_it_appears_in_text(self):
        token = fixtures.fake_token()
        for name, repo in self.repos.items():
            hits = [p for p in self.files(repo) if token in p.read_text()]
            self.assertTrue(hits, name)
            for path in hits:
                with self.subTest(f"{name}/{path.name}"):
                    cleaned, counts = scrub.scrub_text(path.read_text(), CTX)
                    self.assertGreaterEqual(counts.get("token", 0), 1)
                    self.assertNotIn(token, cleaned)

    def test_fixture_files_hold_nothing_else_to_remove(self):
        for name, repo in self.repos.items():
            for path in self.files(repo):
                with self.subTest(f"{name}/{path.name}"):
                    found = set(categories(path.read_text()))
                    self.assertLessEqual(found, {"token"})

    def test_example_invalid_addresses_are_not_flagged(self):
        for name, repo in self.repos.items():
            with self.subTest(name):
                log = subprocess.run(
                    ["git", "-C", str(repo), "log", "--format=%an <%ae> %cn <%ce>"],
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout
                self.assertIn("@example.invalid", log)
                self.assertEqual(categories(log), {})


if __name__ == "__main__":
    unittest.main()
