import shutil
import tempfile
import unittest
from pathlib import Path

from runbooks.lib.gap_scanner import SOURCE_LABEL, TRIAGE_LABEL, run


class FakeRemote:
    def __init__(self, fixtures):
        self.fixtures = fixtures
        self.cloned = []

    def __call__(self, name, dest):
        self.cloned.append(name)
        if name not in self.fixtures:
            raise RuntimeError(f"unreachable: {name}")
        shutil.copytree(self.fixtures[name], dest)


class FakeTracker:
    def __init__(self):
        self.filed = []

    def __call__(self, body):
        self.filed.append(body)


class PayloadTracker:
    """Records issue payloads filed, and serves open dedup keys (the #20 seam)."""

    def __init__(self, open_keys=()):
        self.filed = []
        self._open = list(open_keys)

    def file_issue(self, payload):
        self.filed.append(payload)

    def open_issues(self):
        return list(self._open)


class GapScannerRunTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.fixtures = {}
        self.tracker = FakeTracker()

    def tearDown(self):
        self._tmp.cleanup()

    def _fixture_repo(self, name):
        src = self.base / "remote" / name
        src.mkdir(parents=True)
        (src / "README.md").write_text("proprietary")
        self.fixtures[name] = src

    def test_scans_listed_repos_files_nothing_and_cleans_up(self):
        self._fixture_repo("billing")
        self._fixture_repo("unlisted")
        clone = FakeRemote(self.fixtures)

        result = run(["billing"], clone=clone, file_issue=self.tracker)

        self.assertEqual(clone.cloned, ["billing"])
        self.assertEqual(result["scanned"], ["billing"])
        self.assertEqual(result["filed"], 0)
        self.assertEqual(self.tracker.filed, [])  # no proposal logic yet
        self.assertFalse(result["workdir"].exists())  # working area empty after run

    def test_empty_repo_list_is_a_clean_no_op(self):
        clone = FakeRemote(self.fixtures)
        result = run([], clone=clone, file_issue=self.tracker)
        self.assertEqual(clone.cloned, [])
        self.assertEqual(result["scanned"], [])
        self.assertEqual(result["filed"], 0)
        self.assertFalse(result["workdir"].exists())


