"""Positive and adversarial tests for wellmanifest.logs/urtlog-bridge-profile/v1."""

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
from standard.urtlog_bridge_check import (
    URTLOG_BRIDGE_PROFILE_PATH,
    validate_urtlog_bridge_profile,
)


def _load_reference_profile() -> dict[str, Any]:
    return json.loads((_REPO_ROOT / URTLOG_BRIDGE_PROFILE_PATH).read_text(encoding="utf-8"))


class UrtlogBridgeProfileTests(unittest.TestCase):
    def test_bundled_schema_and_profile_pass(self) -> None:
        result = validate_urtlog_bridge_profile(_REPO_ROOT)
        self.assertTrue(result["valid"], result)
        self.assertEqual(len(result["schemaSha256"]), 64)
        self.assertEqual(len(result["profileSha256"]), 64)
        self.assertEqual(
            lc.main(["urtlog-bridge", "--root", str(_REPO_ROOT), "--format", "json"]),
            0,
        )

    def _assert_rejected(self, profile: dict[str, Any], expected_rule: str) -> None:
        with tempfile.TemporaryDirectory(prefix="urtlog-profile-") as raw_tmp:
            path = Path(raw_tmp) / "profile.json"
            path.write_text(json.dumps(profile), encoding="utf-8")
            result = validate_urtlog_bridge_profile(_REPO_ROOT, path)
            self.assertFalse(result["valid"], result)
            self.assertEqual(result["findings"][0]["rule"], expected_rule, result)

    def test_rejects_mandatory_dependency_or_fail_closed_host_breakage(self) -> None:
        bad = _load_reference_profile()
        bad["packaging"]["mandatoryRuntimeDependency"] = True
        self._assert_rejected(bad, "LOGS-URTLOG-PACKAGING")

        bad2 = _load_reference_profile()
        bad2["packaging"]["failOpenOnMissingOrError"] = False
        self._assert_rejected(bad2, "LOGS-URTLOG-PACKAGING")

    def test_rejects_invalid_event_status_or_wrong_blocked_mapping(self) -> None:
        bad = _load_reference_profile()
        bad["temporalModel"]["allowedEventStatuses"] = [
            "planned",
            "started",
            "succeeded",
            "failed",
            "blocked",
            "canceled",
        ]
        self._assert_rejected(bad, "LOGS-URTLOG-STATUS")

        bad2 = _load_reference_profile()
        bad2["temporalModel"]["blockedStateMapping"]["eventStatus"] = "failed"
        self._assert_rejected(bad2, "LOGS-URTLOG-BLOCKED-MAP")

    def test_rejects_unbounded_decision_slice_and_bool_budget(self) -> None:
        for bad_bytes in (64, 2048, True, False):
            bad = copy.deepcopy(_load_reference_profile())
            bad["decisionContextSlice"]["maxSliceBytes"] = bad_bytes
            self._assert_rejected(bad, "LOGS-URTLOG-SLICE-BUDGET")

        bad_dump = _load_reference_profile()
        bad_dump["decisionContextSlice"]["forbidUnfilteredDump"] = False
        self._assert_rejected(bad_dump, "LOGS-URTLOG-SLICE")

    def test_rejects_pytest_skip_allowance_unknown_fields_and_symlinks(self) -> None:
        bad_skip = _load_reference_profile()
        bad_skip["verification"]["forbidPytestMarkSkip"] = False
        self._assert_rejected(bad_skip, "LOGS-URTLOG-VERIFY")

        bad_extra = _load_reference_profile()
        bad_extra["unexpectedKey"] = 1
        self._assert_rejected(bad_extra, "LOGS-URTLOG-FIELDS")

        with tempfile.TemporaryDirectory(prefix="urtlog-sym-") as raw_tmp:
            tmp = Path(raw_tmp)
            real = tmp / "real.json"
            real.write_text(json.dumps(_load_reference_profile()), encoding="utf-8")
            link = tmp / "link.json"
            link.symlink_to(real)
            res = validate_urtlog_bridge_profile(_REPO_ROOT, link)
            self.assertFalse(res["valid"])
            self.assertEqual(res["findings"][0]["rule"], "LOGS-URTLOG-PROFILE-SYMLINK")
