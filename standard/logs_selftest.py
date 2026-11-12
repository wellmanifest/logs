"""Positive and adversarial conformance self-tests for wellmanifest.logs/v1."""

from __future__ import annotations

import copy
import json
import shutil
import tempfile
from pathlib import Path

from standard import logs_adoption as _a
from standard import logs_contract as _c
from standard import logs_events as _e
from standard import logs_primitives as _p
from standard import logs_selftest_fixtures as _f
from standard import logs_subvalidators as _s


def _check_core_and_diagnostic_cases(source: Path, temporary: Path) -> None:
    baseline = temporary / "baseline"
    _f.copy_fixture(source, baseline)
    valid = _e.validate_repository(baseline)
    if not valid["valid"]:
        raise AssertionError(f"baseline failed: {valid['findings']}")
    with (baseline / "logs/continuity.jsonl").open(encoding="utf-8") as handle:
        fixture_types = [
            json.loads(line)["eventType"]
            for line in handle.read(_p.MAX_ADOPTED_SCHEMA_BYTES).splitlines()
        ]
    if set(fixture_types) != set(_s.CONTINUITY_EVENT_TYPES) or len(
        fixture_types
    ) != len(_s.CONTINUITY_EVENT_TYPES):
        raise AssertionError(
            "continuity fixture does not cover each declared boundary once"
        )

    for name, mutator, expected_rule in (
        ("extra", lambda ev: ev.update({"payload": {}}), "LOGS-EVENT-FIELDS"),
        (
            "unsafe",
            lambda ev: ev.update({"secretMaterialIncluded": True}),
            "LOGS-EVENT-SAFETY",
        ),
        ("chain", lambda ev: ev.update({"previousHash": "1" * 64}), "LOGS-EVENT-CHAIN"),
        (
            "evidence",
            lambda ev: ev["evidence"][0].update({"sha256": "2" * 64}),
            "LOGS-EVENT-EVIDENCE",
        ),
        (
            "undocumented",
            lambda ev: ev.update({"code": "LOGS-NOT-DOCUMENTED"}),
            "LOGS-EVENT-CODE",
        ),
        (
            "timestamp",
            lambda ev: ev.update({"occurredAt": "2026-08-12 18:20:00Z"}),
            "LOGS-EVENT-TIME",
        ),
        (
            "squat",
            lambda ev: ev.update({"eventType": "logs.forged"}),
            "LOGS-EVENT-TYPE",
        ),
        ("mode", lambda ev: ev.update({"mode": "apply"}), "LOGS-EVENT-MODE"),
        (
            "origin",
            lambda ev: ev.update({"source": "Logs.Bootstrap"}),
            "LOGS-EVENT-SOURCE",
        ),
        ("unbound", lambda ev: ev.update({"inputHash": "-"}), "LOGS-EVENT-INPUT"),
        (
            "placeholder",
            lambda ev: ev.update({"receiptRef": "-"}),
            "LOGS-EVENT-RECEIPT",
        ),
        (
            "state",
            lambda ev: ev.update({"subjectState": "SUCCEEDED "}),
            "LOGS-EVENT-STATE",
        ),
    ):
        case_dir = temporary / name
        _f.copy_fixture(source, case_dir)
        _f.rewrite_event(case_dir / "logs/control.jsonl", mutator)
        _f.assert_invalid(case_dir, expected_rule)

    domain = temporary / "domain"
    _f.copy_fixture(source, domain)
    _f.rewrite_event(
        domain / "logs/control.jsonl",
        lambda event: event.update({"eventType": "ticket.status_change"}),
    )
    _f.assert_valid(domain, "namespaced deployment event type")

    diagnostic = temporary / "diagnostic"
    _f.copy_fixture(source, diagnostic)
    _f.rewrite_event(
        diagnostic / "logs/control.jsonl",
        lambda event: event.update(
            {
                "diagnostic": {
                    "phase": "requesting_link",
                    "status": "failed",
                    "retryable": True,
                    "attempt": 2,
                    "attempts": 3,
                    "durationMs": 1501,
                    "endpointRef": "http://127.0.0.1:18081",
                    "transportCode": "ECONNREFUSED",
                    "httpStatus": None,
                    "remediationRefs": ["error://subactor/login-endpoint-unreachable"],
                    "traceId": "1" * 32,
                    "spanId": "2" * 16,
                }
            }
        ),
    )
    _f.assert_valid(diagnostic, "typed operational diagnostic")

    credential_endpoint = temporary / "credential-endpoint"
    _f.copy_fixture(source, credential_endpoint)
    _f.rewrite_event(
        credential_endpoint / "logs/control.jsonl",
        lambda event: event.update(
            {
                "diagnostic": {
                    "phase": "requesting_link",
                    "status": "failed",
                    "retryable": False,
                    "attempt": 1,
                    "attempts": 1,
                    "durationMs": 1,
                    "endpointRef": "https://user:placeholder@example.test/login?session=placeholder",
                    "transportCode": None,
                    "httpStatus": 401,
                    "remediationRefs": [],
                    "traceId": None,
                    "spanId": None,
                }
            }
        ),
    )
    _f.assert_invalid(credential_endpoint, "LOGS-EVENT-DIAGNOSTIC")

    attempt_order = temporary / "attempt-order"
    _f.copy_fixture(source, attempt_order)
    _f.rewrite_event(
        attempt_order / "logs/control.jsonl",
        lambda event: event.update(
            {
                "diagnostic": {
                    "phase": "polling_approval",
                    "status": "retrying",
                    "retryable": True,
                    "attempt": 3,
                    "attempts": 2,
                    "durationMs": 10,
                    "endpointRef": "endpoint:founder-control",
                    "transportCode": None,
                    "httpStatus": None,
                    "remediationRefs": ["knowledge://subactor/login/v1"],
                    "traceId": None,
                    "spanId": None,
                }
            }
        ),
    )
    _f.assert_invalid(attempt_order, "LOGS-EVENT-DIAGNOSTIC")


