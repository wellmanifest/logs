"""Positive and adversarial tests for wellmanifest.logs/uritime-integration-profile/v1."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from standard import logs_check as lc
from standard.uritime_integration_check import (
    URITIME_INTEGRATION_PROFILE_PATH,
    validate_uritime_integration_profile,
)


def _load_reference_profile() -> dict[str, Any]:
    return json.loads(
        (_REPO_ROOT / URITIME_INTEGRATION_PROFILE_PATH).read_text(encoding="utf-8")
    )


class UritimeIntegrationProfileTests(unittest.TestCase):
    def test_bundled_schema_and_profile_pass(self) -> None:
        result = validate_uritime_integration_profile(_REPO_ROOT)
        self.assertTrue(result["valid"], result)
        self.assertEqual(len(result["schemaSha256"]), 64)
        self.assertEqual(len(result["profileSha256"]), 64)
        self.assertEqual(
            lc.main(
                ["uritime-integration", "--root", str(_REPO_ROOT), "--format", "json"]
            ),
            0,
        )

    def _assert_rejected(self, profile: dict[str, Any], expected_rule: str) -> None:
        with tempfile.TemporaryDirectory(prefix="uritime-profile-") as raw_tmp:
            path = Path(raw_tmp) / "profile.json"
            path.write_text(json.dumps(profile), encoding="utf-8")
            result = validate_uritime_integration_profile(_REPO_ROOT, path)
            self.assertFalse(result["valid"], result)
            self.assertEqual(result["findings"][0]["rule"], expected_rule, result)

    def test_rejects_temporal_ownership_violations(self) -> None:
        mutations = [
            lambda p: p["temporalOwnership"].update({"forbidCompetingScheduler": False}),
            lambda p: p["temporalOwnership"].update({"requireExplicitAwareUtcNow": False}),
            lambda p: p["temporalOwnership"].update({"requireOccurrenceIdDeduplication": False}),
            lambda p: p["temporalOwnership"].update({"requireGenerationBoundFreshness": False}),
            lambda p: p["temporalOwnership"].update({"horizons": ["H0_REFLEX", "H1_TACTICAL"]}),
        ]
        for mutate in mutations:
            bad = copy.deepcopy(_load_reference_profile())
            mutate(bad)
            self._assert_rejected(bad, "LOGS-URITIME-TEMPORAL")

    def test_rejects_mandatory_dependency_or_missing_opt_in_env(self) -> None:
        mutations = [
            lambda p: p["packaging"].update({"mandatoryRuntimeDependency": True}),
            lambda p: p["packaging"].update({"failOpenOnMissingOrError": False}),
            lambda p: p["packaging"].update({"optInEnvVars": ["CUSTOM_ONLY_ENV"]}),
            lambda p: p["packaging"].update({"lazyImportModules": ["urtlog", "uritime"]}),
        ]
        for mutate in mutations:
            bad = copy.deepcopy(_load_reference_profile())
            mutate(bad)
            self._assert_rejected(bad, "LOGS-URITIME-PACKAGING")

    def test_rejects_log_only_adoption_and_missing_causation_or_audit(self) -> None:
        mutations = [
            lambda p: p["dualModeTelemetry"].update({"forbidLogOnlyAdoption": False}),
            lambda p: p["dualModeTelemetry"].update({"requirePlanBeforeEffect": False}),
            lambda p: p["dualModeTelemetry"].update({"requireCausationLink": False}),
            lambda p: p["dualModeTelemetry"].update({"requireAccessAudit": False}),
            lambda p: p["dualModeTelemetry"]["blockedStateMapping"].update({"eventStatus": "failed"}),
        ]
        for mutate in mutations:
            bad = copy.deepcopy(_load_reference_profile())
            mutate(bad)
            self._assert_rejected(bad, "LOGS-URITIME-TELEMETRY")

    def test_rejects_unlocked_or_non_atomic_storage_and_bool_retries(self) -> None:
        mutations = [
            lambda p: p["storageDurability"].update({"requireCrossProcessLock": False}),
            lambda p: p["storageDurability"].update({"requireFsyncAtomicReplace": False}),
            lambda p: p["storageDurability"].update({"cleanupTempOnError": False}),
            lambda p: p["storageDurability"].update({"sqliteJournalMode": "DELETE"}),
            lambda p: p["storageDurability"].update({"sqliteBusyRetryMaxAttempts": True}),
            lambda p: p["storageDurability"].update({"sqliteBusyRetryMaxAttempts": 1}),
        ]
        for mutate in mutations:
            bad = copy.deepcopy(_load_reference_profile())
            mutate(bad)
            self._assert_rejected(bad, "LOGS-URITIME-STORAGE")

    def test_rejects_loadavg_only_admission_and_unseparated_failures(self) -> None:
        mutations = [
            lambda p: p["resilienceAndAdmission"].update({"forbidLoadavgOnlyAdmission": False}),
            lambda p: p["resilienceAndAdmission"].update({"separateTransientFromPermanentFailures": False}),
            lambda p: p["resilienceAndAdmission"].update({"abstentionBackoffRequired": False}),
            lambda p: p["resilienceAndAdmission"].update({"externalReadRetryMaxAttempts": False}),
            lambda p: p["resilienceAndAdmission"].update({"externalReadRetryMaxAttempts": 9}),
        ]
        for mutate in mutations:
            bad = copy.deepcopy(_load_reference_profile())
            mutate(bad)
            self._assert_rejected(bad, "LOGS-URITIME-RESILIENCE")

    def test_rejects_unnormalized_decision_model_and_unbounded_slices(self) -> None:
        mutations = [
            lambda p: p["decisionModelRuntime"].update({"requireModelAliasNormalization": False}),
            lambda p: p["decisionModelRuntime"].update({"requireLiveUrtlogBriefInjection": False}),
            lambda p: p["decisionModelRuntime"].update({"forbidUnfilteredDump": False}),
            lambda p: p["decisionModelRuntime"].update({"executionAllowed": True}),
            lambda p: p["decisionModelRuntime"].update({"maxSliceBytes": True}),
            lambda p: p["decisionModelRuntime"].update({"maxSliceBytes": 2048}),
        ]
        for mutate in mutations:
            bad = copy.deepcopy(_load_reference_profile())
            mutate(bad)
            self._assert_rejected(bad, "LOGS-URITIME-DECISION")

    def test_rejects_boundary_drift_and_authority_escalation(self) -> None:
        boundary_bad = _load_reference_profile()
        boundary_bad["ecosystemBoundaries"]["autonomSynthesisTrigger"] = "ALL_ABSTENTIONS"
        self._assert_rejected(boundary_bad, "LOGS-URITIME-BOUNDARY")

        boundary_exec = _load_reference_profile()
        boundary_exec["ecosystemBoundaries"]["autonomExecutesUnpromotedCandidate"] = True
        self._assert_rejected(boundary_exec, "LOGS-URITIME-BOUNDARY")

        for auth_key in (
            "grantsExecutionAuthority",
            "grantsLeaseAuthority",
            "grantsMergeAuthority",
        ):
            bad = copy.deepcopy(_load_reference_profile())
            bad["ecosystemBoundaries"][auth_key] = True
            self._assert_rejected(bad, "LOGS-URITIME-AUTHORITY")

    def test_rejects_verify_gaps_unknown_fields_and_symlinks(self) -> None:
        bad_verify = _load_reference_profile()
        bad_verify["verification"]["requireConcurrentWriteTests"] = False
        self._assert_rejected(bad_verify, "LOGS-URITIME-VERIFY")

        bad_skip = _load_reference_profile()
        bad_skip["verification"]["forbidPytestMarkSkip"] = False
        self._assert_rejected(bad_skip, "LOGS-URITIME-VERIFY")

        bad_extra = _load_reference_profile()
        bad_extra["unexpectedKey"] = 1
        self._assert_rejected(bad_extra, "LOGS-URITIME-FIELDS")

        with tempfile.TemporaryDirectory(prefix="uritime-sym-") as raw_tmp:
            tmp = Path(raw_tmp)
            real = tmp / "real.json"
            real.write_text(json.dumps(_load_reference_profile()), encoding="utf-8")
            link = tmp / "link.json"
            link.symlink_to(real)
            res = validate_uritime_integration_profile(_REPO_ROOT, link)
            self.assertFalse(res["valid"])
            self.assertEqual(res["findings"][0]["rule"], "LOGS-URITIME-PROFILE-SYMLINK")
