import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))

from sanitizer import check  # noqa: E402  (after sys.path bootstrap)


class SanitizerGuardTest(unittest.TestCase):
    def test_allows_generalized_body(self):
        body = (
            "Several repos repeat the same retry-with-backoff logic by hand. "
            "A skill that prescribes a standard backoff policy would help."
        )
        result = check(body)
        self.assertTrue(result["allowed"])
        self.assertIsNone(result["reason"])

    def test_allows_empty_body(self):
        result = check("")
        self.assertTrue(result["allowed"])

    def test_allows_abstract_description_of_a_need(self):
        # Mentions a domain (billing, retries) abstractly: no path, code, or marker.
        body = (
            "Multiple billing services reimplement idempotent retries differently. "
            "A shared skill describing an idempotency-key convention would unify them."
        )
        result = check(body, private_markers=["acme-internal/billing-core"])
        self.assertTrue(result["allowed"])

    def test_blocks_import_line(self):
        body = "Seen everywhere:\nfrom billing.core import ChargeProcessor\nand again."
        result = check(body)
        self.assertFalse(result["allowed"])
        self.assertIn("import", result["reason"].lower())

    def test_blocks_quoted_file_path(self):
        body = "The duplicated logic sits in src/billing/charge.py across services."
        result = check(body)
        self.assertFalse(result["allowed"])
        self.assertIn("path", result["reason"].lower())

    def test_blocks_pasted_code_block(self):
        body = (
            "This pattern recurs. For example:\n\n"
            "```python\ndef charge(account):\n    return account.balance\n```"
        )
        result = check(body)
        self.assertFalse(result["allowed"])
        self.assertIn("code", result["reason"].lower())

    def test_blocks_known_private_marker(self):
        body = "We keep redoing this in acme-internal/billing-core every quarter."
        result = check(body, private_markers=["acme-internal/billing-core"])
        self.assertFalse(result["allowed"])
        self.assertIn("acme-internal/billing-core", result["reason"])

    def test_source_url_with_a_path_is_over_blocked_known_limit(self):
        # Documents the known limit: the structural path signal also matches a
        # public source URL that has a path-with-extension. We keep check() strict
        # (the structural guard is load-bearing) rather than weaken it; #20 cites
        # sources by bare domain instead. See test below.
        body = "Pattern documented at https://example.com/guide/patterns.html."
        result = check(body)
        self.assertFalse(result["allowed"])
        self.assertIn("path", result["reason"].lower())

    def test_bare_domain_citation_is_allowed(self):
        # The citation style #20 uses so legitimate proposals are not over-blocked.
        body = (
            "Multiple repos reimplement retry-with-backoff. A standard policy "
            "(see the discussion on martinfowler.com) would unify them."
        )
        result = check(body)
        self.assertTrue(result["allowed"])


if __name__ == "__main__":
    unittest.main()
