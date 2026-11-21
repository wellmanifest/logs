"""Dependency-free validator for wellmanifest.logs/urtlog-bridge-profile/v1."""

from __future__ import annotations

import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from standard.logs_primitives import (
    ContractFailure,
    confined_file,
    exact_fields,
    finding,
    read_json,
    sha256_file,
)

URTLOG_BRIDGE_SCHEMA_PATH = Path("contracts/urtlog-bridge.schema.v1.json")
URTLOG_BRIDGE_PROFILE_PATH = Path("contracts/urtlog-bridge.profile.v1.json")
MAX_PROFILE_BYTES = 65536
SEMVER_RE = re.compile(r"\A[0-9]+\.[0-9]+\.[0-9]+\Z")
REPO_RE = re.compile(r"\A[a-z0-9-]+/[a-z0-9-]+\Z")
ADOPT_RE = re.compile(r"\Awellmanifest/[a-z0-9-]+\Z")
REQ_RE = re.compile(r"\Auritime-urtlog>=[0-9]+\.[0-9]+\.[0-9]+\Z")
EXPECTED_TUPLE = ["URT", "URI", "URN_IN", "URN_OUT"]
EXPECTED_STATUSES = {
    "planned",
    "started",
    "succeeded",
    "failed",
    "unknown",
    "canceled",
}
EXPECTED_DAG_FIELDS = {"causation_id", "depends_on", "input_urns", "output_urns"}
EXPECTED_REGISTRY_KINDS = {"uri", "url", "urn"}
ALLOWED_LOOKUP_MODES = {"btree-prefix-or-single-urn", "single-urn"}


def _is_strict_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _require_bool_const(
    obj: dict[str, Any], key: str, expected: bool, label: str, rule: str
) -> None:
    if obj.get(key) is not expected:
        raise ContractFailure(
            rule, label, f"{key} must be {str(expected).lower()}"
        )


def _require_str_const(
    obj: dict[str, Any], key: str, expected: str, label: str, rule: str
) -> None:
    if obj.get(key) != expected:
        raise ContractFailure(rule, label, f"{key} must equal {expected!r}")


def _require_closed_dict(
    parent: dict[str, Any], key: str, required_keys: set[str], label: str
) -> dict[str, Any]:
    val = parent.get(key)
    if not isinstance(val, dict):
        raise ContractFailure("LOGS-URTLOG-TYPE", label, f"{key} must be an object")
    exact_fields(val, required_keys, rule="LOGS-URTLOG-FIELDS", path=f"{label}.{key}")
    return val


def validate_urtlog_bridge_schema_doc(
    schema_doc: Any, label: str
) -> None:
    if not isinstance(schema_doc, dict):
        raise ContractFailure("LOGS-URTLOG-SCHEMA", label, "schema root must be an object")
    if schema_doc.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        raise ContractFailure("LOGS-URTLOG-SCHEMA", label, "unsupported JSON Schema dialect")
    if schema_doc.get("additionalProperties") is not False:
        raise ContractFailure("LOGS-URTLOG-SCHEMA", label, "schema root must close additionalProperties")
    stack: list[tuple[Any, str]] = [(schema_doc, label)]
    while stack:
        node, where = stack.pop()
        if isinstance(node, dict):
            if node.get("type") == "object" and node.get("additionalProperties") is not False:
                raise ContractFailure(
                    "LOGS-URTLOG-SCHEMA-CLOSED",
                    where,
                    "every object subschema must set additionalProperties=false",
                )
            for k, child in node.items():
                if isinstance(child, (dict, list)):
                    stack.append((child, f"{where}.{k}"))
        elif isinstance(node, list):
            for idx, child in enumerate(node):
                if isinstance(child, (dict, list)):
                    stack.append((child, f"{where}[{idx}]"))


