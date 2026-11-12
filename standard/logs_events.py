"""Event envelope, propose-only request, and JSONL stream validators."""

from __future__ import annotations

import copy
import stat
from pathlib import Path
from typing import Any

from standard import logs_adoption as _a
from standard import logs_contract as _c
from standard import logs_primitives as _p
from standard import logs_subvalidators as _s


def calculate_event_hash(event: dict[str, Any]) -> str:
    payload = {
        key: copy.deepcopy(value) for key, value in event.items() if key != "eventHash"
    }
    return _p.sha256_bytes(_p.canonical(payload).encode("utf-8"))


def validate_request(bundle: dict[str, Any], value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _p.ContractFailure(
            "LOGS-REQUEST-FIELDS", "request", "request must be an object"
        )
    operation = value.get("operation")
    if operation == "inspect":
        request = _p.exact_fields(
            value,
            {"schema", "operation", "processRef"},
            rule="LOGS-REQUEST-FIELDS",
            path="request",
        )
        expected_process = _p.EXPECTED_PROCESSES["inspect"]
    elif operation == "plan_append":
        request = _p.exact_fields(
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
        expected_process = _p.EXPECTED_PROCESSES["planAppend"]
        stream = request.get("stream")
        version = request.get("expectedVersion")
        event_ref = request.get("eventRef")
        event_sha = request.get("eventSha256")
        if not isinstance(stream, str) or _p.STREAM_RE.fullmatch(stream) is None:
            raise _p.ContractFailure(
                "LOGS-REQUEST-STREAM", "request", "request stream is invalid"
            )
        if (
            isinstance(version, bool)
            or not isinstance(version, int)
            or not 0 <= version <= 9007199254740991
        ):
            raise _p.ContractFailure(
                "LOGS-REQUEST-VERSION", "request", "expected version is invalid"
            )
        if (
            not isinstance(event_ref, str)
            or _p.ARTIFACT_RE.fullmatch(event_ref) is None
        ):
            raise _p.ContractFailure(
                "LOGS-REQUEST-ARTIFACT",
                "request",
                "event artifact reference is invalid",
            )
        if not isinstance(event_sha, str) or _p.SHA_RE.fullmatch(event_sha) is None:
            raise _p.ContractFailure(
                "LOGS-REQUEST-DIGEST", "request", "event artifact digest is invalid"
            )
    else:
        raise _p.ContractFailure(
            "LOGS-REQUEST-OPERATION",
            "request",
            "request operation is not inspect or propose-only plan_append",
        )
    if request.get("schema") != "wellmanifest.logs/request/v1":
        raise _p.ContractFailure(
            "LOGS-REQUEST-SCHEMA", "request", "request schema is unsupported"
        )
    if request.get("processRef") != expected_process:
        raise _p.ContractFailure(
            "LOGS-REQUEST-PROCESS",
            "request",
            "request process does not match operation",
        )
    if not isinstance(bundle.get("requestGbnf"), str):
        raise _p.ContractFailure(
            "LOGS-CONTRACT-GRAMMAR", "request", "request grammar is unavailable"
        )
    return copy.deepcopy(request)


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
    prior_events: dict[str, dict[str, Any]],
) -> str:
    event_schema = bundle["schemas"]["event"]
    required = set(event_schema["required"])
    allowed = set(event_schema["properties"])
    if not isinstance(event, dict):
        raise _p.ContractFailure(
            "LOGS-EVENT-FIELDS", path, "document must be an object"
        )
    observed = set(event)
    if not required.issubset(observed) or not observed.issubset(allowed):
        raise _p.ContractFailure(
            "LOGS-EVENT-FIELDS",
            path,
            "document fields do not match the closed contract",
        )
    value = event
    if value.get("schema") != "wellmanifest.logs/event/v1":
        raise _p.ContractFailure(
            "LOGS-EVENT-SCHEMA", path, "event schema is unsupported"
        )
    if (
        not isinstance(value.get("eventId"), str)
        or _p.EVENT_ID_RE.fullmatch(value["eventId"]) is None
    ):
        raise _p.ContractFailure("LOGS-EVENT-ID", path, "event ID is invalid")
    if value.get("stream") != stream or _p.STREAM_RE.fullmatch(stream) is None:
        raise _p.ContractFailure(
            "LOGS-EVENT-STREAM", path, "event stream differs from its file"
        )
    observed_sequence = value.get("sequence")
    if (
        isinstance(observed_sequence, bool)
        or not isinstance(observed_sequence, int)
        or observed_sequence != sequence
    ):
        raise _p.ContractFailure(
            "LOGS-EVENT-SEQUENCE", path, "event sequence is not contiguous"
        )
    vocabulary = bundle["vocabulary"]
    event_type = value.get("eventType")
    if event_type not in vocabulary["eventTypes"] and (
        not isinstance(event_type, str)
        or not 3 <= len(event_type) <= 64
        or _p.DOMAIN_TYPE_RE.fullmatch(event_type) is None
    ):
        raise _p.ContractFailure("LOGS-EVENT-TYPE", path, "event type is invalid")
    if value.get("severity") not in vocabulary["severities"]:
        raise _p.ContractFailure(
            "LOGS-EVENT-SEVERITY", path, "event severity is invalid"
        )
    if value.get("mode") not in vocabulary["modes"]:
        raise _p.ContractFailure("LOGS-EVENT-MODE", path, "event mode is invalid")
    if value.get("outcome") not in vocabulary["outcomes"]:
        raise _p.ContractFailure("LOGS-EVENT-OUTCOME", path, "event outcome is invalid")
    subject_state = value.get("subjectState")
    if subject_state is not None and (
        not isinstance(subject_state, str)
        or len(subject_state) > 32
        or _p.STATE_RE.fullmatch(subject_state) is None
    ):
        raise _p.ContractFailure(
            "LOGS-EVENT-STATE", path, "event subject state is invalid"
        )
    _p.require_datetime(value.get("occurredAt"), path)
    correlation = value.get("correlationId")
    causation = value.get("causationId")
    if not isinstance(correlation, str) or _p.ID_RE.fullmatch(correlation) is None:
        raise _p.ContractFailure(
            "LOGS-EVENT-CORRELATION", path, "correlation ID is invalid"
        )
    if causation is not None and (
        not isinstance(causation, str)
        or _p.ID_RE.fullmatch(causation) is None
        or causation == value["eventId"]
    ):
        raise _p.ContractFailure(
            "LOGS-EVENT-CAUSATION", path, "causation ID is invalid"
        )
    producer = value.get("producer")
    source = value.get("source")
    subject = value.get("subjectRef")
    if (
        not isinstance(producer, str)
        or len(producer) > 128
        or _p.ACTOR_RE.fullmatch(producer) is None
    ):
        raise _p.ContractFailure(
            "LOGS-EVENT-PRODUCER", path, "event producer is invalid"
        )
    if (
        not isinstance(source, str)
        or not 3 <= len(source) <= 64
        or _p.SOURCE_RE.fullmatch(source) is None
    ):
        raise _p.ContractFailure("LOGS-EVENT-SOURCE", path, "event source is invalid")
    if (
        not isinstance(subject, str)
        or len(subject) > 160
        or _p.SUBJECT_RE.fullmatch(subject) is None
    ):
        raise _p.ContractFailure("LOGS-EVENT-SUBJECT", path, "event subject is invalid")
    code = value.get("code")
    if code is not None and (not isinstance(code, str) or code not in catalog):
        raise _p.ContractFailure(
            "LOGS-EVENT-CODE", path, "event code has no error definition"
        )
    if (
        value.get("rawOutputIncluded") is not False
        or value.get("secretMaterialIncluded") is not False
    ):
        raise _p.ContractFailure(
            "LOGS-EVENT-SAFETY", path, "event safety flags must both be false"
        )
    input_hash = value.get("inputHash")
    if not isinstance(input_hash, str) or _p.SHA_RE.fullmatch(input_hash) is None:
        raise _p.ContractFailure(
            "LOGS-EVENT-INPUT", path, "event input hash is invalid"
        )
    receipt = value.get("receiptRef")
    if receipt is not None and (
        not isinstance(receipt, str)
        or len(receipt) > 160
        or _p.RECEIPT_RE.fullmatch(receipt) is None
    ):
        raise _p.ContractFailure(
            "LOGS-EVENT-RECEIPT", path, "event receipt reference is invalid"
        )
    _s.validate_continuity(value, prior_events=prior_events, path=path)
    diagnostic = value.get("diagnostic")
    if diagnostic is not None:
        _s.validate_diagnostic(diagnostic, path)
    _validate_event_evidence(value.get("evidence"), root=root, path=path)
    if value.get("previousHash") != previous_hash:
        raise _p.ContractFailure(
            "LOGS-EVENT-CHAIN", path, "event predecessor hash is invalid"
        )
    event_hash = value.get("eventHash")
    if not isinstance(event_hash, str) or _p.SHA_RE.fullmatch(event_hash) is None:
        raise _p.ContractFailure(
            "LOGS-EVENT-HASH", path, "event hash format is invalid"
        )
    if calculate_event_hash(value) != event_hash:
        raise _p.ContractFailure(
            "LOGS-EVENT-HASH", path, "event hash differs from canonical bytes"
        )
    return event_hash


def _validate_event_evidence(evidence: Any, *, root: Path, path: str) -> None:
    if not isinstance(evidence, list) or len(evidence) > 16:
        raise _p.ContractFailure(
            "LOGS-EVENT-EVIDENCE", path, "event evidence list is invalid"
        )
    seen_evidence: set[tuple[str, str]] = set()
    for item in evidence:
        evidence_item = _p.exact_fields(
            item, {"path", "sha256"}, rule="LOGS-EVENT-EVIDENCE", path=path
        )
        evidence_path = evidence_item.get("path")
        evidence_sha = evidence_item.get("sha256")
        if (
            not isinstance(evidence_path, str)
            or len(evidence_path) > 240
            or not isinstance(evidence_sha, str)
        ):
            raise _p.ContractFailure(
                "LOGS-EVENT-EVIDENCE", path, "event evidence entry is invalid"
            )
        file_path = _p.confined_file(root, evidence_path, "LOGS-EVENT-EVIDENCE")
        actual_sha = _p.sha256_file(
            file_path,
            rule="LOGS-EVENT-EVIDENCE",
            display_path=evidence_path,
        )
        if _p.SHA_RE.fullmatch(evidence_sha) is None or actual_sha != evidence_sha:
            raise _p.ContractFailure(
                "LOGS-EVENT-EVIDENCE", path, "event evidence digest differs"
            )
        pair = (evidence_path, evidence_sha)
        if pair in seen_evidence:
            raise _p.ContractFailure(
                "LOGS-EVENT-EVIDENCE", path, "event evidence is duplicated"
            )
        seen_evidence.add(pair)


def validate_streams(
    root: Path,
    bundle: dict[str, Any],
    catalog: dict[str, dict[str, Any]],
) -> tuple[int, int]:
    resolved_root = root.resolve()
    directory = resolved_root / "logs"
    _p.reject_symlink_ancestors(
        directory,
        stop_at=resolved_root,
        rule="LOGS-STORE-DIRECTORY",
        display_path="logs",
    )
    if not directory.is_dir():
        raise _p.ContractFailure(
            "LOGS-STORE-DIRECTORY", "logs", "log directory is missing"
        )
    entries = sorted(directory.iterdir(), key=lambda p: p.name)
    for entry in entries:
        lstat_mode = entry.lstat().st_mode
        if entry.suffix != ".jsonl" or (
            not stat.S_ISREG(lstat_mode) and not stat.S_ISLNK(lstat_mode)
        ):
            raise _p.ContractFailure(
                "LOGS-STORE-PATH", "logs", "log directory contains an unsupported entry"
            )
    if not entries:
        raise _p.ContractFailure("LOGS-STORE-EMPTY", "logs", "no event stream exists")
    event_ids: set[str] = set()
    events_checked = 0
    for file_path in entries:
        stream = file_path.stem
        relative = file_path.relative_to(resolved_root).as_posix()
        if _p.STREAM_RE.fullmatch(stream) is None:
            raise _p.ContractFailure(
                "LOGS-STORE-PATH", relative, "stream filename is invalid"
            )
        raw = _p.read_bounded_regular_bytes(
            file_path,
            max_bytes=_p.MAX_STREAM_BYTES,
            rule="LOGS-STORE-READ",
            size_rule="LOGS-STORE-READ",
            label="stream",
            display_path=relative,
        )
        lines = raw.splitlines(keepends=True)
        if not lines:
            raise _p.ContractFailure(
                "LOGS-STORE-EMPTY", relative, "stream contains no events"
            )
        previous_hash = _p.ZERO_HASH
        prior_events: dict[str, dict[str, Any]] = {}
        for sequence, line in enumerate(lines, start=1):
            line_path = f"{relative}:{sequence}"
            if not line.endswith(b"\n") or line in {b"\n", b"\r\n"}:
                raise _p.ContractFailure(
                    "LOGS-EVENT-CANONICAL",
                    line_path,
                    "event line is blank or lacks a final newline",
                )
            try:
                decoded = line.decode("utf-8")
            except UnicodeError as error:
                raise _p.ContractFailure(
                    "LOGS-EVENT-JSON", line_path, "event line is not valid UTF-8 JSON"
                ) from error
            event = _p.strict_json_loads(
                decoded, rule="LOGS-EVENT-JSON", path=line_path, label="event line"
            )
            if _p.canonical(event).encode("utf-8") + b"\n" != line:
                raise _p.ContractFailure(
                    "LOGS-EVENT-CANONICAL",
                    line_path,
                    "event line is not canonical JSONL",
                )
            previous_hash = validate_event(
                event,
                bundle=bundle,
                catalog=catalog,
                root=resolved_root,
                path=line_path,
                stream=stream,
                sequence=sequence,
                previous_hash=previous_hash,
                prior_events=prior_events,
            )
            event_id = event["eventId"]
            if event_id in event_ids:
                raise _p.ContractFailure(
                    "LOGS-EVENT-UNIQUE", line_path, "event ID is duplicated"
                )
            event_ids.add(event_id)
            prior_events[event_id] = event
            events_checked += 1
    return len(entries), events_checked


def validate_repository(root: Path) -> dict[str, Any]:
    findings: list[_p.Finding] = []
    streams_checked = 0
    events_checked = 0
    errors_checked = 0
    contract_sha = ""
    try:
        bundle, contract_sha = _c.load_contract(root)
    except _p.ContractFailure as error:
        findings.append(_p.finding(error))
        return _p.report(
            findings, contract_sha, streams_checked, events_checked, errors_checked
        )
    try:
        _c.validate_proto(root, bundle)
    except _p.ContractFailure as error:
        findings.append(_p.finding(error))
    catalog: dict[str, dict[str, Any]] = {}
    try:
        catalog = _a.load_error_catalog(root, bundle)
        errors_checked = len(catalog)
    except _p.ContractFailure as error:
        findings.append(_p.finding(error))
    if catalog:
        try:
            streams_checked, events_checked = validate_streams(root, bundle, catalog)
        except _p.ContractFailure as error:
            findings.append(_p.finding(error))
    return _p.report(
        findings, contract_sha, streams_checked, events_checked, errors_checked
    )
