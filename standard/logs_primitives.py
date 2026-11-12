"""Shared constants, strict JSON, and descriptor-safe I/O for wellmanifest.logs/v1."""

from __future__ import annotations

import errno
import hashlib
import json
import math
import os
import re
import stat
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

CONTRACT_PATH = Path("contracts/logs.contract.v0.5.json")
LEGACY_CONTRACT_PATHS = (
    Path("contracts/logs.contract.json"),
    Path("contracts/logs.contract.v0.3.json"),
    Path("contracts/logs.contract.v0.4.json"),
)
HELP_PATH = "errors/LOGS-VALIDATION-001.md"
DIAGNOSTIC_CODE = "LOGS-VALIDATION-001"
ZERO_HASH = "0" * 64
MAX_ADOPTED_SCHEMA_BYTES = 1024 * 1024
MAX_ADOPTED_CATALOG_BYTES = 64 * 1024
MAX_ERROR_DOCUMENT_BYTES = 256 * 1024
MAX_CONTRACT_BYTES = 2 * 1024 * 1024
MAX_REQUEST_BYTES = 64 * 1024
MAX_STREAM_BYTES = 16 * 1024 * 1024
MAX_EVIDENCE_BYTES = 16 * 1024 * 1024
MAX_JSON_DEPTH = 128