def validate_urtlog_bridge_profile_doc(doc: Any, label: str) -> None:
    if not isinstance(doc, dict):
        raise ContractFailure("LOGS-URTLOG-PROFILE", label, "profile root must be an object")
    exact_fields(
        doc,
        {
            "$schema",
            "schema",
            "version",
            "placement",
            "packaging",
            "temporalModel",
            "registry",
            "decisionContextSlice",
            "verification",
        },
        rule="LOGS-URTLOG-FIELDS",
        path=label,
    )
    _require_str_const(doc, "$schema", "./urtlog-bridge.schema.v1.json", label, "LOGS-URTLOG-SCHEMA-REF")
    _require_str_const(
        doc,
        "schema",
        "wellmanifest.logs/urtlog-bridge-profile/v1",
        label,
        "LOGS-URTLOG-SCHEMA-ID",
    )
    version = doc.get("version")
    if not isinstance(version, str) or SEMVER_RE.fullmatch(version) is None:
        raise ContractFailure("LOGS-URTLOG-VERSION", label, "version must be SemVer X.Y.Z")

    placement = _require_closed_dict(
        doc, "placement", {"home", "shape", "runtimeImplementations", "adopt"}, label
    )
    _require_str_const(placement, "home", "wellmanifest", f"{label}.placement", "LOGS-URTLOG-PLACEMENT")
    _require_str_const(placement, "shape", "domain_pack", f"{label}.placement", "LOGS-URTLOG-PLACEMENT")
    impls = placement.get("runtimeImplementations")
    if (
        not isinstance(impls, list)
        or not (1 <= len(impls) <= 16)
        or len(set(impls)) != len(impls)
        or not all(isinstance(x, str) and REPO_RE.fullmatch(x) for x in impls)
    ):
        raise ContractFailure(
            "LOGS-URTLOG-PLACEMENT",
            f"{label}.placement.runtimeImplementations",
            "runtimeImplementations must list 1..16 unique owner/repo identifiers",
        )
    adopts = placement.get("adopt")
    if (
        not isinstance(adopts, list)
        or not (1 <= len(adopts) <= 16)
        or len(set(adopts)) != len(adopts)
        or not all(isinstance(x, str) and ADOPT_RE.fullmatch(x) for x in adopts)
        or "wellmanifest/logs" not in adopts
    ):
        raise ContractFailure(
            "LOGS-URTLOG-PLACEMENT",
            f"{label}.placement.adopt",
            "adopt must list unique wellmanifest/* standards including wellmanifest/logs",
        )

    packaging = _require_closed_dict(
        doc,
        "packaging",
        {
            "extraName",
            "requirement",
            "mandatoryRuntimeDependency",
            "lazyImportModule",
            "optInEnvVar",
            "failOpenOnMissingOrError",
            "mutateTrackedRepoFiles",
        },
        label,
    )
    _require_str_const(packaging, "extraName", "urtlog", f"{label}.packaging", "LOGS-URTLOG-PACKAGING")
    req = packaging.get("requirement")
    if not isinstance(req, str) or REQ_RE.fullmatch(req) is None:
        raise ContractFailure(
            "LOGS-URTLOG-PACKAGING",
            f"{label}.packaging.requirement",
            "requirement must match uritime-urtlog>=X.Y.Z",
        )
    _require_bool_const(packaging, "mandatoryRuntimeDependency", False, f"{label}.packaging", "LOGS-URTLOG-PACKAGING")
    _require_str_const(packaging, "lazyImportModule", "urtlog", f"{label}.packaging", "LOGS-URTLOG-PACKAGING")
    _require_str_const(packaging, "optInEnvVar", "URTLOG_STATE_DIR", f"{label}.packaging", "LOGS-URTLOG-PACKAGING")
    _require_bool_const(packaging, "failOpenOnMissingOrError", True, f"{label}.packaging", "LOGS-URTLOG-PACKAGING")
    _require_bool_const(packaging, "mutateTrackedRepoFiles", False, f"{label}.packaging", "LOGS-URTLOG-PACKAGING")

    temporal = _require_closed_dict(
        doc,
        "temporalModel",
        {
            "tuple",
            "planKind",
            "logKind",
            "planNeverSucceeded",
            "planGrantsAuthority",
            "allowedEventStatuses",
            "blockedStateMapping",
            "dagLinkFields",
        },
        label,
    )
    if temporal.get("tuple") != EXPECTED_TUPLE:
        raise ContractFailure(
            "LOGS-URTLOG-TEMPORAL",
            f"{label}.temporalModel.tuple",
            f"tuple must equal {EXPECTED_TUPLE}",
        )
    _require_str_const(temporal, "planKind", "intent", f"{label}.temporalModel", "LOGS-URTLOG-TEMPORAL")
    _require_str_const(temporal, "logKind", "event", f"{label}.temporalModel", "LOGS-URTLOG-TEMPORAL")
    _require_bool_const(temporal, "planNeverSucceeded", True, f"{label}.temporalModel", "LOGS-URTLOG-TEMPORAL")
    _require_bool_const(temporal, "planGrantsAuthority", False, f"{label}.temporalModel", "LOGS-URTLOG-TEMPORAL")
    statuses = temporal.get("allowedEventStatuses")
    if (
        not isinstance(statuses, list)
        or len(statuses) != len(EXPECTED_STATUSES)
        or set(statuses) != EXPECTED_STATUSES
    ):
        raise ContractFailure(
            "LOGS-URTLOG-STATUS",
            f"{label}.temporalModel.allowedEventStatuses",
            f"allowedEventStatuses must equal {sorted(EXPECTED_STATUSES)}",
        )
    blocked = _require_closed_dict(
        temporal,
        "blockedStateMapping",
        {"eventStatus", "logType", "metadataStatusField", "metadataStatusValue"},
        f"{label}.temporalModel",
    )
    _require_str_const(blocked, "eventStatus", "unknown", f"{label}.temporalModel.blockedStateMapping", "LOGS-URTLOG-BLOCKED-MAP")
    _require_str_const(blocked, "logType", "audit", f"{label}.temporalModel.blockedStateMapping", "LOGS-URTLOG-BLOCKED-MAP")
    _require_str_const(blocked, "metadataStatusField", "status", f"{label}.temporalModel.blockedStateMapping", "LOGS-URTLOG-BLOCKED-MAP")
    _require_str_const(blocked, "metadataStatusValue", "blocked", f"{label}.temporalModel.blockedStateMapping", "LOGS-URTLOG-BLOCKED-MAP")
    dag_fields = temporal.get("dagLinkFields")
    if (
        not isinstance(dag_fields, list)
        or len(dag_fields) < 2
        or len(set(dag_fields)) != len(dag_fields)
        or not set(dag_fields).issubset(EXPECTED_DAG_FIELDS)
        or "causation_id" not in dag_fields
    ):
        raise ContractFailure(
            "LOGS-URTLOG-DAG",
            f"{label}.temporalModel.dagLinkFields",
            "dagLinkFields must include causation_id and at least one additional DAG link field",
        )

    registry = _require_closed_dict(
        doc,
        "registry",
        {
            "supportedKinds",
            "secretsInUrlsOrFixtures",
            "accessContextFailClosed",
            "payloadStorage",
        },
        label,
    )
    kinds = registry.get("supportedKinds")
    if not isinstance(kinds, list) or len(kinds) != 3 or set(kinds) != EXPECTED_REGISTRY_KINDS:
        raise ContractFailure(
            "LOGS-URTLOG-REGISTRY",
            f"{label}.registry.supportedKinds",
            "supportedKinds must contain uri, url, and urn",
        )
    _require_bool_const(registry, "secretsInUrlsOrFixtures", False, f"{label}.registry", "LOGS-URTLOG-REGISTRY")
    _require_bool_const(registry, "accessContextFailClosed", True, f"{label}.registry", "LOGS-URTLOG-REGISTRY")
    _require_str_const(registry, "payloadStorage", "urn-vault-separated", f"{label}.registry", "LOGS-URTLOG-REGISTRY")

    decision = _require_closed_dict(
        doc,
        "decisionContextSlice",
        {
            "targetRole",
            "maxSliceBytes",
            "lookupMode",
            "singleUrnIsolationForEntityQueries",
            "forbidUnfilteredDump",
            "grantsExecutionAuthority",
        },
        label,
    )
    _require_str_const(decision, "targetRole", "decision", f"{label}.decisionContextSlice", "LOGS-URTLOG-SLICE")
    max_bytes = decision.get("maxSliceBytes")
    if not _is_strict_int(max_bytes) or not (128 <= max_bytes <= 1024):
        raise ContractFailure(
            "LOGS-URTLOG-SLICE-BUDGET",
            f"{label}.decisionContextSlice.maxSliceBytes",
            "maxSliceBytes must be an integer in 128..1024 (recommended <= 600 for 3B decision models)",
        )
    if decision.get("lookupMode") not in ALLOWED_LOOKUP_MODES:
        raise ContractFailure(
            "LOGS-URTLOG-SLICE",
            f"{label}.decisionContextSlice.lookupMode",
            f"lookupMode must be one of {sorted(ALLOWED_LOOKUP_MODES)}",
        )
    _require_bool_const(decision, "singleUrnIsolationForEntityQueries", True, f"{label}.decisionContextSlice", "LOGS-URTLOG-SLICE")
    _require_bool_const(decision, "forbidUnfilteredDump", True, f"{label}.decisionContextSlice", "LOGS-URTLOG-SLICE")
    _require_bool_const(decision, "grantsExecutionAuthority", False, f"{label}.decisionContextSlice", "LOGS-URTLOG-SLICE")

    verification = _require_closed_dict(
        doc,
        "verification",
        {
            "requireOfflineFailOpenTests",
            "requireLiveIntegrationTests",
            "forbidPytestMarkSkip",
            "optionalDependencyGuard",
            "forbidSecretLikeTestLiterals",
        },
        label,
    )
    _require_bool_const(verification, "requireOfflineFailOpenTests", True, f"{label}.verification", "LOGS-URTLOG-VERIFY")
    _require_bool_const(verification, "requireLiveIntegrationTests", True, f"{label}.verification", "LOGS-URTLOG-VERIFY")
    _require_bool_const(verification, "forbidPytestMarkSkip", True, f"{label}.verification", "LOGS-URTLOG-VERIFY")
    _require_str_const(verification, "optionalDependencyGuard", "in-body-find-spec", f"{label}.verification", "LOGS-URTLOG-VERIFY")
    _require_bool_const(verification, "forbidSecretLikeTestLiterals", True, f"{label}.verification", "LOGS-URTLOG-VERIFY")


