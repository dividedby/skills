"""Drift guard: asserts harness _repair_json and the skill's repair_json have byte-identical bodies.

The two copies are intentionally duplicated (ADR 0026) — the skill must stay
self-contained (ADR 0008) so it cannot import harness code at a Consumer's
runtime. This test enforces that the duplication never silently diverges:
a one-sided edit fails CI before the copies drift in behaviour.
"""

import importlib.util
import inspect
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import cli  # noqa: E402  (after sys.path bootstrap)

_HARNESS_CLI_PATH = Path(__file__).resolve().parents[1] / "cli.py"
_SKILL_REPAIR_PATH = (
    Path(__file__).resolve().parents[2]
    / "skills/meta/apply-agent-research/lib/json_repair.py"
)


def _load_skill_module():
    spec = importlib.util.spec_from_file_location("json_repair", _SKILL_REPAIR_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _body(src: str) -> str:
    """Return the executable body of a repair function, stripping the def line and docstring.

    Drops the ``def`` line (names differ: ``_repair_json`` vs ``repair_json``)
    and the triple-quoted docstring (text may differ). Everything below the
    closing ``\"\"\"`` of the docstring must be byte-identical across copies.

    Assumption: no nested triple-quotes in the body (true here).
    """
    after_open = src.partition('"""')[2]
    body = after_open.partition('"""')[2]
    return body.strip()


class RepairJsonDriftTest(unittest.TestCase):
    def setUp(self):
        self._skill_mod = _load_skill_module()

    def test_bodies_are_byte_identical(self):
        h_src = inspect.getsource(cli._repair_json)
        s_src = inspect.getsource(self._skill_mod.repair_json)

        h_body = _body(h_src)
        s_body = _body(s_src)

        self.assertEqual(
            h_body,
            s_body,
            f"repair_json drifted — update both copies (canonical: harness/cli.py).\n"
            f"  harness: {_HARNESS_CLI_PATH}\n"
            f"  skill:   {_SKILL_REPAIR_PATH}",
        )

    def test_normalized_body_is_non_empty(self):
        """Anti-theater: ensures the normalization didn't strip everything to ''."""
        s_src = inspect.getsource(self._skill_mod.repair_json)
        s_body = _body(s_src)
        self.assertTrue(s_body, "normalized body is empty — normalization bug?")

    def test_normalized_body_contains_known_token(self):
        """Anti-theater: the real body must contain a known implementation token."""
        s_src = inspect.getsource(self._skill_mod.repair_json)
        self.assertIn(
            "in_string",
            _body(s_src),
            "known token 'in_string' missing from normalized body — normalization bug?",
        )


if __name__ == "__main__":
    unittest.main()
