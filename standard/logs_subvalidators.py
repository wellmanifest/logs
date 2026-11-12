"""Continuity causal chain and operational diagnostic sub-validators."""

from __future__ import annotations

import ipaddress
from typing import Any
from urllib.parse import urlsplit

from standard import logs_primitives as _p

CONTINUITY_EVENT_TYPES = (
    "agent.session_started",
    "agent.intent_compiled",
    "agent.tool_requested",
    "agent.tool_completed",
    "git.slice_checkpointed",
    "work.split_requested",
    "work.split_materialized",
    "git.commit_created",
    "git.push_started",
    "git.push_completed",
    "agent.resume_observed",
    "agent.resume_decided",
    "agent.snapshot_recorded",
)
CONTINUITY_SCHEMA_NAMES = {
    "agent.session_started": "sessionStarted",
    "agent.intent_compiled": "intentCompiled",
    "agent.tool_requested": "toolRequested",
    "agent.tool_completed": "toolCompleted",
    "git.slice_checkpointed": "sliceCheckpointed",
    "work.split_requested": "splitRequested",
    "work.split_materialized": "splitMaterialized",
    "git.commit_created": "commitCreated",
    "git.push_started": "pushStarted",
    "git.push_completed": "pushCompleted",
    "agent.resume_observed": "resumeObserved",
    "agent.resume_decided": "resumeDecided",
    "agent.snapshot_recorded": "snapshotRecorded",
}
CONTINUITY_FIELDS = {
    "agent.session_started": {"sessionDigest"},
    "agent.intent_compiled": {"sourceDigest", "intentDigest", "compilerReceiptRef"},
    "agent.tool_requested": {"intentDigest", "requestDigest"},
    "agent.tool_completed": {"requestDigest", "resultDigest", "executionReceiptRef"},
    "git.slice_checkpointed": {
        "sliceDigest",
        "validationDigests",
        "validationReceiptRefs",
    },
    "work.split_requested": {"parentWorkDigest", "splitPlanDigest"},
    "work.split_materialized": {
        "splitPlanDigest",
        "acceptedWorkDigests",
        "splitReceiptRef",
    },
    "git.commit_created": {"sliceDigest", "commitDigest", "commitReceiptRef"},
    "git.push_started": {"commitDigest", "pushPlanDigest", "pushStartReceiptRef"},
    "git.push_completed": {
        "commitDigest",
        "pushPlanDigest",
        "remoteStateDigest",
        "pushReceiptRef",
    },
    "agent.resume_observed": {
        "snapshotDigest",
        "expectedStateDigest",
        "observedStateDigest",
        "observationDigest",
        "observationReceiptRef",
    },
    "agent.resume_decided": {
        "observationDigest",
        "decisionDigest",
        "decisionReceiptRef",
    },
    "agent.snapshot_recorded": {"snapshotDigest", "stateDigest", "snapshotReceiptRef"},
}
CAUSAL_PARENT_TYPES = {
    "agent.intent_compiled": "agent.session_started",
    "agent.tool_requested": "agent.intent_compiled",
    "agent.tool_completed": "agent.tool_requested",
    "work.split_materialized": "work.split_requested",
    "git.commit_created": "git.slice_checkpointed",
    "git.push_started": "git.commit_created",
    "git.push_completed": "git.push_started",
    "agent.resume_observed": "agent.snapshot_recorded",
    "agent.resume_decided": "agent.resume_observed",
}