def validate_urtlog_bridge_profile(
    root: Path, profile_path: Path | None = None
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    schema_sha = ""
    profile_sha = ""
    try:
        schema_file = confined_file(
            root, str(URTLOG_BRIDGE_SCHEMA_PATH), "LOGS-URTLOG-SCHEMA-PATH"
        )
        schema_doc = read_json(
            schema_file,
            rule="LOGS-URTLOG-SCHEMA-JSON",
            label=str(URTLOG_BRIDGE_SCHEMA_PATH),
            max_bytes=MAX_PROFILE_BYTES,
        )
        validate_urtlog_bridge_schema_doc(schema_doc, str(URTLOG_BRIDGE_SCHEMA_PATH))
        schema_sha = sha256_file(schema_file)

        if profile_path is None:
            target = confined_file(
                root, str(URTLOG_BRIDGE_PROFILE_PATH), "LOGS-URTLOG-PROFILE-PATH"
            )
            label = str(URTLOG_BRIDGE_PROFILE_PATH)
        else:
            target = profile_path
            label = str(profile_path)
            if target.is_symlink() or any(
                parent.is_symlink() for parent in target.parents
            ):
                raise ContractFailure(
                    "LOGS-URTLOG-PROFILE-SYMLINK",
                    label,
                    "refusing symlinked profile path",
                )
        profile_doc = read_json(
            target,
            rule="LOGS-URTLOG-PROFILE-JSON",
            label=label,
            max_bytes=MAX_PROFILE_BYTES,
        )
        validate_urtlog_bridge_profile_doc(profile_doc, label)
        profile_sha = sha256_file(target)
    except ContractFailure as error:
        findings.append(asdict(finding(error)))
    return {
        "schema": "wellmanifest.logs/urtlog-bridge-validation/v1",
        "valid": not findings,
        "schemaSha256": schema_sha,
        "profileSha256": profile_sha,
        "findings": findings,
    }
