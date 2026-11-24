"""Check a repo-audit findings.json: its shape, the fixture expectations, and the diff between two runs.

Pure functions over parsed JSON, stdlib only. The schema validator implements
just the keywords findings.schema.json uses.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any, NamedTuple

AREAS = [
    "code-quality",
    "architecture",
    "tech-stack",
    "tests",
    "security",
    "privacy",
    "data-integrity",
    "performance",
    "accessibility",
    "content-branding",
    "usability",
    "feature-completeness",
    "repo-hygiene",
    "ops-release",
    "external-facts",
    "agent-readiness",
]

# The lens that owns each area (rubric.md, Areas table).
AREA_OWNER = {
    "code-quality": "code",
    "architecture": "architecture",
    "tech-stack": "architecture",
    "tests": "code",
    "security": "architecture",
    "privacy": "architecture",
    "data-integrity": "architecture",
    "performance": "code",
    "accessibility": "design",
    "content-branding": "design",
    "usability": "design",
    "feature-completeness": "product",
    "repo-hygiene": "product",
    "ops-release": "product",
    "external-facts": "architecture",
    "agent-readiness": "product",
}

QUICK_LENSES = ("code", "architecture")


class Result(NamedTuple):
    name: str
    ok: bool
    detail: str


# ------------------------------------------------------------------ schema


def _type_ok(value: Any, name: str) -> bool:
    if name == "object":
        return isinstance(value, dict)
    if name == "array":
        return isinstance(value, list)
    if name == "string":
        return isinstance(value, str)
    if name == "boolean":
        return isinstance(value, bool)
    if name == "null":
        return value is None
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return False


def _resolve(ref: str, root: dict) -> dict:
    if not ref.startswith("#/"):
        raise ValueError(f"unsupported $ref: {ref}")
    node: Any = root
    for part in ref[2:].split("/"):
        node = node[part]
    return node


def _walk(value: Any, schema: dict, path: str, root: dict, errors: list[str]) -> None:
    if "$ref" in schema:
        _walk(value, _resolve(schema["$ref"], root), path, root, errors)
        return
    if "type" in schema:
        names = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_type_ok(value, n) for n in names):
            errors.append(
                f"{path}: expected {'|'.join(names)}, got {type(value).__name__}"
            )
            return
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} is not one of {schema['enum']}")
    if (
        "pattern" in schema
        and isinstance(value, str)
        and not re.search(schema["pattern"], value)
    ):
        errors.append(f"{path}: {value!r} does not match {schema['pattern']}")
    if isinstance(value, dict):
        for name in schema.get("required", []):
            if name not in value:
                errors.append(f"{path}: missing required {name!r}")
        props = schema.get("properties", {})
        for name, sub in props.items():
            if name in value:
                _walk(value[name], sub, f"{path}.{name}", root, errors)
        if schema.get("additionalProperties") is False:
            for name in value:
                if name not in props:
                    errors.append(f"{path}: unexpected property {name!r}")
    if isinstance(value, list) and "items" in schema:
        for i, item in enumerate(value):
            _walk(item, schema["items"], f"{path}[{i}]", root, errors)


def validate(doc: Any, schema: dict) -> list[str]:
    """Return the schema violations of doc, empty when it is valid."""
    errors: list[str] = []
    _walk(doc, schema, "$", schema, errors)
    return errors


# -------------------------------------------------------------------- keys


def parse_key(key: str) -> tuple[str, str, str] | None:
    """Split `<area>:<check>:<path>` on its first two colons; None if malformed."""
    parts = key.split(":", 2)
    if len(parts) != 3 or not all(parts):
        return None
    area, check, path = parts
    while path.startswith("./"):
        path = path[2:]
    return area, check, path


def _norm_path(path: str) -> str:
    while path.startswith("./"):
        path = path[2:]
    return path


# ------------------------------------------------------------ expectations


def _dicts(value: Any) -> list[dict]:
    return [v for v in value if isinstance(v, dict)] if isinstance(value, list) else []


def _fact(doc: dict, name: str) -> str | None:
    """The value of the profile row for a fact: an exact name, else a row containing it."""
    rows = _dicts(doc.get("profile"))
    for row in rows:
        if str(row.get("fact", "")).strip().lower() == name:
            return str(row.get("value"))
    for row in rows:
        if re.search(rf"\b{name}\b", str(row.get("fact", "")).lower()):
            return str(row.get("value"))
    return None


def _check_profile(doc: dict, exp: dict) -> list[Result]:
    results = []
    if "type_regex" in exp or "fallback" in exp:
        value = _fact(doc, "type")
        if value is None:
            results.append(Result("type", False, "no `type` row in the profile"))
        else:
            problems = []
            if "type_regex" in exp and not re.search(
                exp["type_regex"], value, re.IGNORECASE
            ):
                problems.append(f"does not match /{exp['type_regex']}/")
            if "fallback" in exp:
                is_fallback = "fallback" in value.lower()
                if is_fallback != exp["fallback"]:
                    problems.append(
                        f"fallback profile expected {exp['fallback']}, got {is_fallback}"
                    )
            results.append(
                Result(
                    "type",
                    not problems,
                    f"{value!r}" + "".join(f"; {p}" for p in problems),
                )
            )
    if "tier" in exp:
        value = _fact(doc, "tier")
        if value is None:
            results.append(Result("tier", False, "no `tier` row in the profile"))
        else:
            ok = re.search(exp["tier"], value, re.IGNORECASE) is not None
            results.append(Result("tier", ok, f"{value!r}, expected {exp['tier']}"))
    if "packages_min" in exp:
        packages = _dicts(
            doc.get("scorecard", {}).get("packages")
            if isinstance(doc.get("scorecard"), dict)
            else None
        )
        ok = len(packages) >= exp["packages_min"]
        results.append(
            Result(
                "packages",
                ok,
                f"{len(packages)} package rows, expected at least {exp['packages_min']}",
            )
        )
    return results


def _check_lens_coverage(doc: dict, spec: dict) -> Result:
    """Every lens's coverage line says how it sampled (types.md, Size tiers)."""
    rows = _dicts(doc.get("lens_coverage"))
    if not rows:
        return Result("lens coverage", False, "no lens_coverage rows")
    unsampled = [
        str(row.get("lens"))
        for row in rows
        if not re.search(
            spec["regex"],
            f"{row.get('read')} {row.get('chosen_by')}",
            re.IGNORECASE,
        )
    ]
    if unsampled:
        return Result(
            "lens coverage",
            False,
            f"no sampling stated for: {', '.join(unsampled)}; expected /{spec['regex']}/",
        )
    return Result("lens coverage", True, f"{len(rows)} lens rows state their sample")


