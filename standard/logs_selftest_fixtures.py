"""Fixture helpers for wellmanifest.logs/v1 self-tests and unit tests."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from standard import logs_adoption as _a
from standard import logs_events as _e
from standard import logs_primitives as _p


def copy_fixture(source: Path, destination: Path) -> None:
    for relative in (
        *_p.LEGACY_CONTRACT_PATHS,
        _p.CONTRACT_PATH,
        Path("proto/wellmanifest/logs/v1/logs.proto"),
        Path("proto/current/wellmanifest/logs/v1/logs.proto"),
        Path("proto/v0.5/wellmanifest/logs/v1/logs.proto"),
        Path(_p.HELP_PATH),
        Path("logs/control.jsonl"),
        Path("logs/continuity.jsonl"),
    ):
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, target)


def rewrite_event_at(path: Path, index: int, mutate: Any) -> None:
    events = [json.loads(line) for line in path.read_text("utf-8").splitlines() if line]
    if index < 0:
        index += len(events)
    event = events[index]
    mutate(event)
    event["eventHash"] = _e.calculate_event_hash(event)
    for successor_index in range(index + 1, len(events)):
        events[successor_index]["previousHash"] = events[successor_index - 1][
            "eventHash"
        ]
        events[successor_index]["eventHash"] = _e.calculate_event_hash(
            events[successor_index]
        )
    path.write_text(
        "".join(_p.canonical(item) + "\n" for item in events), encoding="utf-8"
    )


def rewrite_event(path: Path, mutate: Any) -> None:
    rewrite_event_at(path, -1, mutate)


def assert_valid(root: Path, label: str) -> None:
    result = _e.validate_repository(root)
    if not result["valid"]:
        raise AssertionError(f"{label} was rejected: {result['findings']}")


def assert_invalid(root: Path, rule: str) -> None:
    result = _e.validate_repository(root)
    rules = {item["rule"] for item in result["findings"]}
    if result["valid"] or rule not in rules:
        raise AssertionError(f"expected {rule}, observed {sorted(rules)}")


def write_adopter_error_fixture(
    root: Path,
    contract_sha: str,
    *,
    codes: tuple[str, ...] = ("ONEDEV-TEST-001",),
) -> Path:
    errors = root / "errors"
    errors.mkdir(parents=True)
    for code in codes:
        title = "Concurrent coordinator cycle was safely rejected"
        definition = {
            "category": "CONCURRENCY",
            "causes": ["Another coordinator still owns the process lease"],
            "code": code,
            "doNot": ["Do not delete a live lease file or replay the status write"],
            "meaning": "The requested cycle did not run because another process owns the serialized coordinator boundary.",
            "owner": "service:onedev-agent",
            "relatedEventTypes": ["error_raised", "remediation_completed"],
            "remediation": [
                "Let the owning cycle finish or verify that its process terminated"
            ],
            "schema": "wellmanifest.logs/error/v1",
            "severity": "WARNING",
            "title": title,
            "verification": ["Run the coordinator concurrency regression test"],
            "version": 1,
        }
        (errors / f"{code}.md").write_text(
            f"# {code}: {title}\n\n"
            "## Error DSL\n\n"
            f"```log-error-dsl\n{_p.canonical(definition)}\n```\n\n"
            "## Situation\n\nA second coordinator attempted an overlapping cycle.\n\n"
            "## Meaning\n\nThe active owner retains exclusive status and queue authority.\n\n"
            "## Safe resolution\n\nWait for the owner or verify process termination before retrying.\n\n"
            "## Verification\n\nRun the deterministic concurrency regression.\n\n"
            "## Do not\n\nDo not remove a lease held by a live process.\n\n"
            "## Related events\n\nUse error_raised and remediation_completed.\n",
            encoding="utf-8",
        )
    catalog = root / "logs-error-catalog.v1.json"
    catalog.write_text(
        json.dumps(
            {
                "schema": "wellmanifest.logs/adopter-error-catalog/v1",
                "namespace": "ONEDEV",
                "contractSha256": contract_sha,
                "errorsDirectory": "errors",
                "diagnosticCodes": sorted(codes),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return catalog


def assert_error_adoption_invalid(source: Path, catalog: Path, rule: str) -> None:
    result = _a.validate_adopted_error_catalog(source, catalog)
    rules = {item["rule"] for item in result["findings"]}
    if result["valid"] or rule not in rules:
        raise AssertionError(f"expected adopter rule {rule}, observed {sorted(rules)}")
