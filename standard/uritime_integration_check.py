"""Dependency-free validator for wellmanifest.logs/uritime-integration-profile/v1."""

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

URITIME_INTEGRATION_SCHEMA_PATH = Path("contracts/uritime-integration.schema.v1.json")
URITIME_INTEGRATION_PROFILE_PATH = Path("contracts/uritime-integration.profile.v1.json")
MAX_PROFILE_BYTES = 65536
SEMVER_RE = re.compile(r"\A[0-9]+\.[0-9]+\.[0-9]+\Z")
REPO_RE = re.compile(r"\A[a-z0-9-]+/[a-z0-9-]+\Z")
ADOPT_RE = re.compile(r"\Awellmanifest/[a-z0-9-]+\Z")
ENV_VAR_RE = re.compile(r"\A[A-Z][A-Z0-9_]+\Z")
EXPECTED_HORIZONS = ["H0_REFLEX", "H1_TACTICAL", "H2_OPERATIONAL", "H3_ETERNAL"]
EXPECTED_LAZY_MODULES = {"uritime", "uritime_urt", "urtlog"}
EXPECTED_EVENT_STATUSES = {
    "planned", "started", "succeeded", "failed", "unknown", "canceled"
}
EXPECTED_READ_ONLY_EFFECTS = {"pure", "read", "query", "fs:read", "docker:read"}

_ROOT_FIELDS = {
    "$schema", "schema", "version", "extendsProfile", "placement",
    "temporalOwnership", "packaging", "dualModeTelemetry", "storageDurability",
    "resilienceAndAdmission", "decisionModelRuntime", "ecosystemBoundaries",
    "verification",
}

_SECTION_SPECS: list[tuple[str, set[str], str, dict[str, Any]]] = [
    (
        "temporalOwnership",
        {
            "soleTimeOwner", "forbidCompetingScheduler", "horizons",
            "requireExplicitAwareUtcNow", "freezeMaterializerConfig",
            "targetIdentityMode", "requireOccurrenceIdDeduplication",
            "requireGenerationBoundFreshness",
        },
        "LOGS-URITIME-TEMPORAL",
        {
            "soleTimeOwner": "uritime",
            "forbidCompetingScheduler": True,
            "horizons": EXPECTED_HORIZONS,
            "requireExplicitAwareUtcNow": True,
            "freezeMaterializerConfig": True,
            "targetIdentityMode": "uuid-and-generation",
            "requireOccurrenceIdDeduplication": True,
            "requireGenerationBoundFreshness": True,
        },
    ),
    (
        "verification",
        {
            "requireOfflineFailOpenTests", "requireLiveIntegrationTests",
            "requireConcurrentWriteTests", "forbidPytestMarkSkip",
            "optionalDependencyGuard", "forbidSecretLikeTestLiterals",
        },
        "LOGS-URITIME-VERIFY",
        {
            "requireOfflineFailOpenTests": True,
            "requireLiveIntegrationTests": True,
            "requireConcurrentWriteTests": True,
            "forbidPytestMarkSkip": True,
            "optionalDependencyGuard": "in-body-find-spec",
            "forbidSecretLikeTestLiterals": True,
        },
    ),
]


def _is_strict_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _require_consts(
    obj: dict[str, Any], consts: dict[str, Any], label: str, rule: str
) -> None:
    for key, expected in consts.items():
        actual = obj.get(key)
        if isinstance(expected, bool):
            if actual is not expected:
                raise ContractFailure(rule, label, f"{key} must be {str(expected).lower()}")
        elif actual != expected:
            raise ContractFailure(rule, label, f"{key} must equal {expected!r}")


def _require_int_range(
    obj: dict[str, Any], key: str, low: int, high: int, label: str, rule: str
) -> None:
    value = obj.get(key)
    if not _is_strict_int(value) or not (low <= value <= high):
        raise ContractFailure(
            rule, f"{label}.{key}", f"{key} must be an integer in {low}..{high}"
        )


def _require_closed_dict(
    parent: dict[str, Any], key: str, required_keys: set[str], label: str
) -> dict[str, Any]:
    val = parent.get(key)
    if not isinstance(val, dict):
        raise ContractFailure("LOGS-URITIME-TYPE", label, f"{key} must be an object")
    exact_fields(val, required_keys, rule="LOGS-URITIME-FIELDS", path=f"{label}.{key}")
    return val