CODE_RE = re.compile(r"^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+$")
NAMESPACE_RE = re.compile(r"^[A-Z][A-Z0-9]{1,31}$")
STREAM_RE = re.compile(r"^[a-z][a-z0-9._-]{0,63}$")
ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
EVENT_ID_RE = re.compile(r"^event:[A-Za-z0-9._:-]{2,122}$")
ACTOR_RE = re.compile(r"^(?:human|agent|service):[A-Za-z0-9._:-]+$")
OWNER_RE = re.compile(r"^(?:human|agent|service|unresolved):[A-Za-z0-9._:-]+$")
SUBJECT_RE = re.compile(r"^[a-z][a-z0-9+.-]*:[A-Za-z0-9._:/-]+$")
DOMAIN_TYPE_RE = re.compile(r"^(?!logs\.)[a-z][a-z0-9]*(?:\.[a-z][a-z0-9_]*)+$")
SOURCE_RE = re.compile(r"^[a-z][a-z0-9]*(?:\.[a-z][a-z0-9_]*)*$")
STATE_RE = re.compile(r"^[a-z][a-z0-9_]*$")
RECEIPT_RE = re.compile(
    r"^receipt://[a-z0-9][a-z0-9.-]{0,63}(?:/[A-Za-z0-9][A-Za-z0-9._:-]{0,63}){1,8}$"
)
ENDPOINT_REF_RE = re.compile(
    r"^(?:endpoint:[A-Za-z0-9._:/-]+|https?://"
    r"(?:[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?|\[[0-9A-Fa-f:.]+\])"
    r"(?::[1-9][0-9]{0,4})?)$"
)
TRANSPORT_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")
REMEDIATION_REF_RE = re.compile(r"^(?:error|knowledge|runbook)://[A-Za-z0-9._:/-]+$")
TRACE_ID_RE = re.compile(r"^[a-f0-9]{32}$")
SPAN_ID_RE = re.compile(r"^[a-f0-9]{16}$")
PATH_RE = re.compile(r"^(?!/)(?!.*(?:^|/)\.\.(?:/|$))[A-Za-z0-9._/-]+$")
SHA_RE = re.compile(r"^[a-f0-9]{64}$")
DATETIME_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]"
    r"(?:\.[0-9]{1,9})?Z$"
)
ARTIFACT_RE = re.compile(r"^artifact://[a-z0-9.-]+/[A-Za-z0-9._:/-]+/r[1-9][0-9]*$")
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f-\x9f]")
_SURROGATE_RE = re.compile(r"[\ud800-\udfff]")

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
EXPECTED_REQUEST_GBNF = (
    r"root ::= inspect | plan_append" + "\n"
    r'inspect ::= "{\"schema\":\"wellmanifest.logs/request/v1\",\"operation\":\"inspect\",\"processRef\":\"logs://repository/contracts/query/inspect\"}"'
    + "\n"
    r'plan_append ::= "{\"schema\":\"wellmanifest.logs/request/v1\",\"operation\":\"plan_append\",\"processRef\":\"logs://stream/events/query/plan-append\",\"stream\":" string ",\"expectedVersion\":" integer ",\"eventRef\":" string ",\"eventSha256\":" string "}"'
    + "\n"
    r'integer ::= "0" | [1-9] [0-9]*' + "\n"
    r'string ::= "\"" chars "\""' + "\n"
    r'chars ::= ([^"\\\x00-\x1f] | "\\" (["\\/bfnrt] | "u" [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F]))*'
    + "\n"
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


def finding(error: ContractFailure) -> Finding:
    return Finding(
        code=DIAGNOSTIC_CODE,
        rule=error.rule,
        severity="ERROR",
        path=error.path,
        message=error.message,
    )


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


def has_control_chars(value: str) -> bool:
    return _CONTROL_CHAR_RE.search(value) is not None


def _validate_canonical_domain(
    value: Any, *, path: str = CONTRACT_PATH.as_posix()
) -> None:
    stack: list[tuple[Any, int]] = [(value, 0)]
    while stack:
        current, depth = stack.pop()
        if depth > MAX_JSON_DEPTH:
            raise ContractFailure(
                "LOGS-CANONICAL-DEPTH",
                path,
                "JSON nesting exceeds the bounded v1 depth",
            )
        if isinstance(current, float):
            raise ContractFailure(
                "LOGS-CANONICAL-NUMBER",
                path,
                "floating-point values are outside the v1 canonical domain",
            )
        if isinstance(current, str):
            if _SURROGATE_RE.search(current) is not None:
                raise ContractFailure(
                    "LOGS-CANONICAL-STRING",
                    path,
                    "lone UTF-16 surrogates are outside the v1 canonical domain",
                )
        elif isinstance(current, dict):
            for key, child in current.items():
                if not isinstance(key, str) or _SURROGATE_RE.search(key) is not None:
                    raise ContractFailure(
                        "LOGS-CANONICAL-STRING",
                        path,
                        "object keys must be valid UTF-8 strings without surrogates",
                    )
                stack.append((child, depth + 1))
        elif isinstance(current, list):
            for child in current:
                stack.append((child, depth + 1))


def canonical(value: Any) -> str:
    """Canonical JSON for the v1 domain, excluding floats, surrogates, and deep nesting."""
    _validate_canonical_domain(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, val in pairs:
        if _SURROGATE_RE.search(key) is not None:
            raise ValueError("lone UTF-16 surrogate in object key")
        if key in out:
            raise ValueError(f"duplicate JSON key: {key}")
        out[key] = val
    return out


def _parse_finite_float(token: str) -> float:
    parsed = float(token)
    if not math.isfinite(parsed):
        raise ValueError("non-finite JSON float overflow")
    return parsed


def _reject_json_constant(token: str) -> Any:
    raise ValueError(f"non-standard JSON constant: {token}")


def strict_json_loads(raw_text: str, *, rule: str, path: str, label: str) -> Any:
    try:
        parsed = json.loads(
            raw_text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_float=_parse_finite_float,
            parse_constant=_reject_json_constant,
        )
    except (ValueError, RecursionError) as error:
        raise ContractFailure(
            rule, path, f"{label} is unreadable or invalid"
        ) from error
    stack: list[tuple[Any, int]] = [(parsed, 0)]
    while stack:
        current, depth = stack.pop()
        if depth > MAX_JSON_DEPTH:
            raise ContractFailure(rule, path, f"{label} exceeds maximum JSON depth")
        if isinstance(current, str):
            if _SURROGATE_RE.search(current) is not None:
                raise ContractFailure(
                    rule, path, f"{label} contains lone UTF-16 surrogate"
                )
        elif isinstance(current, dict):
            for child in current.values():
                stack.append((child, depth + 1))
        elif isinstance(current, list):
            for child in current:
                stack.append((child, depth + 1))
    return parsed


def reject_symlink_ancestors(
    target: Path,
    *,
    stop_at: Path,
    rule: str,
    display_path: str,
) -> None:
    try:
        rel_parts = target.relative_to(stop_at).parts
    except ValueError as error:
        raise ContractFailure(
            rule, display_path, "path escapes the repository root"
        ) from error
    cursor = stop_at
    for part in rel_parts:
        if part in ("", "."):
            continue
        if part == "..":
            raise ContractFailure(
                rule, display_path, "path violates repository confinement"
            )
        cursor = cursor / part
        try:
            st = os.lstat(cursor)
        except OSError as error:
            raise ContractFailure(
                rule, display_path, "required path is unavailable"
            ) from error
        if stat.S_ISLNK(st.st_mode):
            raise ContractFailure(rule, display_path, "symbolic paths are forbidden")


def read_bounded_regular_bytes(
    path: Path,
    *,
    max_bytes: int,
    rule: str,
    label: str,
    display_path: str | None = None,
    min_bytes: int = 0,
    size_rule: str | None = None,
) -> bytes:
    shown = display_path if display_path is not None else path.as_posix()
    effective_size_rule = size_rule or rule
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        before = os.lstat(path)
    except OSError as error:
        raise ContractFailure(rule, shown, f"{label} is unavailable") from error
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise ContractFailure(
            effective_size_rule, shown, f"{label} is not a regular file"
        )
    try:
        fd = os.open(path, flags)
    except OSError as error:
        target_rule = effective_size_rule if error.errno == errno.ELOOP else rule
        raise ContractFailure(target_rule, shown, f"{label} is unavailable") from error
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (
            before.st_dev,
            before.st_ino,
        ):
            raise ContractFailure(
                effective_size_rule, shown, f"{label} changed during open"
            )
        if opened.st_size < min_bytes or opened.st_size > max_bytes:
            raise ContractFailure(
                effective_size_rule,
                shown,
                f"{label} violates the bounded input size",
            )
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(fd, min(65536, max_bytes - total + 1))
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise ContractFailure(
                    effective_size_rule,
                    shown,
                    f"{label} exceeds the bounded input size",
                )
            chunks.append(chunk)
        data = b"".join(chunks)
    except OSError as error:
        raise ContractFailure(rule, shown, f"{label} is unreadable") from error
    finally:
        os.close(fd)
    if len(data) < min_bytes:
        raise ContractFailure(
            effective_size_rule,
            shown,
            f"{label} violates the bounded input size",
        )
    return data


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(
    path: Path,
    *,
    rule: str = "LOGS-FILE-READ",
    max_bytes: int = MAX_EVIDENCE_BYTES,
    display_path: str | None = None,
) -> str:
    return sha256_bytes(
        read_bounded_regular_bytes(
            path,
            max_bytes=max_bytes,
            rule=rule,
            label="file",
            display_path=display_path,
        )
    )


def exact_fields(
    value: Any,
    required: set[str],
    *,
    rule: str,
    path: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractFailure(rule, path, "document must be an object")
    if set(value) != required:
        raise ContractFailure(
            rule, path, "document fields do not match the closed contract"
        )
    return value


def read_json(
    path: Path,
    *,
    rule: str,
    label: str,
    max_bytes: int = MAX_CONTRACT_BYTES,
    display_path: str | None = None,
) -> Any:
    shown = display_path if display_path is not None else path.as_posix()
    raw = read_bounded_regular_bytes(
        path,
        max_bytes=max_bytes,
        rule=rule,
        label=label,
        display_path=shown,
    )
    try:
        text = raw.decode("utf-8")
    except UnicodeError as error:
        raise ContractFailure(
            rule, shown, f"{label} is unreadable or invalid"
        ) from error
    return strict_json_loads(text, rule=rule, path=shown, label=label)


def confined_file(root: Path, relative: str, rule: str) -> Path:
    if PATH_RE.fullmatch(relative) is None:
        raise ContractFailure(rule, relative, "path violates repository confinement")
    resolved_root = root.resolve()
    lexical = resolved_root / relative
    reject_symlink_ancestors(
        lexical, stop_at=resolved_root, rule=rule, display_path=relative
    )
    candidate = lexical.resolve()
    try:
        candidate.relative_to(resolved_root)
    except ValueError as error:
        raise ContractFailure(
            rule, relative, "path escapes the repository root"
        ) from error
    try:
        st = os.lstat(candidate)
    except OSError as error:
        raise ContractFailure(rule, relative, "required file is missing") from error
    if not stat.S_ISREG(st.st_mode):
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
        or any(
            not isinstance(item, str)
            or not item
            or len(item) > 320
            or has_control_chars(item)
            or _SURROGATE_RE.search(item) is not None
            for item in value
        )
        or (unique and len(value) != len(set(value)))
    ):
        raise ContractFailure(rule, path, "string list violates its bounded contract")
    return value


def require_datetime(value: Any, path: str) -> None:
    if not isinstance(value, str) or DATETIME_RE.fullmatch(value) is None:
        raise ContractFailure(
            "LOGS-EVENT-TIME", path, "event time is not normalized UTC"
        )
    try:
        datetime(
            int(value[0:4]),
            int(value[5:7]),
            int(value[8:10]),
            int(value[11:13]),
            int(value[14:16]),
            int(value[17:19]),
        )
    except ValueError as error:
        raise ContractFailure(
            "LOGS-EVENT-TIME", path, "event time is invalid"
        ) from error