def _scorecard_areas(doc: dict) -> dict[str, dict]:
    card = doc.get("scorecard")
    rows = _dicts(card.get("areas")) if isinstance(card, dict) else []
    return {str(r.get("area")): r for r in rows}


def _check_areas(doc: dict, expected: dict) -> Result:
    have = _scorecard_areas(doc)
    problems = []
    for area, want in expected.items():
        if want is None:
            continue
        row = have.get(area)
        if row is None:
            problems.append(f"{area}: no scorecard row")
        elif row.get("applies") != want:
            problems.append(f"{area}: applies={row.get('applies')}, expected {want}")
    asserted = sum(1 for v in expected.values() if v is not None)
    detail = "; ".join(problems) if problems else f"{asserted} asserted areas match"
    return Result("applicable areas", not problems, detail)


def _reason(row: dict | None) -> str:
    value = row.get("not_assessed_reason") if row else None
    return value if isinstance(value, str) else ""


def check_coverage(doc: dict, depth: str) -> list[Result]:
    """No silent gap: every area has a verdict or a reason; quick says Depth for unlaunched lenses."""
    scorecard = _scorecard_areas(doc)
    coverage = {str(r.get("area")): r for r in _dicts(doc.get("coverage"))}
    problems = []
    for area in AREAS:
        card, cov = scorecard.get(area), coverage.get(area)
        if card is None:
            problems.append(f"{area}: no scorecard row")
            continue
        if cov is None:
            problems.append(f"{area}: no coverage row")
        unassessed = card.get("verdict") == "not_assessed"
        if card.get("applies") is False and not unassessed:
            problems.append(
                f"{area}: does not apply but has verdict {card.get('verdict')}"
            )
        if (unassessed or card.get("applies") is False) and not _reason(card):
            problems.append(f"{area}: not assessed with no reason")
        if (
            cov is not None
            and (unassessed or card.get("applies") is False)
            and not _reason(cov)
        ):
            problems.append(f"{area}: coverage row has no reason")
    results = [
        Result(
            "no silent gap",
            not problems,
            "; ".join(problems) or "16 areas, each a verdict or a reason",
        )
    ]
    if depth == "quick":
        gaps = []
        for area in AREAS:
            card = scorecard.get(area)
            if (
                card is None
                or AREA_OWNER[area] in QUICK_LENSES
                or card.get("applies") is False
            ):
                continue
            if card.get("verdict") != "not_assessed" or not _reason(card).startswith(
                "Depth"
            ):
                gaps.append(
                    f"{area}: expected Not assessed with a Depth reason, got {card.get('verdict')!r} / {_reason(card)!r}"
                )
        results.append(
            Result(
                "quick depth gaps",
                not gaps,
                "; ".join(gaps) or "unlaunched lenses' areas say Depth",
            )
        )
    return results