def _validate_unique_str_list(
    values: Any,
    *,
    min_len: int,
    max_len: int,
    label: str,
    rule: str,
    pattern: re.Pattern[str] | None = None,
    allowed_set: set[str] | None = None,
    required_subset: set[str] | None = None,
) -> list[str]:
    if (
        not isinstance(values, list)
        or not (min_len <= len(values) <= max_len)
        or len(set(values)) != len(values)
        or not all(isinstance(item, str) for item in values)
    ):
        raise ContractFailure(rule, label, f"expected {min_len}..{max_len} unique string entries")
    if pattern is not None and not all(pattern.fullmatch(x) for x in values):
        raise ContractFailure(rule, label, "entry failed pattern validation")
    if allowed_set is not None and not set(values).issubset(allowed_set):
        raise ContractFailure(rule, label, f"entries must be drawn from {sorted(allowed_set)}")
    if required_subset is not None and not required_subset.issubset(values):
        raise ContractFailure(rule, label, f"entries must include {sorted(required_subset)}")
    return values


def validate_uritime_integration_schema_doc(schema_doc: Any, label: str) -> None:
    if not isinstance(schema_doc, dict):
        raise ContractFailure("LOGS-URITIME-SCHEMA", label, "schema root must be an object")
    if schema_doc.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        raise ContractFailure("LOGS-URITIME-SCHEMA", label, "unsupported JSON Schema dialect")
    if schema_doc.get("additionalProperties") is not False:
        raise ContractFailure("LOGS-URITIME-SCHEMA", label, "schema root must close additionalProperties")
    stack: list[tuple[Any, str]] = [(schema_doc, label)]
    while stack:
        node, where = stack.pop()
        if isinstance(node, dict):
            if node.get("type") == "object" and node.get("additionalProperties") is not False:
                raise ContractFailure(
                    "LOGS-URITIME-SCHEMA-CLOSED",
                    where,
                    "every object subschema must set additionalProperties=false",
                )
            for key, child in node.items():
                if isinstance(child, (dict, list)):
                    stack.append((child, f"{where}.{key}"))
        elif isinstance(node, list):
            for idx, child in enumerate(node):
                if isinstance(child, (dict, list)):
                    stack.append((child, f"{where}[{idx}]"))


