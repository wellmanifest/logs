#!/usr/bin/env python3
"""Dependency-free conformance checker for wellmanifest.logs/v1."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import shutil
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


CONTRACT_PATH = Path("contracts/logs.contract.json")
HELP_PATH = "errors/LOGS-VALIDATION-001.md"
DIAGNOSTIC_CODE = "LOGS-VALIDATION-001"
ZERO_HASH = "0" * 64
CODE_RE = re.compile(r"^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+$")
STREAM_RE = re.compile(r"^[a-z][a-z0-9._-]{0,63}$")
ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
EVENT_ID_RE = re.compile(r"^event:[A-Za-z0-9._:-]{2,122}$")
ACTOR_RE = re.compile(r"^(?:human|agent|service):[A-Za-z0-9._:-]+$")
OWNER_RE = re.compile(r"^(?:human|agent|service|unresolved):[A-Za-z0-9._:-]+$")
SUBJECT_RE = re.compile(r"^[a-z][a-z0-9+.-]*:[A-Za-z0-9._:/-]+$")
PATH_RE = re.compile(r"^(?!/)(?!.*(?:^|/)\.\.(?:/|$))[A-Za-z0-9._/-]+$")
SHA_RE = re.compile(r"^[a-f0-9]{64}$")
DATETIME_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]"
    r"(?:\.[0-9]{1,9})?Z$"
)
ARTIFACT_RE = re.compile(
    r"^artifact://[a-z0-9.-]+/[A-Za-z0-9._:/-]+/r[1-9][0-9]*$"
)
REQUIRED_ERROR_SECTIONS = (
    "Error DSL",
    "Situation",
    "Meaning",
    "Safe resolution",
    "Verification",
    "Do not",
    "Related events",
)
EXPECTED_PROCESSES = {
    "inspect": "logs://repository/contracts/query/inspect",
    "validate": "logs://repository/events/query/validate",
    "planAppend": "logs://stream/events/query/plan-append",
    "append": "logs://stream/events/command/append",
    "registerError": "logs://repository/errors/command/register",
}
EXPECTED_REQUEST_GBNF = "\n".join(
    (
        r"root ::= inspect | plan_append",
        r'inspect ::= "{\"schema\":\"wellmanifest.logs/request/v1\",\"operation\":\"inspect\",\"processRef\":\"logs://repository/contracts/query/inspect\"}"',
        r'plan_append ::= "{\"schema\":\"wellmanifest.logs/request/v1\",\"operation\":\"plan_append\",\"processRef\":\"logs://stream/events/query/plan-append\",\"stream\":" string ",\"expectedVersion\":" integer ",\"eventRef\":" string ",\"eventSha256\":" string "}"',
        r'integer ::= "0" | [1-9] [0-9]*',
        r'string ::= "\"" chars "\""',
        r'chars ::= ([^"\\\x00-\x1f] | "\\" (["\\/bfnrt] | "u" [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F]))*',
    )
) + "\n"
EXPECTED_PROTO_MESSAGES = (
    "EvidenceRef",
    "LogEvent",
    "ErrorDefinition",
    "InspectRequest",
    "InspectResponse",
    "PlanAppendRequest",
    "PlanAppendResponse",
    "ExecuteAppendRequest",
    "ExecuteAppendResponse",
    "ValidateRepositoryRequest",
    "ValidateRepositoryResponse",
    "ReadStreamRequest",
    "ReadStreamResponse",
    "Finding",
)
EXPECTED_RPCS = (
    "rpc Inspect(InspectRequest) returns (InspectResponse);",
    "rpc PlanAppend(PlanAppendRequest) returns (PlanAppendResponse);",
    "rpc ExecuteAppend(ExecuteAppendRequest) returns (ExecuteAppendResponse);",
    "rpc ValidateRepository(ValidateRepositoryRequest) returns (ValidateRepositoryResponse);",
    "rpc ReadStream(ReadStreamRequest) returns (ReadStreamResponse);",
)


@dataclass(frozen=True)
class Finding:
    code: str
    rule: str
    severity: str
    path: str
    message: str
    helpPath: str = HELP_PATH


class ContractFailure(ValueError):
    def __init__(self, rule: str, path: str, message: str) -> None:
        super().__init__(message)
        self.rule = rule
        self.path = path
        self.message = message


def canonical(value: Any) -> str:
    """Canonical JSON for the v1 domain, which deliberately excludes floats."""
    _reject_float(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _reject_float(value: Any) -> None:
    if isinstance(value, float):
        raise ContractFailure(
            "LOGS-CANONICAL-NUMBER",
            CONTRACT_PATH.as_posix(),
            "floating-point values are outside the v1 canonical domain",
        )
    if isinstance(value, dict):
        for child in value.values():
            _reject_float(child)
    elif isinstance(value, list):
        for child in value:
            _reject_float(child)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def exact_fields(
    value: Any,
    required: set[str],
    *,
    rule: str,
    path: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractFailure(rule, path, "document must be an object")
    observed = set(value)
    if observed != required:
        raise ContractFailure(rule, path, "document fields do not match the closed contract")
    return value


def read_json(path: Path, *, rule: str, label: str) -> Any:
    try:
        return json.loads(path.read_text("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ContractFailure(rule, path.as_posix(), f"{label} is unreadable or invalid") from error


def _assert_closed_objects(value: Any, path: str = "schemas") -> None:
    if isinstance(value, dict):
        if value.get("type") == "object" and value.get("additionalProperties") is not False:
            raise ContractFailure(
                "LOGS-CONTRACT-CLOSED",
                CONTRACT_PATH.as_posix(),
                f"object schema at {path} is not closed",
            )
        for key, child in value.items():
            _assert_closed_objects(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_closed_objects(child, f"{path}[{index}]")


def load_contract(root: Path) -> tuple[dict[str, Any], str]:
    path = root / CONTRACT_PATH
    bundle = exact_fields(
        read_json(path, rule="LOGS-CONTRACT-JSON", label="contract bundle"),
        {
            "$schema",
            "schema",
            "version",
            "canonical",
            "protobufPath",
            "projection",
            "hashProfile",
            "processes",
            "diagnosticCodes",
            "vocabulary",
            "requestGbnf",
            "schemas",
        },
        rule="LOGS-CONTRACT-FIELDS",
        path=CONTRACT_PATH.as_posix(),
    )
    constants = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "schema": "wellmanifest.logs/contract-bundle/v1",
        "version": "0.1.0",
        "canonical": "protobuf",
        "protobufPath": "proto/wellmanifest/logs/v1/logs.proto",
        "projection": "canonical-jsonl",
        "hashProfile": "wellmanifest-canonical-json-v1+SHA-256",
    }
    if any(bundle.get(key) != expected for key, expected in constants.items()):
        raise ContractFailure(
            "LOGS-CONTRACT-IDENTITY",
            CONTRACT_PATH.as_posix(),
            "contract identity or canonicalization profile changed",
        )
    if bundle.get("processes") != EXPECTED_PROCESSES:
        raise ContractFailure(
            "LOGS-CONTRACT-PROCESS",
            CONTRACT_PATH.as_posix(),
            "POA process registry is incomplete or changed",
        )
    if bundle.get("diagnosticCodes") != [DIAGNOSTIC_CODE]:
        raise ContractFailure(
            "LOGS-CONTRACT-CATALOG",
            CONTRACT_PATH.as_posix(),
            "diagnostic catalog does not match the v1 runtime",
        )
    schemas = exact_fields(
        bundle.get("schemas"),
        {"evidence", "event", "error", "request"},
        rule="LOGS-CONTRACT-SCHEMAS",
        path=CONTRACT_PATH.as_posix(),
    )
    vocabulary = exact_fields(
        bundle.get("vocabulary"),
        {"severities", "eventTypes", "outcomes", "errorCategories"},
        rule="LOGS-CONTRACT-VOCABULARY",
        path=CONTRACT_PATH.as_posix(),
    )
    for key in vocabulary:
        values = vocabulary[key]
        if not isinstance(values, list) or not values or len(values) != len(set(values)):
            raise ContractFailure(
                "LOGS-CONTRACT-VOCABULARY",
                CONTRACT_PATH.as_posix(),
                "contract vocabulary must contain nonempty unique arrays",
            )
    event_properties = schemas["event"].get("properties", {})
    if event_properties.get("severity", {}).get("enum") != vocabulary["severities"]:
        raise ContractFailure(
            "LOGS-CONTRACT-VOCABULARY",
            CONTRACT_PATH.as_posix(),
            "event severity schema differs from vocabulary",
        )
    if event_properties.get("eventType", {}).get("enum") != vocabulary["eventTypes"]:
        raise ContractFailure(
            "LOGS-CONTRACT-VOCABULARY",
            CONTRACT_PATH.as_posix(),
            "event type schema differs from vocabulary",
        )
    if event_properties.get("outcome", {}).get("enum") != vocabulary["outcomes"]:
        raise ContractFailure(
            "LOGS-CONTRACT-VOCABULARY",
            CONTRACT_PATH.as_posix(),
            "event outcome schema differs from vocabulary",
        )
    _assert_closed_objects(schemas)
    if bundle.get("requestGbnf") != EXPECTED_REQUEST_GBNF:
        raise ContractFailure(
            "LOGS-CONTRACT-GRAMMAR",
            CONTRACT_PATH.as_posix(),
            "request grammar differs from the closed propose-only compatibility unit",
        )
    return bundle, sha256_file(path)


def validate_proto(root: Path, bundle: dict[str, Any]) -> None:
    relative = Path(bundle["protobufPath"])
    path = confined_file(root, relative.as_posix(), "LOGS-PROTO-PATH")
    try:
        text = path.read_text("utf-8")
    except (OSError, UnicodeError) as error:
        raise ContractFailure(
            "LOGS-PROTO-READ",
            relative.as_posix(),
            "Protobuf contract is unreadable",
        ) from error
    required = [
        'syntax = "proto3";',
        "package wellmanifest.logs.v1;",
        "service LogsControlService {",
        *(f"message {name} {{" for name in EXPECTED_PROTO_MESSAGES),
        *EXPECTED_RPCS,
    ]
    vocabulary = bundle["vocabulary"]
    required.extend(f"SEVERITY_{value}" for value in vocabulary["severities"])
    required.extend(
        f"EVENT_TYPE_{value.upper()}" for value in vocabulary["eventTypes"]
    )
    required.extend(f"OUTCOME_{value}" for value in vocabulary["outcomes"])
    forbidden = (
        "google.protobuf.Struct",
        "google.protobuf.Value",
        "bytes payload",
        "string raw_output",
        "string credential",
        "string shell",
    )
    if any(fragment not in text for fragment in required) or any(
        fragment in text for fragment in forbidden
    ):
        raise ContractFailure(
            "LOGS-PROTO-COMPLETE",
            relative.as_posix(),
            "Protobuf messages, RPCs or bounded vocabulary are incomplete",
        )


def confined_file(root: Path, relative: str, rule: str) -> Path:
    if PATH_RE.fullmatch(relative) is None:
        raise ContractFailure(rule, relative, "path violates repository confinement")
    resolved_root = root.resolve()
    candidate = (resolved_root / relative).resolve()
    try:
        candidate.relative_to(resolved_root)
    except ValueError as error:
        raise ContractFailure(rule, relative, "path escapes the repository root") from error
    if not candidate.is_file():
        raise ContractFailure(rule, relative, "required file is missing")
    return candidate


def require_string_list(
    value: Any,
    *,
    minimum: int,
    maximum: int,
    unique: bool,
    rule: str,
    path: str,
) -> list[str]:
    if (
        not isinstance(value, list)
        or not minimum <= len(value) <= maximum
        or any(not isinstance(item, str) or not item or len(item) > 320 for item in value)
        or (unique and len(value) != len(set(value)))
    ):
        raise ContractFailure(rule, path, "string list violates its bounded contract")
    return value


def validate_error_definition(
    value: Any,
    *,
    code: str,
    bundle: dict[str, Any],
    path: str,
) -> dict[str, Any]:
    definition = exact_fields(
        value,
        {
            "schema",
            "code",
            "version",
            "severity",
            "category",
            "title",
            "meaning",
            "causes",
            "remediation",
            "verification",
            "doNot",
            "owner",
            "relatedEventTypes",
        },
        rule="LOGS-DOC-FIELDS",
        path=path,
    )
    vocabulary = bundle["vocabulary"]
    if definition.get("schema") != "wellmanifest.logs/error/v1":
        raise ContractFailure("LOGS-DOC-SCHEMA", path, "error DSL schema is unsupported")
    if definition.get("code") != code or CODE_RE.fullmatch(code) is None:
        raise ContractFailure("LOGS-DOC-CODE", path, "error DSL code differs from its file")
    version = definition.get("version")
    if isinstance(version, bool) or not isinstance(version, int) or not 1 <= version <= 2147483647:
        raise ContractFailure("LOGS-DOC-VERSION", path, "error DSL version is invalid")
    if definition.get("severity") not in {"WARNING", "ERROR", "CRITICAL"}:
        raise ContractFailure("LOGS-DOC-SEVERITY", path, "error severity is invalid")
    if definition.get("category") not in vocabulary["errorCategories"]:
        raise ContractFailure("LOGS-DOC-CATEGORY", path, "error category is invalid")
    for key, maximum in (("title", 160), ("meaning", 600)):
        item = definition.get(key)
        if not isinstance(item, str) or not item or len(item) > maximum:
            raise ContractFailure("LOGS-DOC-TEXT", path, f"error {key} is invalid")
    require_string_list(
        definition.get("causes"),
        minimum=1,
        maximum=12,
        unique=True,
        rule="LOGS-DOC-CAUSES",
        path=path,
    )
    for key in ("remediation", "verification", "doNot"):
        require_string_list(
            definition.get(key),
            minimum=1,
            maximum=12,
            unique=False,
            rule="LOGS-DOC-STEPS",
            path=path,
        )
    owner = definition.get("owner")
    if not isinstance(owner, str) or OWNER_RE.fullmatch(owner) is None:
        raise ContractFailure("LOGS-DOC-OWNER", path, "error owner route is invalid")
    related = require_string_list(
        definition.get("relatedEventTypes"),
        minimum=1,
        maximum=7,
        unique=True,
        rule="LOGS-DOC-EVENTS",
        path=path,
    )
    if any(item not in vocabulary["eventTypes"] for item in related):
        raise ContractFailure("LOGS-DOC-EVENTS", path, "error references an unknown event type")
    return definition


def load_error_catalog(root: Path, bundle: dict[str, Any]) -> dict[str, dict[str, Any]]:
    directory = root / "errors"
    if not directory.is_dir():
        raise ContractFailure("LOGS-DOC-DIRECTORY", "errors", "error directory is missing")
    documents: dict[str, dict[str, Any]] = {}
    unexpected = sorted(
        item.name for item in directory.iterdir() if not item.is_file() or item.suffix != ".md"
    )
    if unexpected:
        raise ContractFailure(
            "LOGS-DOC-PATH",
            "errors",
            "error directory contains an unsupported entry",
        )
    fence_pattern = re.compile(r"```log-error-dsl\n([^\n]+)\n```", re.MULTILINE)
    for file_path in sorted(directory.glob("*.md")):
        code = file_path.stem
        relative = file_path.relative_to(root).as_posix()
        if CODE_RE.fullmatch(code) is None:
            raise ContractFailure("LOGS-DOC-PATH", relative, "error filename is not a stable code")
        try:
            text = file_path.read_text("utf-8")
        except (OSError, UnicodeError) as error:
            raise ContractFailure("LOGS-DOC-READ", relative, "error page is unreadable") from error
        for section in REQUIRED_ERROR_SECTIONS:
            marker = f"## {section}\n"
            if text.count(marker) != 1:
                raise ContractFailure(
                    "LOGS-DOC-SECTIONS",
                    relative,
                    "error page does not contain each required section exactly once",
                )
            after = text.split(marker, 1)[1]
            body = after.split("\n## ", 1)[0].strip()
            if not body:
                raise ContractFailure(
                    "LOGS-DOC-SECTIONS",
                    relative,
                    "error page contains an empty required section",
                )
        fences = fence_pattern.findall(text)
        if len(fences) != 1:
            raise ContractFailure(
                "LOGS-DOC-FENCE",
                relative,
                "error page must contain exactly one single-line log-error-dsl fence",
            )
        try:
            definition = json.loads(fences[0])
        except json.JSONDecodeError as error:
            raise ContractFailure("LOGS-DOC-JSON", relative, "embedded error DSL is invalid") from error
        if canonical(definition) != fences[0]:
            raise ContractFailure("LOGS-DOC-CANONICAL", relative, "embedded error DSL is not canonical")
        documents[code] = validate_error_definition(
            definition,
            code=code,
            bundle=bundle,
            path=relative,
        )
        expected_title = f"# {code}: {documents[code]['title']}\n"
        if not text.startswith(expected_title):
            raise ContractFailure(
                "LOGS-DOC-TITLE",
                relative,
                "error heading does not match its filename and embedded DSL title",
            )
    declared = set(bundle["diagnosticCodes"])
    if set(documents) != declared:
        raise ContractFailure(
            "LOGS-DOC-CATALOG",
            "errors",
            "error page set differs from the diagnostic catalog",
        )
    return documents


def require_datetime(value: Any, path: str) -> None:
    if not isinstance(value, str) or DATETIME_RE.fullmatch(value) is None:
        raise ContractFailure("LOGS-EVENT-TIME", path, "event time is not normalized UTC")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise ContractFailure("LOGS-EVENT-TIME", path, "event time is invalid") from error
    if parsed.utcoffset() is None:
        raise ContractFailure("LOGS-EVENT-TIME", path, "event time has no timezone")


def calculate_event_hash(event: dict[str, Any]) -> str:
    payload = {key: copy.deepcopy(value) for key, value in event.items() if key != "eventHash"}
    return sha256_bytes(canonical(payload).encode("utf-8"))


def validate_event(
    event: Any,
    *,
    bundle: dict[str, Any],
    catalog: dict[str, dict[str, Any]],
    root: Path,
    path: str,
    stream: str,
    sequence: int,
    previous_hash: str,
) -> str:
    required = set(bundle["schemas"]["event"]["required"])
    value = exact_fields(event, required, rule="LOGS-EVENT-FIELDS", path=path)
    if value.get("schema") != "wellmanifest.logs/event/v1":
        raise ContractFailure("LOGS-EVENT-SCHEMA", path, "event schema is unsupported")
    if not isinstance(value.get("eventId"), str) or EVENT_ID_RE.fullmatch(value["eventId"]) is None:
        raise ContractFailure("LOGS-EVENT-ID", path, "event ID is invalid")
    if value.get("stream") != stream or STREAM_RE.fullmatch(stream) is None:
        raise ContractFailure("LOGS-EVENT-STREAM", path, "event stream differs from its file")
    observed_sequence = value.get("sequence")
    if (
        isinstance(observed_sequence, bool)
        or not isinstance(observed_sequence, int)
        or observed_sequence != sequence
    ):
        raise ContractFailure("LOGS-EVENT-SEQUENCE", path, "event sequence is not contiguous")
    vocabulary = bundle["vocabulary"]
    if value.get("eventType") not in vocabulary["eventTypes"]:
        raise ContractFailure("LOGS-EVENT-TYPE", path, "event type is invalid")
    if value.get("severity") not in vocabulary["severities"]:
        raise ContractFailure("LOGS-EVENT-SEVERITY", path, "event severity is invalid")
    if value.get("outcome") not in vocabulary["outcomes"]:
        raise ContractFailure("LOGS-EVENT-OUTCOME", path, "event outcome is invalid")
    require_datetime(value.get("occurredAt"), path)
    correlation = value.get("correlationId")
    causation = value.get("causationId")
    if not isinstance(correlation, str) or ID_RE.fullmatch(correlation) is None:
        raise ContractFailure("LOGS-EVENT-CORRELATION", path, "correlation ID is invalid")
    if causation is not None and (
        not isinstance(causation, str) or ID_RE.fullmatch(causation) is None
    ):
        raise ContractFailure("LOGS-EVENT-CAUSATION", path, "causation ID is invalid")
    producer = value.get("producer")
    subject = value.get("subjectRef")
    if (
        not isinstance(producer, str)
        or len(producer) > 128
        or ACTOR_RE.fullmatch(producer) is None
    ):
        raise ContractFailure("LOGS-EVENT-PRODUCER", path, "event producer is invalid")
    if (
        not isinstance(subject, str)
        or len(subject) > 160
        or SUBJECT_RE.fullmatch(subject) is None
    ):
        raise ContractFailure("LOGS-EVENT-SUBJECT", path, "event subject is invalid")
    code = value.get("code")
    if code is not None and (not isinstance(code, str) or code not in catalog):
        raise ContractFailure("LOGS-EVENT-CODE", path, "event code has no error definition")
    if value.get("rawOutputIncluded") is not False or value.get("secretMaterialIncluded") is not False:
        raise ContractFailure("LOGS-EVENT-SAFETY", path, "event safety flags must both be false")
    evidence = value.get("evidence")
    if not isinstance(evidence, list) or not 1 <= len(evidence) <= 16:
        raise ContractFailure("LOGS-EVENT-EVIDENCE", path, "event evidence list is invalid")
    seen_evidence: set[tuple[str, str]] = set()
    for item in evidence:
        evidence_item = exact_fields(
            item,
            {"path", "sha256"},
            rule="LOGS-EVENT-EVIDENCE",
            path=path,
        )
        evidence_path = evidence_item.get("path")
        evidence_sha = evidence_item.get("sha256")
        if (
            not isinstance(evidence_path, str)
            or len(evidence_path) > 240
            or not isinstance(evidence_sha, str)
        ):
            raise ContractFailure("LOGS-EVENT-EVIDENCE", path, "event evidence entry is invalid")
        file_path = confined_file(root, evidence_path, "LOGS-EVENT-EVIDENCE")
        if SHA_RE.fullmatch(evidence_sha) is None or sha256_file(file_path) != evidence_sha:
            raise ContractFailure("LOGS-EVENT-EVIDENCE", path, "event evidence digest differs")
        pair = (evidence_path, evidence_sha)
        if pair in seen_evidence:
            raise ContractFailure("LOGS-EVENT-EVIDENCE", path, "event evidence is duplicated")
        seen_evidence.add(pair)
    if value.get("previousHash") != previous_hash:
        raise ContractFailure("LOGS-EVENT-CHAIN", path, "event predecessor hash is invalid")
    event_hash = value.get("eventHash")
    if not isinstance(event_hash, str) or SHA_RE.fullmatch(event_hash) is None:
        raise ContractFailure("LOGS-EVENT-HASH", path, "event hash format is invalid")
    if calculate_event_hash(value) != event_hash:
        raise ContractFailure("LOGS-EVENT-HASH", path, "event hash differs from canonical bytes")
    return event_hash


def validate_streams(
    root: Path,
    bundle: dict[str, Any],
    catalog: dict[str, dict[str, Any]],
) -> tuple[int, int]:
    directory = root / "logs"
    if not directory.is_dir():
        raise ContractFailure("LOGS-STORE-DIRECTORY", "logs", "log directory is missing")
    unsupported = sorted(
        item.name
        for item in directory.iterdir()
        if not item.is_file() or item.suffix != ".jsonl"
    )
    if unsupported:
        raise ContractFailure(
            "LOGS-STORE-PATH",
            "logs",
            "log directory contains an unsupported entry",
        )
    streams = sorted(directory.glob("*.jsonl"))
    if not streams:
        raise ContractFailure("LOGS-STORE-EMPTY", "logs", "no event stream exists")
    event_ids: set[str] = set()
    events_checked = 0
    for file_path in streams:
        stream = file_path.stem
        relative = file_path.relative_to(root).as_posix()
        if STREAM_RE.fullmatch(stream) is None:
            raise ContractFailure("LOGS-STORE-PATH", relative, "stream filename is invalid")
        try:
            lines = file_path.read_bytes().splitlines(keepends=True)
        except OSError as error:
            raise ContractFailure("LOGS-STORE-READ", relative, "stream is unreadable") from error
        if not lines:
            raise ContractFailure("LOGS-STORE-EMPTY", relative, "stream contains no events")
        previous_hash = ZERO_HASH
        for sequence, line in enumerate(lines, start=1):
            line_path = f"{relative}:{sequence}"
            if not line.endswith(b"\n") or line in {b"\n", b"\r\n"}:
                raise ContractFailure(
                    "LOGS-EVENT-CANONICAL",
                    line_path,
                    "event line is blank or lacks a final newline",
                )
            try:
                event = json.loads(line.decode("utf-8"))
            except (UnicodeError, json.JSONDecodeError) as error:
                raise ContractFailure(
                    "LOGS-EVENT-JSON",
                    line_path,
                    "event line is not valid UTF-8 JSON",
                ) from error
            if canonical(event).encode("utf-8") + b"\n" != line:
                raise ContractFailure(
                    "LOGS-EVENT-CANONICAL",
                    line_path,
                    "event line is not canonical JSONL",
                )
            previous_hash = validate_event(
                event,
                bundle=bundle,
                catalog=catalog,
                root=root,
                path=line_path,
                stream=stream,
                sequence=sequence,
                previous_hash=previous_hash,
            )
            event_id = event["eventId"]
            if event_id in event_ids:
                raise ContractFailure("LOGS-EVENT-UNIQUE", line_path, "event ID is duplicated")
            event_ids.add(event_id)
            events_checked += 1
    return len(streams), events_checked


def finding(error: ContractFailure) -> Finding:
    return Finding(
        code=DIAGNOSTIC_CODE,
        rule=error.rule,
        severity="ERROR",
        path=error.path,
        message=error.message,
    )


def validate_repository(root: Path) -> dict[str, Any]:
    findings: list[Finding] = []
    streams_checked = 0
    events_checked = 0
    errors_checked = 0
    contract_sha = ""
    try:
        bundle, contract_sha = load_contract(root)
    except ContractFailure as error:
        findings.append(finding(error))
        return report(findings, contract_sha, streams_checked, events_checked, errors_checked)
    for action in (
        lambda: validate_proto(root, bundle),
    ):
        try:
            action()
        except ContractFailure as error:
            findings.append(finding(error))
    catalog: dict[str, dict[str, Any]] = {}
    try:
        catalog = load_error_catalog(root, bundle)
        errors_checked = len(catalog)
    except ContractFailure as error:
        findings.append(finding(error))
    if catalog:
        try:
            streams_checked, events_checked = validate_streams(root, bundle, catalog)
        except ContractFailure as error:
            findings.append(finding(error))
    return report(findings, contract_sha, streams_checked, events_checked, errors_checked)


def report(
    findings: list[Finding],
    contract_sha: str,
    streams_checked: int,
    events_checked: int,
    errors_checked: int,
) -> dict[str, Any]:
    return {
        "schema": "wellmanifest.logs/validation-report/v1",
        "valid": not findings,
        "contractSha256": contract_sha,
        "streamsChecked": streams_checked,
        "eventsChecked": events_checked,
        "errorDefinitionsChecked": errors_checked,
        "findings": [asdict(item) for item in findings],
    }


def validate_request(bundle: dict[str, Any], value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractFailure("LOGS-REQUEST-FIELDS", "request", "request must be an object")
    operation = value.get("operation")
    if operation == "inspect":
        request = exact_fields(
            value,
            {"schema", "operation", "processRef"},
            rule="LOGS-REQUEST-FIELDS",
            path="request",
        )
        expected_process = EXPECTED_PROCESSES["inspect"]
    elif operation == "plan_append":
        request = exact_fields(
            value,
            {
                "schema",
                "operation",
                "processRef",
                "stream",
                "expectedVersion",
                "eventRef",
                "eventSha256",
            },
            rule="LOGS-REQUEST-FIELDS",
            path="request",
        )
        expected_process = EXPECTED_PROCESSES["planAppend"]
        stream = request.get("stream")
        version = request.get("expectedVersion")
        event_ref = request.get("eventRef")
        event_sha = request.get("eventSha256")
        if not isinstance(stream, str) or STREAM_RE.fullmatch(stream) is None:
            raise ContractFailure("LOGS-REQUEST-STREAM", "request", "request stream is invalid")
        if isinstance(version, bool) or not isinstance(version, int) or not 0 <= version <= 9007199254740991:
            raise ContractFailure("LOGS-REQUEST-VERSION", "request", "expected version is invalid")
        if not isinstance(event_ref, str) or ARTIFACT_RE.fullmatch(event_ref) is None:
            raise ContractFailure("LOGS-REQUEST-ARTIFACT", "request", "event artifact reference is invalid")
        if not isinstance(event_sha, str) or SHA_RE.fullmatch(event_sha) is None:
            raise ContractFailure("LOGS-REQUEST-DIGEST", "request", "event artifact digest is invalid")
    else:
        raise ContractFailure(
            "LOGS-REQUEST-OPERATION",
            "request",
            "request operation is not inspect or propose-only plan_append",
        )
    if request.get("schema") != "wellmanifest.logs/request/v1":
        raise ContractFailure("LOGS-REQUEST-SCHEMA", "request", "request schema is unsupported")
    if request.get("processRef") != expected_process:
        raise ContractFailure("LOGS-REQUEST-PROCESS", "request", "request process does not match operation")
    if not isinstance(bundle.get("requestGbnf"), str):
        raise ContractFailure("LOGS-CONTRACT-GRAMMAR", "request", "request grammar is unavailable")
    return copy.deepcopy(request)


def copy_fixture(source: Path, destination: Path) -> None:
    for relative in (
        CONTRACT_PATH,
        Path("proto/wellmanifest/logs/v1/logs.proto"),
        Path(HELP_PATH),
        Path("logs/control.jsonl"),
    ):
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, target)


def rewrite_event(path: Path, mutate: Any) -> None:
    event = json.loads(path.read_text("utf-8"))
    mutate(event)
    event["eventHash"] = calculate_event_hash(event)
    path.write_text(canonical(event) + "\n", encoding="utf-8")


def assert_invalid(root: Path, rule: str) -> None:
    result = validate_repository(root)
    rules = {item["rule"] for item in result["findings"]}
    if result["valid"] or rule not in rules:
        raise AssertionError(f"expected {rule}, observed {sorted(rules)}")


def run_self_test(source: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="wellmanifest-logs-") as temporary:
        baseline = Path(temporary) / "baseline"
        copy_fixture(source, baseline)
        valid = validate_repository(baseline)
        if not valid["valid"]:
            raise AssertionError(f"baseline failed: {valid['findings']}")

        extra = Path(temporary) / "extra"
        copy_fixture(source, extra)
        rewrite_event(extra / "logs/control.jsonl", lambda event: event.update({"payload": {}}))
        assert_invalid(extra, "LOGS-EVENT-FIELDS")

        unsafe = Path(temporary) / "unsafe"
        copy_fixture(source, unsafe)
        rewrite_event(
            unsafe / "logs/control.jsonl",
            lambda event: event.update({"secretMaterialIncluded": True}),
        )
        assert_invalid(unsafe, "LOGS-EVENT-SAFETY")

        chain = Path(temporary) / "chain"
        copy_fixture(source, chain)
        rewrite_event(
            chain / "logs/control.jsonl",
            lambda event: event.update({"previousHash": "1" * 64}),
        )
        assert_invalid(chain, "LOGS-EVENT-CHAIN")

        evidence = Path(temporary) / "evidence"
        copy_fixture(source, evidence)
        rewrite_event(
            evidence / "logs/control.jsonl",
            lambda event: event["evidence"][0].update({"sha256": "2" * 64}),
        )
        assert_invalid(evidence, "LOGS-EVENT-EVIDENCE")

        undocumented = Path(temporary) / "undocumented"
        copy_fixture(source, undocumented)
        rewrite_event(
            undocumented / "logs/control.jsonl",
            lambda event: event.update({"code": "LOGS-NOT-DOCUMENTED"}),
        )
        assert_invalid(undocumented, "LOGS-EVENT-CODE")

        timestamp = Path(temporary) / "timestamp"
        copy_fixture(source, timestamp)
        rewrite_event(
            timestamp / "logs/control.jsonl",
            lambda event: event.update({"occurredAt": "2026-08-12 18:20:00Z"}),
        )
        assert_invalid(timestamp, "LOGS-EVENT-TIME")

        docs = Path(temporary) / "docs"
        copy_fixture(source, docs)
        page = docs / HELP_PATH
        page.write_text(page.read_text("utf-8").replace("## Do not\n", "## Unsafe shortcuts\n"), "utf-8")
        assert_invalid(docs, "LOGS-DOC-SECTIONS")

        title = Path(temporary) / "title"
        copy_fixture(source, title)
        page = title / HELP_PATH
        page.write_text(
            page.read_text("utf-8").replace("# LOGS-VALIDATION-001:", "# LOGS-WRONG:"),
            "utf-8",
        )
        assert_invalid(title, "LOGS-DOC-TITLE")

        grammar = Path(temporary) / "grammar"
        copy_fixture(source, grammar)
        contract = read_json(
            grammar / CONTRACT_PATH,
            rule="SELF-TEST",
            label="self-test contract",
        )
        contract["requestGbnf"] = contract["requestGbnf"].replace("plan_append", "append")
        (grammar / CONTRACT_PATH).write_text(json.dumps(contract, indent=2) + "\n", "utf-8")
        assert_invalid(grammar, "LOGS-CONTRACT-GRAMMAR")

        bundle, _ = load_contract(source)
        inspect = {
            "schema": "wellmanifest.logs/request/v1",
            "operation": "inspect",
            "processRef": EXPECTED_PROCESSES["inspect"],
        }
        validate_request(bundle, inspect)
        plan = {
            "schema": "wellmanifest.logs/request/v1",
            "operation": "plan_append",
            "processRef": EXPECTED_PROCESSES["planAppend"],
            "stream": "control",
            "expectedVersion": 1,
            "eventRef": "artifact://wellmanifest.dev/logs/event/r1",
            "eventSha256": "1" * 64,
        }
        validate_request(bundle, plan)
        for invalid in (
            {**inspect, "grant_ref": "grant:forged"},
            {**inspect, "operation": "append"},
        ):
            try:
                validate_request(bundle, invalid)
            except ContractFailure:
                pass
            else:
                raise AssertionError("authority-bearing request was accepted")
    print("logs conformance self-test: PASS (11 adversarial checks)")


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
    subparsers.add_parser("self-test", help="run positive and adversarial conformance")
    return parser


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
    try:
        bundle, _ = load_contract(root)
        value = read_json(args.request, rule="LOGS-REQUEST-JSON", label="request")
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