class GapScannerProposalTest(unittest.TestCase):
    """The proposal step (#20): detect a recurring need across scanned repos,
    run the real sanitizer then the real proposal gate, file at most one
    generalized issue. Private content is blocked before it can be filed."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.fixtures = {}

    def tearDown(self):
        self._tmp.cleanup()

    def _fixture_repo(self, name):
        src = self.base / "remote" / name
        src.mkdir(parents=True)
        (src / "README.md").write_text("proprietary")
        self.fixtures[name] = src

    def _run(self, find_needs, tracker, **over):
        self._fixture_repo("billing")
        self._fixture_repo("payments")
        kwargs = dict(
            repo_list=["billing", "payments"],
            clone=FakeRemote(self.fixtures),
            find_needs=find_needs,
            open_issues=tracker.open_issues,
            file_issue=tracker.file_issue,
        )
        kwargs.update(over)
        return run(**kwargs)

    def test_recurring_need_files_one_generalized_proposal_with_labels(self):
        tracker = PayloadTracker()
        candidate = {
            "dedup_key": "retry-backoff-policy",
            "priority": 3,
            "title": "Skill: standard retry-with-backoff policy",
            "body": "Several repos hand-roll retry-with-backoff. A skill prescribing "
            "a standard policy would unify them.",
        }
        result = self._run(lambda repos: [candidate], tracker)

        self.assertEqual(result["filed"], 1)
        self.assertEqual(len(tracker.filed), 1)
        payload = tracker.filed[0]
        self.assertEqual(payload["title"], candidate["title"])
        self.assertIn(SOURCE_LABEL, payload["labels"])
        self.assertIn(TRIAGE_LABEL, payload["labels"])
        self.assertFalse(result["workdir"].exists())  # scratch cleaned up

    def test_private_structural_signal_in_body_is_blocked_nothing_filed(self):
        # Would clear the gate (high priority, unique key) but the body pastes a
        # file path — the sanitizer blocks it before the gate is consulted.
        tracker = PayloadTracker()
        candidate = {
            "dedup_key": "retry-backoff-policy",
            "priority": 9,
            "title": "leaky",
            "body": "The duplicated logic lives in src/billing/charge.py everywhere.",
        }
        result = self._run(lambda repos: [candidate], tracker)
        self.assertEqual(result["filed"], 0)
        self.assertEqual(tracker.filed, [])

    def test_private_signal_in_title_is_blocked_nothing_filed(self):
        # The title is published too, so it must pass the sanitizer just like the
        # body — a clean body does not excuse a leaky title.
        tracker = PayloadTracker()
        candidate = {
            "dedup_key": "retry-backoff-policy",
            "priority": 9,
            "title": "Generalize retry logic from src/billing/charge.py",
            "body": "A standard retry-with-backoff skill would unify the repos.",
        }
        result = self._run(lambda repos: [candidate], tracker)
        self.assertEqual(result["filed"], 0)
        self.assertEqual(tracker.filed, [])

    def test_private_marker_in_body_is_blocked(self):
        tracker = PayloadTracker()
        candidate = {
            "dedup_key": "k",
            "priority": 5,
            "title": "leaky marker",
            "body": "We keep redoing this in acme-internal/billing-core.",
        }
        result = self._run(
            lambda repos: [candidate], tracker,
            private_markers=["acme-internal/billing-core"],
        )
        self.assertEqual(result["filed"], 0)
        self.assertEqual(tracker.filed, [])

    def test_one_off_need_is_not_filed(self):
        # The analysis step judges recurrence; a one-off surfaces no candidate.
        tracker = PayloadTracker()
        result = self._run(lambda repos: [], tracker)
        self.assertEqual(result["filed"], 0)
        self.assertEqual(tracker.filed, [])

    def test_dedup_against_open_proposal_files_nothing(self):
        tracker = PayloadTracker(open_keys=["retry-backoff-policy"])
        candidate = {
            "dedup_key": "retry-backoff-policy",
            "priority": 3,
            "title": "dup",
            "body": "A standard retry-with-backoff skill would unify the repos.",
        }
        result = self._run(lambda repos: [candidate], tracker)
        self.assertEqual(result["filed"], 0)
        self.assertEqual(tracker.filed, [])

    def test_find_needs_receives_scanned_repo_paths(self):
        tracker = PayloadTracker()
        seen = {}

        def find(repos):
            seen["names"] = sorted(repos)
            for path in repos.values():
                # The analysis reads cloned content read-only.
                self.assertTrue((path / "README.md").exists())
            return []

        self._run(find, tracker)
        self.assertEqual(seen["names"], ["billing", "payments"])

    def test_clean_candidate_blocked_one_does_not_leak_a_filed_issue(self):
        # A leaky high-priority draft is dropped; a clean lower-priority draft
        # still files. Proves sanitize-then-gate over the survivors.
        tracker = PayloadTracker()
        leaky = {
            "dedup_key": "leak", "priority": 9, "title": "x",
            "body": "see src/secret/config.py",
        }
        clean = {
            "dedup_key": "clean-need", "priority": 2, "title": "clean",
            "body": "A shared idempotency-key convention would help across repos.",
        }
        result = self._run(lambda repos: [leaky, clean], tracker)
        self.assertEqual(result["filed"], 1)
        self.assertEqual(tracker.filed[0]["title"], "clean")

    def test_skeleton_compat_no_proposal_seams_scans_and_files_nothing(self):
        self._fixture_repo("billing")
        clone = FakeRemote(self.fixtures)
        result = run(["billing"], clone=clone)
        self.assertEqual(result["scanned"], ["billing"])
        self.assertEqual(result["filed"], 0)
        self.assertFalse(result["workdir"].exists())


if __name__ == "__main__":
    unittest.main()