def _validate_sections(doc: dict[str, Any], label: str) -> None:
    placement = _require_closed_dict(
        doc, "placement", {"home", "shape", "runtimeImplementations", "adopt"}, label
    )
    _require_consts(placement, {"home": "wellmanifest", "shape": "domain_pack"}, f"{label}.placement", "LOGS-URITIME-PLACEMENT")
    _validate_unique_str_list(
        placement.get("runtimeImplementations"), min_len=1, max_len=24,
        label=f"{label}.placement.runtimeImplementations", rule="LOGS-URITIME-PLACEMENT",
        pattern=REPO_RE, required_subset={"uritime/uritime", "uritime/urt", "uritime/urtlog"},
    )
    _validate_unique_str_list(
        placement.get("adopt"), min_len=1, max_len=16,
        label=f"{label}.placement.adopt", rule="LOGS-URITIME-PLACEMENT",
        pattern=ADOPT_RE, required_subset={"wellmanifest/logs", "wellmanifest/autonomy"},
    )

    for section_key, req_keys, rule, consts in _SECTION_SPECS:
        sec = _require_closed_dict(doc, section_key, req_keys, label)
        _require_consts(sec, consts, f"{label}.{section_key}", rule)

    packaging = _require_closed_dict(
        doc, "packaging",
        {
            "uritimeExtraName", "urtlogExtraName", "mandatoryRuntimeDependency",
            "lazyImportModules", "optInEnvVars", "failOpenOnMissingOrError",
            "mutateTrackedRepoFiles",
        },
        label,
    )
    _require_consts(
        packaging,
        {
            "uritimeExtraName": "uritime",
            "urtlogExtraName": "urtlog",
            "mandatoryRuntimeDependency": False,
            "failOpenOnMissingOrError": True,
            "mutateTrackedRepoFiles": False,
        },
        f"{label}.packaging", "LOGS-URITIME-PACKAGING",
    )
    _validate_unique_str_list(
        packaging.get("lazyImportModules"), min_len=3, max_len=3,
        label=f"{label}.packaging.lazyImportModules", rule="LOGS-URITIME-PACKAGING",
        allowed_set=EXPECTED_LAZY_MODULES, required_subset=EXPECTED_LAZY_MODULES,
    )
    _validate_unique_str_list(
        packaging.get("optInEnvVars"), min_len=1, max_len=8,
        label=f"{label}.packaging.optInEnvVars", rule="LOGS-URITIME-PACKAGING",
        pattern=ENV_VAR_RE, required_subset={"URTLOG_STATE_DIR"},
    )

    telemetry = _require_closed_dict(
        doc, "dualModeTelemetry",
        {
            "forbidLogOnlyAdoption", "requirePlanBeforeEffect", "requireCausationLink",
            "requireAccessAudit", "planGrantsAuthority", "allowedEventStatuses",
            "blockedStateMapping",
        },
        label,
    )
    _require_consts(
        telemetry,
        {
            "forbidLogOnlyAdoption": True,
            "requirePlanBeforeEffect": True,
            "requireCausationLink": True,
            "requireAccessAudit": True,
            "planGrantsAuthority": False,
        },
        f"{label}.dualModeTelemetry", "LOGS-URITIME-TELEMETRY",
    )
    _validate_unique_str_list(
        telemetry.get("allowedEventStatuses"),
        min_len=len(EXPECTED_EVENT_STATUSES), max_len=len(EXPECTED_EVENT_STATUSES),
        label=f"{label}.dualModeTelemetry.allowedEventStatuses", rule="LOGS-URITIME-TELEMETRY",
        allowed_set=EXPECTED_EVENT_STATUSES, required_subset=EXPECTED_EVENT_STATUSES,
    )
    blocked = _require_closed_dict(
        telemetry, "blockedStateMapping",
        {"eventStatus", "logType", "metadataStatusField", "metadataStatusValue"},
        f"{label}.dualModeTelemetry",
    )
    _require_consts(
        blocked,
        {"eventStatus": "unknown", "logType": "audit", "metadataStatusField": "status", "metadataStatusValue": "blocked"},
        f"{label}.dualModeTelemetry.blockedStateMapping", "LOGS-URITIME-TELEMETRY",
    )

    storage = _require_closed_dict(
        doc, "storageDurability",
        {"requireCrossProcessLock", "requireFsyncAtomicReplace", "cleanupTempOnError", "sqliteJournalMode", "sqliteBusyRetryMaxAttempts"},
        label,
    )
    _require_consts(
        storage,
        {"requireCrossProcessLock": True, "requireFsyncAtomicReplace": True, "cleanupTempOnError": True, "sqliteJournalMode": "WAL"},
        f"{label}.storageDurability", "LOGS-URITIME-STORAGE",
    )
    _require_int_range(storage, "sqliteBusyRetryMaxAttempts", 2, 8, f"{label}.storageDurability", "LOGS-URITIME-STORAGE")

    resilience = _require_closed_dict(
        doc, "resilienceAndAdmission",
        {"separateTransientFromPermanentFailures", "hostAdmissionSignal", "forbidLoadavgOnlyAdmission", "externalReadRetryMaxAttempts", "abstentionBackoffRequired"},
        label,
    )
    _require_consts(
        resilience,
        {"separateTransientFromPermanentFailures": True, "hostAdmissionSignal": "psi-and-runnable-contention", "forbidLoadavgOnlyAdmission": True, "abstentionBackoffRequired": True},
        f"{label}.resilienceAndAdmission", "LOGS-URITIME-RESILIENCE",
    )
    _require_int_range(resilience, "externalReadRetryMaxAttempts", 2, 5, f"{label}.resilienceAndAdmission", "LOGS-URITIME-RESILIENCE")

    decision = _require_closed_dict(
        doc, "decisionModelRuntime",
        {"targetRole", "maxSliceBytes", "requireModelAliasNormalization", "requireLiveUrtlogBriefInjection", "singleUrnIsolationForEntityQueries", "forbidUnfilteredDump", "advisoryOnly", "executionAllowed", "readOnlyEffects"},
        label,
    )
    _require_consts(
        decision,
        {
            "targetRole": "decision",
            "requireModelAliasNormalization": True,
            "requireLiveUrtlogBriefInjection": True,
            "singleUrnIsolationForEntityQueries": True,
            "forbidUnfilteredDump": True,
            "advisoryOnly": True,
            "executionAllowed": False,
        },
        f"{label}.decisionModelRuntime", "LOGS-URITIME-DECISION",
    )
    _require_int_range(decision, "maxSliceBytes", 128, 1024, f"{label}.decisionModelRuntime", "LOGS-URITIME-DECISION")
    _validate_unique_str_list(
        decision.get("readOnlyEffects"), min_len=2, max_len=len(EXPECTED_READ_ONLY_EFFECTS),
        label=f"{label}.decisionModelRuntime.readOnlyEffects", rule="LOGS-URITIME-DECISION",
        allowed_set=EXPECTED_READ_ONLY_EFFECTS, required_subset={"pure", "read"},
    )

    boundaries = _require_closed_dict(
        doc, "ecosystemBoundaries",
        {
            "polycellRole", "autonomSynthesisTrigger", "autonomExecutesUnpromotedCandidate",
            "forgeRole", "controllerRole", "validatorRole",
            "grantsExecutionAuthority", "grantsLeaseAuthority", "grantsMergeAuthority",
        },
        label,
    )
    _require_consts(
        boundaries,
        {
            "polycellRole": "pure-deterministic-classifier",
            "autonomSynthesisTrigger": "NO_MATCH_ONLY",
            "autonomExecutesUnpromotedCandidate": False,
            "forgeRole": "isolated-candidate-qualification",
            "controllerRole": "lease-fenced-execution",
            "validatorRole": "independent-exact-head-approval-and-merge",
        },
        f"{label}.ecosystemBoundaries", "LOGS-URITIME-BOUNDARY",
    )
    _require_consts(
        boundaries,
        {"grantsExecutionAuthority": False, "grantsLeaseAuthority": False, "grantsMergeAuthority": False},
        f"{label}.ecosystemBoundaries", "LOGS-URITIME-AUTHORITY",
    )


