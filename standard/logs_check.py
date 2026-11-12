#!/usr/bin/env python3
"""Dependency-free conformance checker for wellmanifest.logs/v1."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from standard.logs_adoption import (
    load_error_catalog,
    load_error_documents,
    validate_adopted_error_catalog,
    validate_adopted_event_schema,
    validate_error_definition,
)
from standard.logs_contract import (
    EXPECTED_CONTINUITY_PROTO_FIELDS,
    EXPECTED_PROTO_MESSAGES,
    EXPECTED_RPCS,
    load_contract,
    validate_proto,
)
from standard.logs_events import (
    calculate_event_hash,
    validate_event,
    validate_repository,
    validate_request,
    validate_streams,
)
from standard.logs_primitives import (
    ACTOR_RE,
    ARTIFACT_RE,
    CODE_RE,
    CONTRACT_PATH,
    DATETIME_RE,
    DIAGNOSTIC_CODE,
    DOMAIN_TYPE_RE,
    ENDPOINT_REF_RE,
    EVENT_ID_RE,
    EXPECTED_PROCESSES,
    EXPECTED_REQUEST_GBNF,
    HELP_PATH,
    ID_RE,
    LEGACY_CONTRACT_PATHS,
    MAX_ADOPTED_CATALOG_BYTES,
    MAX_ADOPTED_SCHEMA_BYTES,
    MAX_ERROR_DOCUMENT_BYTES,
    MAX_REQUEST_BYTES,
    NAMESPACE_RE,
    OWNER_RE,
    PATH_RE,
    RECEIPT_RE,
    REMEDIATION_REF_RE,
    REQUIRED_ERROR_SECTIONS,
    SHA_RE,
    SOURCE_RE,
    SPAN_ID_RE,
    STATE_RE,
    STREAM_RE,
    SUBJECT_RE,
    TRACE_ID_RE,
    TRANSPORT_CODE_RE,
    ZERO_HASH,
    ContractFailure,
    Finding,
    canonical,
    confined_file,
    exact_fields,
    finding,
    read_json,
    report,
    require_datetime,
    require_string_list,
    sha256_bytes,
    sha256_file,
)
from standard.logs_selftest import run_self_test
from standard.logs_selftest_fixtures import (
    assert_error_adoption_invalid,
    assert_invalid,
    assert_valid,
    copy_fixture,
    rewrite_event,
    rewrite_event_at,
    write_adopter_error_fixture,
)
from standard.logs_subvalidators import (
    CAUSAL_PARENT_TYPES,
    CONTINUITY_EVENT_TYPES,
    CONTINUITY_FIELDS,
    CONTINUITY_SCHEMA_NAMES,
    validate_continuity,
    validate_diagnostic,
)

__all__ = [
    "ACTOR_RE",
    "ARTIFACT_RE",
    "CAUSAL_PARENT_TYPES",
    "CODE_RE",
    "CONTINUITY_EVENT_TYPES",
    "CONTINUITY_FIELDS",
    "CONTINUITY_SCHEMA_NAMES",
    "CONTRACT_PATH",
    "DATETIME_RE",
    "DIAGNOSTIC_CODE",
    "DOMAIN_TYPE_RE",
    "ENDPOINT_REF_RE",
    "EVENT_ID_RE",
    "EXPECTED_CONTINUITY_PROTO_FIELDS",
    "EXPECTED_PROCESSES",
    "EXPECTED_PROTO_MESSAGES",
    "EXPECTED_REQUEST_GBNF",
    "EXPECTED_RPCS",
    "HELP_PATH",
    "ID_RE",
    "LEGACY_CONTRACT_PATHS",
    "MAX_ADOPTED_CATALOG_BYTES",
    "MAX_ADOPTED_SCHEMA_BYTES",
    "MAX_ERROR_DOCUMENT_BYTES",
    "NAMESPACE_RE",
    "OWNER_RE",
    "PATH_RE",
    "RECEIPT_RE",
    "REMEDIATION_REF_RE",
    "REQUIRED_ERROR_SECTIONS",
    "SHA_RE",
    "SOURCE_RE",
    "SPAN_ID_RE",
    "STATE_RE",
    "STREAM_RE",
    "SUBJECT_RE",
    "TRACE_ID_RE",
    "TRANSPORT_CODE_RE",
    "ZERO_HASH",
    "ContractFailure",
    "Finding",
    "assert_error_adoption_invalid",
    "assert_invalid",
    "assert_valid",
    "build_parser",
    "calculate_event_hash",
    "canonical",
    "confined_file",
    "copy_fixture",
    "exact_fields",
    "finding",
    "load_contract",
    "load_error_catalog",
    "load_error_documents",
    "main",
    "print_report",
    "read_json",
    "report",
    "require_datetime",
    "require_string_list",
    "rewrite_event",
    "rewrite_event_at",
    "run_self_test",
    "sha256_bytes",
    "sha256_file",
    "validate_adopted_error_catalog",
    "validate_adopted_event_schema",
    "validate_continuity",
    "validate_diagnostic",
    "validate_error_definition",
    "validate_event",
    "validate_proto",
    "validate_repository",
    "validate_request",
    "validate_streams",
    "write_adopter_error_fixture",
]


def print_report(result: dict[str, Any], output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
        return
    if result["valid"]:
        print(
            "LOGS-PASS: "
            f"{result['streamsChecked']} stream(s), "
            f"{result['eventsChecked']} event(s), "
            f"{result['errorDefinitionsChecked']} error definition(s)"
        )
        return
    for item in result["findings"]:
        print(
            f"{item['code']} {item['severity']} [{item['rule']}] "
            f"{item['path']}: {item['message']} (help: {item['helpPath']})"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate", help="validate repository projections")
    validate.add_argument("--root", type=Path, default=Path("."))
    validate.add_argument("--format", choices=("text", "json"), default="text")
    request = subparsers.add_parser("request", help="validate a propose-only request")
    request.add_argument("--root", type=Path, default=Path("."))
    request.add_argument("--request", type=Path, required=True)
    request.add_argument("--format", choices=("text", "json"), default="text")
    adoption = subparsers.add_parser(
        "adoption", help="validate a consumer's adopted event schema"
    )
    adoption.add_argument("--root", type=Path, default=Path("."))
    adoption.add_argument("--event-schema", type=Path, required=True)
    adoption.add_argument("--format", choices=("text", "json"), default="text")
    error_adoption = subparsers.add_parser(
        "error-adoption", help="validate a consumer-owned error catalog and runbooks"
    )
    error_adoption.add_argument("--root", type=Path, default=Path("."))
    error_adoption.add_argument("--catalog", type=Path, required=True)
    error_adoption.add_argument("--format", choices=("text", "json"), default="text")
    subparsers.add_parser("self-test", help="run positive and adversarial conformance")
    return parser


def _print_findings(findings: list[dict[str, Any]]) -> None:
    for item in findings:
        print(
            f"{item['code']} {item['severity']} [{item['rule']}] "
            f"{item['path']}: {item['message']} (help: {item['helpPath']})"
        )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    source_root = Path(__file__).resolve().parents[1]
    if args.command == "self-test":
        run_self_test(source_root)
        return 0
    root = args.root.resolve()
    if args.command == "validate":
        result = validate_repository(root)
        print_report(result, args.format)
        return 0 if result["valid"] else 1
    if args.command == "adoption":
        result = validate_adopted_event_schema(root, args.event_schema)
        if args.format == "json":
            print(json.dumps(result, indent=2, sort_keys=True))
        elif result["valid"]:
            print(
                "LOGS-ADOPTION-PASS: event schema matches canonical contract "
                f"{result['contractSha256']}"
            )
        else:
            _print_findings(result["findings"])
        return 0 if result["valid"] else 1
    if args.command == "error-adoption":
        result = validate_adopted_error_catalog(root, args.catalog)
        if args.format == "json":
            print(json.dumps(result, indent=2, sort_keys=True))
        elif result["valid"]:
            print(
                "LOGS-ERROR-ADOPTION-PASS: "
                f"{result['errorDefinitionsChecked']} error definition(s) match "
                f"canonical contract {result['contractSha256']}"
            )
        else:
            _print_findings(result["findings"])
        return 0 if result["valid"] else 1
    try:
        bundle, _ = load_contract(root)
        value = read_json(
            args.request,
            rule="LOGS-REQUEST-JSON",
            label="request",
            max_bytes=MAX_REQUEST_BYTES,
        )
        normalized = validate_request(bundle, value)
    except ContractFailure as error:
        result = report([finding(error)], "", 0, 0, 0)
        print_report(result, args.format)
        return 1
    if args.format == "json":
        print(json.dumps(normalized, indent=2, sort_keys=True))
    else:
        print(f"LOGS-REQUEST-PASS: {normalized['operation']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