def _nearest(findings: list[dict], planted: dict) -> str:
    near = [
        f
        for f in findings
        if f.get("area") in planted["areas"]
        or (parse_key(str(f.get("key", ""))) or ("", "", ""))[2] in planted["paths"]
    ]
    if not near:
        return "no finding in the expected areas or paths"
    return "nearest: " + ", ".join(repr(f.get("key")) for f in near[:3])


def _check_planted(doc: dict, planted: dict, depth: str) -> Result:
    label = f"planted: {planted['id']}"
    if depth not in planted.get("checked_at", ["quick", "standard"]):
        area = planted["gap_area"]
        row = _scorecard_areas(doc).get(area)
        if row is None:
            return Result(label + " (depth gap)", False, f"{area}: no scorecard row")
        if row.get("applies") is False:
            return Result(label + " (depth gap)", True, f"{area} does not apply")
        ok = row.get("verdict") == "not_assessed" and _reason(row).startswith("Depth")
        return Result(
            label + " (depth gap)",
            ok,
            f"{area}: {row.get('verdict')!r}, reason {_reason(row)!r}",
        )
    findings = _dicts(doc.get("findings"))
    wanted = {_norm_path(p) for p in planted["paths"]}
    for f in findings:
        parsed = parse_key(str(f.get("key", "")))
        if parsed is None:
            continue
        area, check, path = parsed
        if (
            area in planted["areas"]
            and path in wanted
            and re.search(planted["check"], check, re.IGNORECASE)
        ):
            return Result(label, True, f"found {f.get('key')!r}")
    return Result(label, False, "no finding matches; " + _nearest(findings, planted))


def check_expectations(doc: Any, exp: dict, depth: str) -> list[Result]:
    """Evaluate one fixture's expectations against a findings document at a depth.

    exp is the fixture's entry in expectations.json. The document should already
    have passed `validate`; a malformed one yields failures, not exceptions.
    """
    if not isinstance(doc, dict):
        return [Result("findings.json", False, "not a JSON object")]
    results = _check_profile(doc, exp.get("profile", {}))
    if "lens_coverage" in exp:
        results.append(_check_lens_coverage(doc, exp["lens_coverage"]))
    results.append(_check_areas(doc, exp.get("areas", {})))
    results += check_coverage(doc, depth)
    results += [_check_planted(doc, p, depth) for p in exp.get("planted", [])]
    return results