def validate_continuity(
    event: dict[str, Any],
    *,
    prior_events: dict[str, dict[str, Any]],
    path: str,
) -> None:
    event_type = event["eventType"]
    if event_type not in CONTINUITY_EVENT_TYPES:
        if "continuity" in event:
            raise _p.ContractFailure(
                "LOGS-EVENT-CONTINUITY",
                path,
                "continuity payload is only valid for a declared continuity event type",
            )
        return
    if "continuity" not in event:
        raise _p.ContractFailure(
            "LOGS-EVENT-CONTINUITY",
            path,
            "declared continuity event is missing its typed payload",
        )
    payload = _p.exact_fields(
        event["continuity"],
        CONTINUITY_FIELDS[event_type],
        rule="LOGS-EVENT-CONTINUITY",
        path=path,
    )
    for name, item in payload.items():
        if name.endswith("Digests"):
            minimum = 2 if name == "acceptedWorkDigests" else 1
            if (
                not isinstance(item, list)
                or not minimum <= len(item) <= 16
                or len(item) != len(set(item))
                or any(
                    not isinstance(v, str) or _p.SHA_RE.fullmatch(v) is None
                    for v in item
                )
            ):
                raise _p.ContractFailure(
                    "LOGS-EVENT-CONTINUITY", path, "continuity digest list is invalid"
                )
        elif name.endswith("ReceiptRefs"):
            if (
                not isinstance(item, list)
                or not 1 <= len(item) <= 16
                or len(item) != len(set(item))
                or any(
                    not isinstance(v, str)
                    or len(v) > 160
                    or _p.RECEIPT_RE.fullmatch(v) is None
                    for v in item
                )
            ):
                raise _p.ContractFailure(
                    "LOGS-EVENT-CONTINUITY",
                    path,
                    "continuity receipt reference list is invalid",
                )
        elif name.endswith("ReceiptRef"):
            if (
                not isinstance(item, str)
                or len(item) > 160
                or _p.RECEIPT_RE.fullmatch(item) is None
            ):
                raise _p.ContractFailure(
                    "LOGS-EVENT-CONTINUITY",
                    path,
                    "continuity receipt reference is invalid",
                )
        elif not isinstance(item, str) or _p.SHA_RE.fullmatch(item) is None:
            raise _p.ContractFailure(
                "LOGS-EVENT-CONTINUITY", path, "continuity digest is invalid"
            )

    causation = event["causationId"]
    if event_type == "agent.session_started":
        if causation is not None:
            raise _p.ContractFailure(
                "LOGS-EVENT-CONTINUITY-CAUSE",
                path,
                "a session start must be the continuity correlation root",
            )
        return
    cause = prior_events.get(causation) if isinstance(causation, str) else None
    if cause is None or cause.get("correlationId") != event["correlationId"]:
        raise _p.ContractFailure(
            "LOGS-EVENT-CONTINUITY-CAUSE",
            path,
            "continuity causation must reference a prior event in the same correlation",
        )
    expected_parent_type = CAUSAL_PARENT_TYPES.get(event_type)
    if (
        expected_parent_type is not None
        and cause.get("eventType") != expected_parent_type
    ):
        raise _p.ContractFailure(
            "LOGS-EVENT-CONTINUITY-CAUSE",
            path,
            "continuity event references the wrong causal event type",
        )
    cause_payload = cause.get("continuity", {})
    paired_digest_fields = {
        "agent.tool_requested": ("intentDigest",),
        "agent.tool_completed": ("requestDigest",),
        "work.split_materialized": ("splitPlanDigest",),
        "git.commit_created": ("sliceDigest",),
        "git.push_started": ("commitDigest",),
        "git.push_completed": ("commitDigest", "pushPlanDigest"),
        "agent.resume_decided": ("observationDigest",),
    }
    paired_fields = paired_digest_fields.get(event_type, ())
    if any(payload[field] != cause_payload.get(field) for field in paired_fields):
        raise _p.ContractFailure(
            "LOGS-EVENT-CONTINUITY-DIGEST",
            path,
            "continuity event digest differs from its causal boundary",
        )
    if event_type == "agent.resume_observed" and (
        payload["snapshotDigest"] != cause_payload.get("snapshotDigest")
        or payload["expectedStateDigest"] != cause_payload.get("stateDigest")
    ):
        raise _p.ContractFailure(
            "LOGS-EVENT-CONTINUITY-DIGEST",
            path,
            "resume observation does not match its recorded snapshot",
        )
    if event_type == "agent.resume_decided":
        diverged = cause_payload.get("observedStateDigest") != cause_payload.get(
            "expectedStateDigest"
        )
        expected_outcome = "REJECTED" if diverged else "ACCEPTED"
        expected_state = "diverged" if diverged else "resume"
        if (
            event.get("outcome") != expected_outcome
            or event.get("subjectState") != expected_state
        ):
            raise _p.ContractFailure(
                "LOGS-EVENT-CONTINUITY-DECISION",
                path,
                "resume decision does not match the observed snapshot state",
            )


def _validate_endpoint_origin(endpoint: str, path: str) -> None:
    if not endpoint.startswith(("http://", "https://")):
        return
    try:
        parsed = urlsplit(endpoint)
        port = parsed.port
    except ValueError as error:
        raise _p.ContractFailure(
            "LOGS-EVENT-DIAGNOSTIC",
            path,
            "endpoint reference is not a secret-free origin or opaque reference",
        ) from error
    if (
        "@" in parsed.netloc
        or parsed.path
        or parsed.query
        or parsed.fragment
        or (port is not None and not 1 <= port <= 65535)
    ):
        raise _p.ContractFailure(
            "LOGS-EVENT-DIAGNOSTIC",
            path,
            "endpoint reference is not a secret-free origin or opaque reference",
        )
    hostname = parsed.hostname
    if not hostname:
        raise _p.ContractFailure(
            "LOGS-EVENT-DIAGNOSTIC",
            path,
            "endpoint reference is not a secret-free origin or opaque reference",
        )
    if parsed.netloc.startswith("["):
        try:
            addr = ipaddress.ip_address(hostname)
        except ValueError as error:
            raise _p.ContractFailure(
                "LOGS-EVENT-DIAGNOSTIC",
                path,
                "endpoint reference is not a secret-free origin or opaque reference",
            ) from error
        if addr.version != 6:
            raise _p.ContractFailure(
                "LOGS-EVENT-DIAGNOSTIC",
                path,
                "endpoint reference is not a secret-free origin or opaque reference",
            )
    elif ".." in hostname or any(
        label.startswith("-") or label.endswith("-") for label in hostname.split(".")
    ):
        raise _p.ContractFailure(
            "LOGS-EVENT-DIAGNOSTIC",
            path,
            "endpoint reference is not a secret-free origin or opaque reference",
        )