def validate_uritime_integration_profile_doc(doc: Any, label: str) -> None:
    if not isinstance(doc, dict):
        raise ContractFailure("LOGS-URITIME-PROFILE", label, "profile root must be an object")
    exact_fields(doc, _ROOT_FIELDS, rule="LOGS-URITIME-FIELDS", path=label)
    _require_consts(doc, {"$schema": "./uritime-integration.schema.v1.json"}, label, "LOGS-URITIME-SCHEMA-REF")
    _require_consts(doc, {"schema": "wellmanifest.logs/uritime-integration-profile/v1"}, label, "LOGS-URITIME-SCHEMA-ID")
    version = doc.get("version")
    if not isinstance(version, str) or SEMVER_RE.fullmatch(version) is None:
        raise ContractFailure("LOGS-URITIME-VERSION", label, "version must be SemVer X.Y.Z")
    _require_consts(doc, {"extendsProfile": "wellmanifest.logs/urtlog-bridge-profile/v1"}, label, "LOGS-URITIME-EXTENDS")
    _validate_sections(doc, label)


def validate_uritime_integration_profile(
    root: Path, profile_path: Path | None = None
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    schema_sha = ""
    profile_sha = ""
    try:
        schema_file = confined_file(root, str(URITIME_INTEGRATION_SCHEMA_PATH), "LOGS-URITIME-SCHEMA-PATH")
        schema_doc = read_json(
            schema_file, rule="LOGS-URITIME-SCHEMA-JSON",
            label=str(URITIME_INTEGRATION_SCHEMA_PATH), max_bytes=MAX_PROFILE_BYTES,
        )
        validate_uritime_integration_schema_doc(schema_doc, str(URITIME_INTEGRATION_SCHEMA_PATH))
        schema_sha = sha256_file(schema_file)

        if profile_path is None:
            target = confined_file(root, str(URITIME_INTEGRATION_PROFILE_PATH), "LOGS-URITIME-PROFILE-PATH")
            label = str(URITIME_INTEGRATION_PROFILE_PATH)
        else:
            target = profile_path
            label = str(profile_path)
            if target.is_symlink() or any(parent.is_symlink() for parent in target.parents):
                raise ContractFailure("LOGS-URITIME-PROFILE-SYMLINK", label, "refusing symlinked profile path")
        profile_doc = read_json(target, rule="LOGS-URITIME-PROFILE-JSON", label=label, max_bytes=MAX_PROFILE_BYTES)
        validate_uritime_integration_profile_doc(profile_doc, label)
        profile_sha = sha256_file(target)
    except ContractFailure as error:
        findings.append(asdict(finding(error)))
    return {
        "schema": "wellmanifest.logs/uritime-integration-validation/v1",
        "valid": not findings,
        "schemaSha256": schema_sha,
        "profileSha256": profile_sha,
        "findings": findings,
    }