# -------------------------------------------------------------------- diff


def _keys(doc: dict) -> list[str]:
    seen: list[str] = []
    for f in _dicts(doc.get("findings")):
        key = f.get("key")
        if isinstance(key, str) and key not in seen:
            seen.append(key)
    return seen


def diff_input_errors(doc: Any) -> list[str]:
    """Why a previous findings.json cannot be diffed, empty when it can.

    Checks only what the diff reads, not the full schema: a baseline from an older
    schema (no `go_public`, retired lens names) still diffs. `area` and `severity`
    are optional; a string when present.
    """
    if not isinstance(doc, dict):
        return ["not a JSON object"]
    findings = doc.get("findings")
    if not isinstance(findings, list):
        return ["`findings` is not a list"]
    errors: list[str] = []
    for i, f in enumerate(findings):
        if not isinstance(f, dict):
            errors.append(f"findings[{i}]: not an object")
            continue
        key = f.get("key")
        if not isinstance(key, str):
            errors.append(f"findings[{i}]: `key` is not a string")
        elif parse_key(key) is None:
            errors.append(f"findings[{i}]: malformed key {key!r}")
        for name in ("area", "severity"):
            if name in f and not isinstance(f[name], str):
                errors.append(f"findings[{i}]: `{name}` is not a string")
    return errors


def changed_paths_cover(path: str, changed: list[str]) -> bool:
    """Whether a change touches a key's path: a file or a directory; `.` is the whole repo."""
    path = _norm_path(path).rstrip("/")
    if path in ("", "."):
        return bool(changed)
    return any(c == path or c.startswith(path + "/") for c in map(_norm_path, changed))


def _areas_by_key(doc: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for f in _dicts(doc.get("findings")):
        key, area = f.get("key"), f.get("area")
        if isinstance(key, str) and isinstance(area, str):
            out.setdefault(key, area)
    return out


def diff_runs(
    prev: dict,
    cur: dict,
    *,
    not_rechecked: Iterable[str] = (),
    changed: list[str] | None = None,
) -> dict[str, list[str]]:
    """Compare two runs on `key`.

    new: only in cur. still_open: in both. A key in prev only is:
    - not_rechecked: its area (the prev finding's `area`, else the key's prefix) was
      not assessed in cur, or a lens named it in `not_rechecked` (sampled out, not
      read). Absence proves nothing.
    - not_reraised: the code did not change under its path, or the commits could not
      be compared (`changed` is None). Absence is noise, not a fix.
    - fixed: re-checked, and a changed file lies under its path.

    changed is the files changed between the two pinned commits (`git diff
    --name-only --no-renames <prev>..<cur>`), [] when the commits are equal. A key
    named in `not_rechecked` that is still in cur stays still_open.
    """
    before, after = _keys(prev), _keys(cur)
    areas = _scorecard_areas(cur)
    prev_area = _areas_by_key(prev)
    named = set(not_rechecked)
    out: dict[str, list[str]] = {
        "new": [k for k in after if k not in before],
        "fixed": [],
        "still_open": [k for k in before if k in after],
        "not_rechecked": [],
        "not_reraised": [],
    }
    for key in before:
        if key in after:
            continue
        parsed = parse_key(key)
        area = prev_area.get(key) or (parsed[0] if parsed else "")
        row = areas.get(area)
        assessed = (
            row is not None
            and row.get("applies") is True
            and row.get("verdict") != "not_assessed"
        )
        if not assessed or key in named:
            out["not_rechecked"].append(key)
        elif changed is None or not (
            parsed and changed_paths_cover(parsed[2], changed)
        ):
            out["not_reraised"].append(key)
        else:
            out["fixed"].append(key)
    return out