def validate_diagnostic(value: Any, path: str) -> None:
    fields = {
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
    diagnostic = _p.exact_fields(value, fields, rule="LOGS-EVENT-DIAGNOSTIC", path=path)
    for name in ("phase", "status"):
        item = diagnostic.get(name)
        if (
            not isinstance(item, str)
            or len(item) > 32
            or _p.STATE_RE.fullmatch(item) is None
        ):
            raise _p.ContractFailure(
                "LOGS-EVENT-DIAGNOSTIC", path, f"diagnostic {name} is invalid"
            )
    if not isinstance(diagnostic.get("retryable"), bool):
        raise _p.ContractFailure(
            "LOGS-EVENT-DIAGNOSTIC", path, "diagnostic retryability is invalid"
        )
    attempt = diagnostic.get("attempt")
    attempts = diagnostic.get("attempts")
    if (
        isinstance(attempt, bool)
        or not isinstance(attempt, int)
        or isinstance(attempts, bool)
        or not isinstance(attempts, int)
        or not 1 <= attempt <= attempts <= 1000
    ):
        raise _p.ContractFailure(
            "LOGS-EVENT-DIAGNOSTIC", path, "diagnostic attempt counters are invalid"
        )
    duration = diagnostic.get("durationMs")
    if (
        isinstance(duration, bool)
        or not isinstance(duration, int)
        or not 0 <= duration <= 604800000
    ):
        raise _p.ContractFailure(
            "LOGS-EVENT-DIAGNOSTIC", path, "diagnostic duration is invalid"
        )
    endpoint = diagnostic.get("endpointRef")
    if endpoint is not None:
        if (
            not isinstance(endpoint, str)
            or len(endpoint) > 255
            or _p.ENDPOINT_REF_RE.fullmatch(endpoint) is None
        ):
            raise _p.ContractFailure(
                "LOGS-EVENT-DIAGNOSTIC",
                path,
                "endpoint reference is not a secret-free origin or opaque reference",
            )
        _validate_endpoint_origin(endpoint, path)
    transport = diagnostic.get("transportCode")
    if transport is not None and (
        not isinstance(transport, str)
        or _p.TRANSPORT_CODE_RE.fullmatch(transport) is None
    ):
        raise _p.ContractFailure(
            "LOGS-EVENT-DIAGNOSTIC", path, "diagnostic transport code is invalid"
        )
    http_status = diagnostic.get("httpStatus")
    if http_status is not None and (
        isinstance(http_status, bool)
        or not isinstance(http_status, int)
        or not 100 <= http_status <= 599
    ):
        raise _p.ContractFailure(
            "LOGS-EVENT-DIAGNOSTIC", path, "diagnostic HTTP status is invalid"
        )
    remediation_refs = diagnostic.get("remediationRefs")
    if (
        not isinstance(remediation_refs, list)
        or len(remediation_refs) > 8
        or len(remediation_refs) != len(set(remediation_refs))
        or any(
            not isinstance(item, str)
            or len(item) > 200
            or _p.REMEDIATION_REF_RE.fullmatch(item) is None
            for item in remediation_refs
        )
    ):
        raise _p.ContractFailure(
            "LOGS-EVENT-DIAGNOSTIC",
            path,
            "diagnostic remediation references are invalid",
        )
    trace_id = diagnostic.get("traceId")
    span_id = diagnostic.get("spanId")
    if trace_id is not None and (
        not isinstance(trace_id, str) or _p.TRACE_ID_RE.fullmatch(trace_id) is None
    ):
        raise _p.ContractFailure(
            "LOGS-EVENT-DIAGNOSTIC", path, "diagnostic trace ID is invalid"
        )
    if span_id is not None and (
        not isinstance(span_id, str) or _p.SPAN_ID_RE.fullmatch(span_id) is None
    ):
        raise _p.ContractFailure(
            "LOGS-EVENT-DIAGNOSTIC", path, "diagnostic span ID is invalid"
        )
