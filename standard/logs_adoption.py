"""Error runbook catalog and consumer adoption validators for wellmanifest.logs/v1."""

from __future__ import annotations

import re
import stat
from dataclasses import asdict
from pathlib import Path
from typing import Any

from standard import logs_contract as _c
from standard import logs_primitives as _p

_FENCE_PATTERN = re.compile(r"```log-error-dsl\n([^\n]+)\n```", re.MULTILINE)


def validate_error_definition(
    value: Any,
    *,
    code: str,
    bundle: dict[str, Any],
    path: str,
) -> dict[str, Any]:
    definition = _p.exact_fields(
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
        raise _p.ContractFailure(
            "LOGS-DOC-SCHEMA", path, "error DSL schema is unsupported"
        )
    if definition.get("code") != code or _p.CODE_RE.fullmatch(code) is None:
        raise _p.ContractFailure(
            "LOGS-DOC-CODE", path, "error DSL code differs from its file"
        )
    version = definition.get("version")
    if (
        isinstance(version, bool)
        or not isinstance(version, int)
        or not 1 <= version <= 2147483647
    ):
        raise _p.ContractFailure(
            "LOGS-DOC-VERSION", path, "error DSL version is invalid"
        )
    allowed_severities = bundle["schemas"]["error"]["properties"]["severity"]["enum"]
    if definition.get("severity") not in allowed_severities:
        raise _p.ContractFailure("LOGS-DOC-SEVERITY", path, "error severity is invalid")
    if definition.get("category") not in vocabulary["errorCategories"]:
        raise _p.ContractFailure("LOGS-DOC-CATEGORY", path, "error category is invalid")
    for key, maximum in (("title", 160), ("meaning", 600)):
        item = definition.get(key)
        if (
            not isinstance(item, str)
            or not item
            or len(item) > maximum
            or _p.has_control_chars(item)
        ):
            raise _p.ContractFailure("LOGS-DOC-TEXT", path, f"error {key} is invalid")
    _p.require_string_list(
        definition.get("causes"),
        minimum=1,
        maximum=12,
        unique=True,
        rule="LOGS-DOC-CAUSES",
        path=path,
    )
    for key in ("remediation", "verification", "doNot"):
        _p.require_string_list(
            definition.get(key),
            minimum=1,
            maximum=12,
            unique=False,
            rule="LOGS-DOC-STEPS",
            path=path,
        )
    owner = definition.get("owner")
    if (
        not isinstance(owner, str)
        or len(owner) > 128
        or _p.OWNER_RE.fullmatch(owner) is None
    ):
        raise _p.ContractFailure("LOGS-DOC-OWNER", path, "error owner route is invalid")
    related = _p.require_string_list(
        definition.get("relatedEventTypes"),
        minimum=1,
        maximum=7,
        unique=True,
        rule="LOGS-DOC-EVENTS",
        path=path,
    )
    if any(item not in vocabulary["eventTypes"] for item in related):
        raise _p.ContractFailure(
            "LOGS-DOC-EVENTS", path, "error references an unknown event type"
        )
    return definition


def load_error_documents(
    root: Path,
    bundle: dict[str, Any],
    *,
    directory_relative: str,
    declared: set[str],
) -> dict[str, dict[str, Any]]:
    if _p.PATH_RE.fullmatch(directory_relative) is None:
        raise _p.ContractFailure(
            "LOGS-DOC-DIRECTORY",
            directory_relative,
            "error directory violates repository confinement",
        )
    resolved_root = root.resolve()
    unresolved_directory = resolved_root / directory_relative
    _p.reject_symlink_ancestors(
        unresolved_directory,
        stop_at=resolved_root,
        rule="LOGS-DOC-DIRECTORY",
        display_path=directory_relative,
    )
    directory = unresolved_directory.resolve()
    try:
        directory.relative_to(resolved_root)
    except ValueError as error:
        raise _p.ContractFailure(
            "LOGS-DOC-DIRECTORY",
            directory_relative,
            "error directory escapes its catalog root",
        ) from error
    if not directory.is_dir():
        raise _p.ContractFailure(
            "LOGS-DOC-DIRECTORY",
            directory_relative,
            "error directory is missing or symbolic",
        )
    documents: dict[str, dict[str, Any]] = {}
    entries = sorted(directory.iterdir(), key=lambda p: p.name)
    for entry in entries:
        lstat_mode = entry.lstat().st_mode
        if entry.suffix != ".md" or (
            not stat.S_ISREG(lstat_mode) and not stat.S_ISLNK(lstat_mode)
        ):
            raise _p.ContractFailure(
                "LOGS-DOC-PATH",
                directory_relative,
                "error directory contains an unsupported entry",
            )
    for file_path in entries:
        code = file_path.stem
        relative = file_path.relative_to(resolved_root).as_posix()
        if _p.CODE_RE.fullmatch(code) is None:
            raise _p.ContractFailure(
                "LOGS-DOC-PATH", relative, "error filename is not a stable code"
            )
        raw = _p.read_bounded_regular_bytes(
            file_path,
            max_bytes=_p.MAX_ERROR_DOCUMENT_BYTES,
            rule="LOGS-DOC-READ",
            size_rule="LOGS-DOC-READ",
            label="error page",
            display_path=relative,
        )
        try:
            text = raw.decode("utf-8")
        except UnicodeError as error:
            raise _p.ContractFailure(
                "LOGS-DOC-READ", relative, "error page is unreadable"
            ) from error
        for section in _p.REQUIRED_ERROR_SECTIONS:
            marker = f"## {section}\n"
            if text.count(marker) != 1:
                raise _p.ContractFailure(
                    "LOGS-DOC-SECTIONS",
                    relative,
                    "error page does not contain each required section exactly once",
                )
            after = text.split(marker, 1)[1]
            body = after.split("\n## ", 1)[0].strip()
            if not body:
                raise _p.ContractFailure(
                    "LOGS-DOC-SECTIONS",
                    relative,
                    "error page contains an empty required section",
                )
        fences = _FENCE_PATTERN.findall(text)
        if len(fences) != 1:
            raise _p.ContractFailure(
                "LOGS-DOC-FENCE",
                relative,
                "error page must contain exactly one single-line log-error-dsl fence",
            )
        definition = _p.strict_json_loads(
            fences[0],
            rule="LOGS-DOC-JSON",
            path=relative,
            label="embedded error DSL",
        )
        if _p.canonical(definition) != fences[0]:
            raise _p.ContractFailure(
                "LOGS-DOC-CANONICAL", relative, "embedded error DSL is not canonical"
            )
        documents[code] = validate_error_definition(
            definition,
            code=code,
            bundle=bundle,
            path=relative,
        )
        expected_title = f"# {code}: {documents[code]['title']}\n"
        if not text.startswith(expected_title):
            raise _p.ContractFailure(
                "LOGS-DOC-TITLE",
                relative,
                "error heading does not match its filename and embedded DSL title",
            )
    if set(documents) != declared:
        raise _p.ContractFailure(
            "LOGS-DOC-CATALOG",
            directory_relative,
            "error page set differs from the diagnostic catalog",
        )
    return documents


def load_error_catalog(root: Path, bundle: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return load_error_documents(
        root,
        bundle,
        directory_relative="errors",
        declared=set(bundle["diagnosticCodes"]),
    )


def validate_adopted_event_schema(root: Path, candidate_path: Path) -> dict[str, Any]:
    """Compare an adopted event schema with the canonical semantic schema."""
    findings: list[_p.Finding] = []
    contract_sha = ""
    candidate_sha = ""
    shown = candidate_path.as_posix()
    try:
        bundle, contract_sha = _c.load_contract(root)
        raw = _p.read_bounded_regular_bytes(
            candidate_path,
            max_bytes=_p.MAX_ADOPTED_SCHEMA_BYTES,
            min_bytes=2,
            rule="LOGS-ADOPTION-SCHEMA-READ",
            size_rule="LOGS-ADOPTION-SCHEMA-SIZE",
            label="adopted event schema",
            display_path=shown,
        )
        try:
            decoded = raw.decode("utf-8")
        except UnicodeError as error:
            raise _p.ContractFailure(
                "LOGS-ADOPTION-SCHEMA-JSON",
                shown,
                "adopted event schema is unreadable or invalid",
            ) from error
        candidate = _p.strict_json_loads(
            decoded,
            rule="LOGS-ADOPTION-SCHEMA-JSON",
            path=shown,
            label="adopted event schema",
        )
        candidate_canonical = _p.canonical(candidate)
        candidate_sha = _p.sha256_bytes(candidate_canonical.encode("utf-8"))
        if candidate_canonical != _p.canonical(bundle["schemas"]["event"]):
            raise _p.ContractFailure(
                "LOGS-ADOPTION-SCHEMA-DRIFT",
                shown,
                "adopted event schema differs from the canonical contract; update the vendored schema or declare a separately versioned projection",
            )
    except _p.ContractFailure as error:
        findings.append(_p.finding(error))
    return {
        "schema": "wellmanifest.logs/adoption-report/v1",
        "valid": not findings,
        "contractSha256": contract_sha,
        "candidateSchemaSha256": candidate_sha,
        "findings": [asdict(item) for item in findings],
    }


def validate_adopted_error_catalog(root: Path, catalog_path: Path) -> dict[str, Any]:
    """Validate one adopter-owned, contract-pinned error catalog and runbook set."""
    findings: list[_p.Finding] = []
    contract_sha = ""
    catalog_sha = ""
    errors_checked = 0
    shown = catalog_path.as_posix()
    try:
        bundle, contract_sha = _c.load_contract(root)
        raw = _p.read_bounded_regular_bytes(
            catalog_path,
            max_bytes=_p.MAX_ADOPTED_CATALOG_BYTES,
            min_bytes=2,
            rule="LOGS-ADOPTION-ERROR-CATALOG-READ",
            size_rule="LOGS-ADOPTION-ERROR-CATALOG-SIZE",
            label="adopter error catalog",
            display_path=shown,
        )
        catalog_sha = _p.sha256_bytes(raw)
        try:
            decoded = raw.decode("utf-8")
        except UnicodeError as error:
            raise _p.ContractFailure(
                "LOGS-ADOPTION-ERROR-CATALOG-JSON",
                shown,
                "adopter error catalog is unreadable or invalid",
            ) from error
        catalog = _p.exact_fields(
            _p.strict_json_loads(
                decoded,
                rule="LOGS-ADOPTION-ERROR-CATALOG-JSON",
                path=shown,
                label="adopter error catalog",
            ),
            {
                "schema",
                "namespace",
                "contractSha256",
                "errorsDirectory",
                "diagnosticCodes",
            },
            rule="LOGS-ADOPTION-ERROR-CATALOG-FIELDS",
            path=shown,
        )
        if catalog.get("schema") != "wellmanifest.logs/adopter-error-catalog/v1":
            raise _p.ContractFailure(
                "LOGS-ADOPTION-ERROR-CATALOG-SCHEMA",
                shown,
                "adopter error catalog schema is unsupported",
            )
        namespace = catalog.get("namespace")
        reserved_namespaces = bundle["vocabulary"]["reservedErrorNamespaces"]
        if (
            not isinstance(namespace, str)
            or _p.NAMESPACE_RE.fullmatch(namespace) is None
            or namespace in reserved_namespaces
        ):
            raise _p.ContractFailure(
                "LOGS-ADOPTION-ERROR-NAMESPACE",
                shown,
                "adopter namespace is invalid or reserved by wellmanifest/logs",
            )
        if catalog.get("contractSha256") != contract_sha:
            raise _p.ContractFailure(
                "LOGS-ADOPTION-ERROR-CONTRACT-DRIFT",
                shown,
                "adopter catalog is not pinned to the canonical contract digest",
            )
        errors_directory = catalog.get("errorsDirectory")
        if (
            not isinstance(errors_directory, str)
            or _p.PATH_RE.fullmatch(errors_directory) is None
        ):
            raise _p.ContractFailure(
                "LOGS-ADOPTION-ERROR-PATH",
                shown,
                "adopter errors directory violates repository confinement",
            )
        codes = _p.require_string_list(
            catalog.get("diagnosticCodes"),
            minimum=1,
            maximum=256,
            unique=True,
            rule="LOGS-ADOPTION-ERROR-CODES",
            path=shown,
        )
        if codes != sorted(codes) or any(
            _p.CODE_RE.fullmatch(code) is None or not code.startswith(f"{namespace}-")
            for code in codes
        ):
            raise _p.ContractFailure(
                "LOGS-ADOPTION-ERROR-NAMESPACE",
                shown,
                "diagnostic codes must be sorted stable codes owned by the declared namespace",
            )
        documents = load_error_documents(
            catalog_path.parent,
            bundle,
            directory_relative=errors_directory,
            declared=set(codes),
        )
        errors_checked = len(documents)
    except _p.ContractFailure as error:
        findings.append(_p.finding(error))
    return {
        "schema": "wellmanifest.logs/error-adoption-report/v1",
        "valid": not findings,
        "contractSha256": contract_sha,
        "candidateCatalogSha256": catalog_sha,
        "errorDefinitionsChecked": errors_checked,
        "findings": [asdict(item) for item in findings],
    }
