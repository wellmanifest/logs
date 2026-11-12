"""Contract bundle and Protobuf projection validators."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from standard import logs_primitives as _p
from standard import logs_subvalidators as _s

EXPECTED_PROTO_MESSAGES = (
    "EvidenceRef",
    "DiagnosticContext",
    "AgentSessionStarted",
    "AgentIntentCompiled",
    "AgentToolRequested",
    "AgentToolCompleted",
    "GitSliceCheckpointed",
    "WorkSplitRequested",
    "WorkSplitMaterialized",
    "GitCommitCreated",
    "GitPushStarted",
    "GitPushCompleted",
    "AgentResumeObserved",
    "AgentResumeDecided",
    "AgentSnapshotRecorded",
    "ContinuityPayload",
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
EXPECTED_CONTINUITY_PROTO_FIELDS = (
    "string session_digest = 1;",
    "string source_digest = 1;",
    "string intent_digest = 2;",
    "string compiler_receipt_ref = 3;",
    "string intent_digest = 1;",
    "string request_digest = 2;",
    "string request_digest = 1;",
    "string execution_receipt_ref = 3;",
    "repeated string validation_digests = 2;",
    "repeated string validation_receipt_refs = 3;",
    "string parent_work_digest = 1;",
    "string split_plan_digest = 2;",
    "repeated string accepted_work_digests = 2;",
    "string split_receipt_ref = 3;",
    "string commit_receipt_ref = 3;",
    "string push_plan_digest = 2;",
    "string push_start_receipt_ref = 3;",
    "string remote_state_digest = 3;",
    "string push_receipt_ref = 4;",
    "string snapshot_digest = 1;",
    "string expected_state_digest = 2;",
    "string observed_state_digest = 3;",
    "string observation_digest = 4;",
    "string observation_receipt_ref = 5;",
    "string observation_digest = 1;",
    "string decision_digest = 2;",
    "string decision_receipt_ref = 3;",
    "string state_digest = 2;",
    "string snapshot_receipt_ref = 3;",
    "string slice_digest = 1;",
    "string commit_digest = 2;",
    "string commit_digest = 1;",
    "AgentSessionStarted agent_session_started = 1;",
    "AgentIntentCompiled agent_intent_compiled = 2;",
    "AgentToolRequested agent_tool_requested = 3;",
    "AgentToolCompleted agent_tool_completed = 4;",
    "GitSliceCheckpointed git_slice_checkpointed = 5;",
    "WorkSplitRequested work_split_requested = 6;",
    "WorkSplitMaterialized work_split_materialized = 7;",
    "GitCommitCreated git_commit_created = 8;",
    "GitPushStarted git_push_started = 9;",
    "GitPushCompleted git_push_completed = 10;",
    "AgentResumeObserved agent_resume_observed = 11;",
    "AgentResumeDecided agent_resume_decided = 12;",
    "AgentSnapshotRecorded agent_snapshot_recorded = 13;",
)


def _assert_closed_objects(value: Any, path: str = "schemas") -> None:
    stack: list[tuple[Any, str, int]] = [(value, path, 0)]
    while stack:
        current, current_path, depth = stack.pop()
        if depth > _p.MAX_JSON_DEPTH:
            raise _p.ContractFailure(
                "LOGS-CONTRACT-CLOSED",
                _p.CONTRACT_PATH.as_posix(),
                "schema nesting exceeds bounded depth",
            )
        if isinstance(current, dict):
            if (
                current.get("type") == "object"
                and current.get("additionalProperties") is not False
            ):
                raise _p.ContractFailure(
                    "LOGS-CONTRACT-CLOSED",
                    _p.CONTRACT_PATH.as_posix(),
                    f"object schema at {current_path} is not closed",
                )
            for key, child in current.items():
                stack.append((child, f"{current_path}.{key}", depth + 1))
        elif isinstance(current, list):
            for index, child in enumerate(current):
                stack.append((child, f"{current_path}[{index}]", depth + 1))


def load_contract(root: Path) -> tuple[dict[str, Any], str]:
    path = _p.confined_file(root, _p.CONTRACT_PATH.as_posix(), "LOGS-CONTRACT-JSON")
    raw = _p.read_bounded_regular_bytes(
        path,
        max_bytes=_p.MAX_CONTRACT_BYTES,
        rule="LOGS-CONTRACT-JSON",
        label="contract bundle",
        display_path=_p.CONTRACT_PATH.as_posix(),
    )
    try:
        decoded = raw.decode("utf-8")
    except UnicodeError as error:
        raise _p.ContractFailure(
            "LOGS-CONTRACT-JSON",
            _p.CONTRACT_PATH.as_posix(),
            "contract bundle is unreadable or invalid",
        ) from error
    bundle = _p.exact_fields(
        _p.strict_json_loads(
            decoded,
            rule="LOGS-CONTRACT-JSON",
            path=_p.CONTRACT_PATH.as_posix(),
            label="contract bundle",
        ),
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
        path=_p.CONTRACT_PATH.as_posix(),
    )
    constants = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "schema": "wellmanifest.logs/contract-bundle/v1",
        "version": "0.5.0",
        "canonical": "protobuf",
        "protobufPath": "proto/v0.5/wellmanifest/logs/v1/logs.proto",
        "projection": "canonical-jsonl",
        "hashProfile": "wellmanifest-canonical-json-v1+SHA-256",
    }
    if any(bundle.get(key) != expected for key, expected in constants.items()):
        raise _p.ContractFailure(
            "LOGS-CONTRACT-IDENTITY",
            _p.CONTRACT_PATH.as_posix(),
            "contract identity or canonicalization profile changed",
        )
    if bundle.get("processes") != _p.EXPECTED_PROCESSES:
        raise _p.ContractFailure(
            "LOGS-CONTRACT-PROCESS",
            _p.CONTRACT_PATH.as_posix(),
            "POA process registry is incomplete or changed",
        )
    if bundle.get("diagnosticCodes") != [_p.DIAGNOSTIC_CODE]:
        raise _p.ContractFailure(
            "LOGS-CONTRACT-CATALOG",
            _p.CONTRACT_PATH.as_posix(),
            "diagnostic catalog does not match the v1 runtime",
        )
    schemas = _p.exact_fields(
        bundle.get("schemas"),
        {"evidence", "event", "error", "request"},
        rule="LOGS-CONTRACT-SCHEMAS",
        path=_p.CONTRACT_PATH.as_posix(),
    )
    vocabulary = _p.exact_fields(
        bundle.get("vocabulary"),
        {
            "severities",
            "eventTypes",
            "continuityEventTypes",
            "outcomes",
            "errorCategories",
            "reservedErrorNamespaces",
            "modes",
        },
        rule="LOGS-CONTRACT-VOCABULARY",
        path=_p.CONTRACT_PATH.as_posix(),
    )
    for key in vocabulary:
        values = vocabulary[key]
        if (
            not isinstance(values, list)
            or not values
            or any(not isinstance(v, str) for v in values)
            or len(values) != len(set(values))
        ):
            raise _p.ContractFailure(
                "LOGS-CONTRACT-VOCABULARY",
                _p.CONTRACT_PATH.as_posix(),
                "contract vocabulary must contain nonempty unique string arrays",
            )
    if vocabulary["errorCategories"] != sorted(vocabulary["errorCategories"]) or any(
        _p.NAMESPACE_RE.fullmatch(item) is None
        for item in vocabulary["reservedErrorNamespaces"]
    ):
        raise _p.ContractFailure(
            "LOGS-CONTRACT-VOCABULARY",
            _p.CONTRACT_PATH.as_posix(),
            "unordered categories or invalid reserved error namespaces",
        )
    if vocabulary["continuityEventTypes"] != list(_s.CONTINUITY_EVENT_TYPES):
        raise _p.ContractFailure(
            "LOGS-CONTRACT-CONTINUITY",
            _p.CONTRACT_PATH.as_posix(),
            "continuity event vocabulary is incomplete or reordered",
        )
    _validate_contract_event_schema(schemas, vocabulary)
    _assert_closed_objects(schemas)
    if bundle.get("requestGbnf") != _p.EXPECTED_REQUEST_GBNF:
        raise _p.ContractFailure(
            "LOGS-CONTRACT-GRAMMAR",
            _p.CONTRACT_PATH.as_posix(),
            "request grammar differs from the closed propose-only compatibility unit",
        )
    return bundle, _p.sha256_bytes(raw)


def _validate_contract_event_schema(
    schemas: dict[str, Any],
    vocabulary: dict[str, Any],
) -> None:
    event_properties = schemas["event"].get("properties", {})
    if event_properties.get("severity", {}).get("enum") != vocabulary["severities"]:
        raise _p.ContractFailure(
            "LOGS-CONTRACT-VOCABULARY",
            _p.CONTRACT_PATH.as_posix(),
            "event severity schema differs from vocabulary",
        )
    event_type_union = event_properties.get("eventType", {}).get("oneOf")
    if (
        not isinstance(event_type_union, list)
        or len(event_type_union) != 2
        or event_type_union[0].get("enum") != vocabulary["eventTypes"]
        or event_type_union[1].get("pattern") != _p.DOMAIN_TYPE_RE.pattern
    ):
        raise _p.ContractFailure(
            "LOGS-CONTRACT-VOCABULARY",
            _p.CONTRACT_PATH.as_posix(),
            "event type schema differs from vocabulary",
        )
    if event_properties.get("mode", {}).get("enum") != vocabulary["modes"]:
        raise _p.ContractFailure(
            "LOGS-CONTRACT-VOCABULARY",
            _p.CONTRACT_PATH.as_posix(),
            "event mode schema differs from vocabulary",
        )
    if event_properties.get("outcome", {}).get("enum") != vocabulary["outcomes"]:
        raise _p.ContractFailure(
            "LOGS-CONTRACT-VOCABULARY",
            _p.CONTRACT_PATH.as_posix(),
            "event outcome schema differs from vocabulary",
        )
    diagnostic_fields = {
        "phase",
        "status",
        "retryable",
        "attempt",
        "attempts",
        "durationMs",
        "endpointRef",
        "transportCode",
        "httpStatus",
        "remediationRefs",
        "traceId",
        "spanId",
    }
    diagnostic_schema = schemas["event"].get("$defs", {}).get("diagnostic", {})
    if (
        "diagnostic" in schemas["event"].get("required", [])
        or event_properties.get("diagnostic") != {"$ref": "#/$defs/diagnostic"}
        or set(diagnostic_schema.get("required", [])) != diagnostic_fields
        or set(diagnostic_schema.get("properties", {})) != diagnostic_fields
    ):
        raise _p.ContractFailure(
            "LOGS-CONTRACT-DIAGNOSTIC",
            _p.CONTRACT_PATH.as_posix(),
            "optional operational diagnostic schema is incomplete or no longer closed",
        )
    event_definitions = schemas["event"].get("$defs", {})
    continuity_refs = event_properties.get("continuity", {}).get("oneOf")
    expected_refs = [
        {"$ref": f"#/$defs/{_s.CONTINUITY_SCHEMA_NAMES[event_type]}"}
        for event_type in _s.CONTINUITY_EVENT_TYPES
    ]
    if (
        "continuity" in schemas["event"].get("required", [])
        or continuity_refs != expected_refs
        or any(
            set(
                event_definitions.get(_s.CONTINUITY_SCHEMA_NAMES[et], {}).get(
                    "required", []
                )
            )
            != fields
            or set(
                event_definitions.get(_s.CONTINUITY_SCHEMA_NAMES[et], {}).get(
                    "properties", {}
                )
            )
            != fields
            for et, fields in _s.CONTINUITY_FIELDS.items()
        )
    ):
        raise _p.ContractFailure(
            "LOGS-CONTRACT-CONTINUITY",
            _p.CONTRACT_PATH.as_posix(),
            "continuity payload variants are incomplete or no longer closed",
        )
    continuity_conditions = schemas["event"].get("allOf")
    conditioned_types = []
    if isinstance(continuity_conditions, list):
        for condition in continuity_conditions:
            et_schema = (
                condition.get("if", {}).get("properties", {}).get("eventType", {})
            )
            if "const" in et_schema:
                conditioned_types.append(et_schema["const"])
    if conditioned_types != list(_s.CONTINUITY_EVENT_TYPES):
        raise _p.ContractFailure(
            "LOGS-CONTRACT-CONTINUITY",
            _p.CONTRACT_PATH.as_posix(),
            "continuity event-to-payload conditions are incomplete or reordered",
        )
    error_properties = schemas["error"].get("properties", {})
    if (
        error_properties.get("category", {}).get("enum")
        != vocabulary["errorCategories"]
    ):
        raise _p.ContractFailure(
            "LOGS-CONTRACT-VOCABULARY",
            _p.CONTRACT_PATH.as_posix(),
            "error category schema differs from vocabulary",
        )


def validate_proto(root: Path, bundle: dict[str, Any]) -> None:
    relative = Path(bundle["protobufPath"])
    path = _p.confined_file(root, relative.as_posix(), "LOGS-PROTO-PATH")
    raw = _p.read_bounded_regular_bytes(
        path,
        max_bytes=_p.MAX_CONTRACT_BYTES,
        rule="LOGS-PROTO-READ",
        label="Protobuf contract",
        display_path=relative.as_posix(),
    )
    try:
        text = raw.decode("utf-8")
    except UnicodeError as error:
        raise _p.ContractFailure(
            "LOGS-PROTO-READ",
            relative.as_posix(),
            "Protobuf contract is unreadable",
        ) from error
    required = [
        'syntax = "proto3";',
        "package wellmanifest.logs.v1;",
        "service LogsControlService {",
        "oneof event {",
        "optional ContinuityPayload continuity = 25;",
        *(f"message {name} {{" for name in EXPECTED_PROTO_MESSAGES),
        *EXPECTED_CONTINUITY_PROTO_FIELDS,
        *EXPECTED_RPCS,
    ]
    vocabulary = bundle["vocabulary"]
    required.extend(f"SEVERITY_{value}" for value in vocabulary["severities"])
    required.extend(f"EVENT_TYPE_{value.upper()}" for value in vocabulary["eventTypes"])
    required.extend(f"OUTCOME_{value}" for value in vocabulary["outcomes"])
    required.extend(f"MODE_{value}" for value in vocabulary["modes"])
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
        raise _p.ContractFailure(
            "LOGS-PROTO-COMPLETE",
            relative.as_posix(),
            "Protobuf messages, RPCs or bounded vocabulary are incomplete",
        )