def _check_continuity_cases(source: Path, temporary: Path) -> None:
    missing_continuity = temporary / "missing-continuity"
    _f.copy_fixture(source, missing_continuity)
    _f.rewrite_event_at(
        missing_continuity / "logs/continuity.jsonl",
        0,
        lambda event: event.pop("continuity"),
    )
    _f.assert_invalid(missing_continuity, "LOGS-EVENT-CONTINUITY")

    for forbidden_field in (
        "rawPrompt",
        "rawDiff",
        "secret",
        "path",
        "hostPath",
        "toolStdout",
        "toolStderr",
    ):
        forbidden = temporary / f"forbidden-{forbidden_field.lower()}"
        _f.copy_fixture(source, forbidden)
        _f.rewrite_event_at(
            forbidden / "logs/continuity.jsonl",
            3,
            lambda event, field=forbidden_field: event["continuity"].update(
                {field: "excluded"}
            ),
        )
        _f.assert_invalid(forbidden, "LOGS-EVENT-CONTINUITY")

    host_path_receipt = temporary / "host-path-receipt"
    _f.copy_fixture(source, host_path_receipt)
    _f.rewrite_event_at(
        host_path_receipt / "logs/continuity.jsonl",
        3,
        lambda event: event["continuity"].update(
            {"executionReceiptRef": "receipt:///home/user/tool-output"}
        ),
    )
    _f.assert_invalid(host_path_receipt, "LOGS-EVENT-CONTINUITY")

    wrong_cause = temporary / "wrong-continuity-cause"
    _f.copy_fixture(source, wrong_cause)
    _f.rewrite_event(
        wrong_cause / "logs/continuity.jsonl",
        lambda event: event.update({"causationId": "event:continuity:001"}),
    )
    _f.assert_invalid(wrong_cause, "LOGS-EVENT-CONTINUITY-CAUSE")

    resume_digest = temporary / "resume-digest"
    _f.copy_fixture(source, resume_digest)
    _f.rewrite_event_at(
        resume_digest / "logs/continuity.jsonl",
        5,
        lambda event: event["continuity"].update({"snapshotDigest": "f" * 64}),
    )
    _f.assert_invalid(resume_digest, "LOGS-EVENT-CONTINUITY-DIGEST")

    pair_digest = temporary / "pair-digest"
    _f.copy_fixture(source, pair_digest)
    _f.rewrite_event_at(
        pair_digest / "logs/continuity.jsonl",
        3,
        lambda event: event["continuity"].update({"requestDigest": "e" * 64}),
    )
    _f.assert_invalid(pair_digest, "LOGS-EVENT-CONTINUITY-DIGEST")

    for label, event_index, digest_field in (
        ("commit-slice", 10, "sliceDigest"),
        ("push-commit", 11, "commitDigest"),
        ("push-completion-plan", 12, "pushPlanDigest"),
    ):
        publication_digest = temporary / label
        _f.copy_fixture(source, publication_digest)
        _f.rewrite_event_at(
            publication_digest / "logs/continuity.jsonl",
            event_index,
            lambda event, field=digest_field: event["continuity"].update(
                {field: "d" * 64}
            ),
        )
        _f.assert_invalid(publication_digest, "LOGS-EVENT-CONTINUITY-DIGEST")

    merged_publication = temporary / "merged-publication"
    _f.copy_fixture(source, merged_publication)
    _f.rewrite_event_at(
        merged_publication / "logs/continuity.jsonl",
        10,
        lambda event: event.update({"eventType": "git.push_started"}),
    )
    _f.assert_invalid(merged_publication, "LOGS-EVENT-CONTINUITY")

    wrong_resume_decision = temporary / "wrong-resume-decision"
    _f.copy_fixture(source, wrong_resume_decision)
    _f.rewrite_event_at(
        wrong_resume_decision / "logs/continuity.jsonl",
        6,
        lambda event: event.update({"outcome": "ACCEPTED", "subjectState": "resume"}),
    )
    _f.assert_invalid(wrong_resume_decision, "LOGS-EVENT-CONTINUITY-DECISION")

    matching_resume = temporary / "matching-resume"
    _f.copy_fixture(source, matching_resume)
    matching_events = [
        json.loads(line)
        for line in (matching_resume / "logs/continuity.jsonl")
        .read_text("utf-8")
        .splitlines()
    ]
    expected_state = matching_events[5]["continuity"]["expectedStateDigest"]
    _f.rewrite_event_at(
        matching_resume / "logs/continuity.jsonl",
        5,
        lambda event: event["continuity"].update(
            {"observedStateDigest": expected_state}
        ),
    )
    _f.rewrite_event_at(
        matching_resume / "logs/continuity.jsonl",
        6,
        lambda event: event.update({"outcome": "ACCEPTED", "subjectState": "resume"}),
    )
    _f.assert_valid(matching_resume, "resume decision after a matching observation")

    generic_payload = temporary / "generic-payload"
    _f.copy_fixture(source, generic_payload)
    _f.rewrite_event(
        generic_payload / "logs/control.jsonl",
        lambda event: event.update({"continuity": {"sessionDigest": "1" * 64}}),
    )
    _f.assert_invalid(generic_payload, "LOGS-EVENT-CONTINUITY")


def _check_docs_requests_and_adoption(source: Path, temporary: Path) -> None:
    docs = temporary / "docs"
    _f.copy_fixture(source, docs)
    page = docs / _p.HELP_PATH
    page.write_text(
        page.read_text("utf-8").replace("## Do not\n", "## Unsafe shortcuts\n"), "utf-8"
    )
    _f.assert_invalid(docs, "LOGS-DOC-SECTIONS")

    title = temporary / "title"
    _f.copy_fixture(source, title)
    page = title / _p.HELP_PATH
    page.write_text(
        page.read_text("utf-8").replace("# LOGS-VALIDATION-001:", "# LOGS-WRONG:"),
        "utf-8",
    )
    _f.assert_invalid(title, "LOGS-DOC-TITLE")

    grammar = temporary / "grammar"
    _f.copy_fixture(source, grammar)
    contract = _p.read_json(
        grammar / _p.CONTRACT_PATH,
        rule="SELF-TEST",
        label="self-test contract",
    )
    contract["requestGbnf"] = contract["requestGbnf"].replace("plan_append", "append")
    (grammar / _p.CONTRACT_PATH).write_text(
        json.dumps(contract, indent=2) + "\n", "utf-8"
    )
    _f.assert_invalid(grammar, "LOGS-CONTRACT-GRAMMAR")

    bundle, contract_sha = _c.load_contract(source)
    inspect = {
        "schema": "wellmanifest.logs/request/v1",
        "operation": "inspect",
        "processRef": _p.EXPECTED_PROCESSES["inspect"],
    }
    _e.validate_request(bundle, inspect)
    plan = {
        "schema": "wellmanifest.logs/request/v1",
        "operation": "plan_append",
        "processRef": _p.EXPECTED_PROCESSES["planAppend"],
        "stream": "control",
        "expectedVersion": 1,
        "eventRef": "artifact://wellmanifest.dev/logs/event/r1",
        "eventSha256": "1" * 64,
    }
    _e.validate_request(bundle, plan)
    for invalid in (
        {**inspect, "grant_ref": "grant:forged"},
        {**inspect, "operation": "append"},
    ):
        try:
            _e.validate_request(bundle, invalid)
        except _p.ContractFailure:
            pass
        else:
            raise AssertionError("authority-bearing request was accepted")

    canonical_schema = temporary / "canonical-event.schema.json"
    canonical_schema.write_text(
        json.dumps(bundle["schemas"]["event"], indent=2) + "\n", encoding="utf-8"
    )
    if not _a.validate_adopted_event_schema(source, canonical_schema)["valid"]:
        raise AssertionError("canonical adopted schema was rejected")

    stale_schema = temporary / "stale-event.schema.json"
    stale = copy.deepcopy(bundle["schemas"]["event"])
    stale["required"].remove("inputHash")
    stale["properties"].pop("inputHash")
    stale_schema.write_text(json.dumps(stale, indent=2) + "\n", encoding="utf-8")
    stale_result = _a.validate_adopted_event_schema(source, stale_schema)
    if (
        stale_result["valid"]
        or stale_result["findings"][0]["rule"] != "LOGS-ADOPTION-SCHEMA-DRIFT"
    ):
        raise AssertionError("stale adopted schema was accepted")

    adopter = temporary / "adopter"
    adopter_catalog = _f.write_adopter_error_fixture(adopter, contract_sha)
    adopted = _a.validate_adopted_error_catalog(source, adopter_catalog)
    if not adopted["valid"] or adopted["errorDefinitionsChecked"] != 1:
        raise AssertionError(
            f"valid adopter error catalog was rejected: {adopted['findings']}"
        )

    drift = temporary / "adopter-drift"
    shutil.copytree(adopter, drift)
    drift_catalog = drift / adopter_catalog.name
    drift_payload = _p.read_json(
        drift_catalog, rule="SELF-TEST", label="adopter catalog"
    )
    drift_payload["contractSha256"] = "0" * 64
    drift_catalog.write_text(
        json.dumps(drift_payload, indent=2) + "\n", encoding="utf-8"
    )
    _f.assert_error_adoption_invalid(
        source, drift_catalog, "LOGS-ADOPTION-ERROR-CONTRACT-DRIFT"
    )

    for name, ns in (("adopter-substituted", "SUBLLM"), ("adopter-reserved", "LOGS")):
        ns_dir = temporary / name
        shutil.copytree(adopter, ns_dir)
        ns_catalog = ns_dir / adopter_catalog.name
        ns_payload = _p.read_json(ns_catalog, rule="SELF-TEST", label="adopter catalog")
        ns_payload["namespace"] = ns
        ns_catalog.write_text(json.dumps(ns_payload, indent=2) + "\n", encoding="utf-8")
        _f.assert_error_adoption_invalid(
            source, ns_catalog, "LOGS-ADOPTION-ERROR-NAMESPACE"
        )

    missing = temporary / "adopter-missing"
    shutil.copytree(adopter, missing)
    (missing / "errors/ONEDEV-TEST-001.md").unlink()
    _f.assert_error_adoption_invalid(
        source, missing / adopter_catalog.name, "LOGS-DOC-CATALOG"
    )

    extra = temporary / "adopter-extra"
    extra_catalog = _f.write_adopter_error_fixture(
        extra,
        contract_sha,
        codes=("ONEDEV-EXTRA-001", "ONEDEV-TEST-001"),
    )
    extra_payload = _p.read_json(
        extra_catalog, rule="SELF-TEST", label="adopter catalog"
    )
    extra_payload["diagnosticCodes"] = ["ONEDEV-TEST-001"]
    extra_catalog.write_text(
        json.dumps(extra_payload, indent=2) + "\n", encoding="utf-8"
    )
    _f.assert_error_adoption_invalid(source, extra_catalog, "LOGS-DOC-CATALOG")


def run_self_test(source: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="wellmanifest-logs-") as raw_tmp:
        temporary = Path(raw_tmp)
        _check_core_and_diagnostic_cases(source, temporary)
        _check_continuity_cases(source, temporary)
        _check_docs_requests_and_adoption(source, temporary)
    print("logs conformance self-test: PASS (continuity and adversarial checks)")
