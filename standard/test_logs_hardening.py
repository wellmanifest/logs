"""Hardening unit tests for wellmanifest.logs/v1 conformance modules."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from standard import logs_check as lc

REPO_ROOT = Path(__file__).resolve().parents[1]


class LogsHardeningTests(unittest.TestCase):
    def test_baseline_and_self_test_pass(self) -> None:
        res = lc.validate_repository(REPO_ROOT)
        self.assertTrue(res["valid"], res)
        self.assertEqual(
            lc.main(["validate", "--root", str(REPO_ROOT), "--format", "json"]), 0
        )

    def test_lone_utf16_surrogate_fails_closed_without_crash(self) -> None:
        with tempfile.TemporaryDirectory(prefix="logs-surrogate-") as raw_tmp:
            tmp = Path(raw_tmp)
            repo = tmp / "repo"
            lc.copy_fixture(REPO_ROOT, repo)
            stream = repo / "logs/control.jsonl"
            stream.write_bytes(b'{"schema":"\\ud800"}\n')
            res = lc.validate_repository(repo)
            self.assertFalse(res["valid"])
            self.assertEqual(res["findings"][0]["rule"], "LOGS-EVENT-JSON")

            schema_file = tmp / "surrogate-schema.json"
            schema_file.write_bytes(b'{"$id":"\\ud800"}\n')
            adopt = lc.validate_adopted_event_schema(REPO_ROOT, schema_file)
            self.assertFalse(adopt["valid"])
            self.assertEqual(adopt["findings"][0]["rule"], "LOGS-ADOPTION-SCHEMA-JSON")

            with self.assertRaises(lc.ContractFailure) as ctx:
                lc.canonical({"bad": "\ud800"})
            self.assertEqual(ctx.exception.rule, "LOGS-CANONICAL-STRING")

    def test_duplicate_keys_float_overflow_and_depth_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="logs-json-") as raw_tmp:
            tmp = Path(raw_tmp)
            dup_req = tmp / "dup.json"
            dup_req.write_text(
                '{"schema":"wellmanifest.logs/request/v1","schema":"wellmanifest.logs/request/v1",'
                '"operation":"inspect","processRef":"logs://repository/contracts/query/inspect"}\n',
                encoding="utf-8",
            )
            self.assertEqual(
                lc.main(
                    ["request", "--root", str(REPO_ROOT), "--request", str(dup_req)]
                ),
                1,
            )

            overflow_schema = tmp / "overflow.json"
            overflow_schema.write_text('{"limit": 1e309}\n', encoding="utf-8")
            adopt = lc.validate_adopted_event_schema(REPO_ROOT, overflow_schema)
            self.assertFalse(adopt["valid"])
            self.assertEqual(adopt["findings"][0]["rule"], "LOGS-ADOPTION-SCHEMA-JSON")

            deep_schema = tmp / "deep.json"
            deep_schema.write_text("[" * 200 + "]" * 200 + "\n", encoding="utf-8")
            deep_res = lc.validate_adopted_event_schema(REPO_ROOT, deep_schema)
            self.assertFalse(deep_res["valid"])
            self.assertEqual(
                deep_res["findings"][0]["rule"], "LOGS-ADOPTION-SCHEMA-JSON"
            )

    def test_symlink_leaf_and_parent_traversal_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="logs-sym-") as raw_tmp:
            tmp = Path(raw_tmp)
            bundle, contract_sha = lc.load_contract(REPO_ROOT)

            real_schema = tmp / "real-event.schema.json"
            real_schema.write_text(
                json.dumps(bundle["schemas"]["event"]), encoding="utf-8"
            )
            sym_schema = tmp / "sym-event.schema.json"
            sym_schema.symlink_to(real_schema)
            self.assertEqual(
                lc.main(
                    [
                        "adoption",
                        "--root",
                        str(REPO_ROOT),
                        "--event-schema",
                        str(sym_schema),
                    ]
                ),
                1,
            )

            adopter = tmp / "adopter"
            catalog = lc.write_adopter_error_fixture(adopter, contract_sha)
            sym_catalog = tmp / "sym-catalog.json"
            sym_catalog.symlink_to(catalog)
            self.assertEqual(
                lc.main(
                    [
                        "error-adoption",
                        "--root",
                        str(REPO_ROOT),
                        "--catalog",
                        str(sym_catalog),
                    ]
                ),
                1,
            )

            # Lexical sym_dir/.. escape in adopter errorsDirectory must fail closed
            outside = tmp / "outside"
            outside.mkdir()
            (adopter / "sym_dir").symlink_to(outside)
            payload = json.loads(catalog.read_text("utf-8"))
            payload["errorsDirectory"] = "sym_dir/../errors"
            catalog.write_text(json.dumps(payload), encoding="utf-8")
            escaped = lc.validate_adopted_error_catalog(REPO_ROOT, catalog)
            self.assertFalse(escaped["valid"])

            # Symlinked logs stream and symlinked evidence must fail closed
            repo_sym = tmp / "repo-sym"
            lc.copy_fixture(REPO_ROOT, repo_sym)
            real_ctrl = tmp / "external.jsonl"
            real_ctrl.write_bytes((repo_sym / "logs/control.jsonl").read_bytes())
            (repo_sym / "logs/control.jsonl").unlink()
            (repo_sym / "logs/control.jsonl").symlink_to(real_ctrl)
            lc.assert_invalid(repo_sym, "LOGS-STORE-READ")

            repo_ev = tmp / "repo-ev"
            lc.copy_fixture(REPO_ROOT, repo_ev)
            ext_contract = tmp / "ext-contract.json"
            ext_contract.write_bytes(
                (repo_ev / "contracts/logs.contract.json").read_bytes()
            )
            (repo_ev / "contracts/logs.contract.json").unlink()
            (repo_ev / "contracts/logs.contract.json").symlink_to(ext_contract)
            lc.assert_invalid(repo_ev, "LOGS-EVENT-EVIDENCE")

    def test_fifo_inputs_do_not_block(self) -> None:
        with tempfile.TemporaryDirectory(prefix="logs-fifo-") as raw_tmp:
            tmp = Path(raw_tmp)
            fifo_path = tmp / "pipe.json"
            os.mkfifo(fifo_path)
            adopt = lc.validate_adopted_event_schema(REPO_ROOT, fifo_path)
            self.assertFalse(adopt["valid"])
            self.assertEqual(adopt["findings"][0]["rule"], "LOGS-ADOPTION-SCHEMA-SIZE")
            self.assertEqual(
                lc.main(
                    ["request", "--root", str(REPO_ROOT), "--request", str(fifo_path)]
                ),
                1,
            )

    def test_diagnostic_endpoint_port_and_ipv6_bounds(self) -> None:
        base_diag = {
            "phase": "connecting",
            "status": "failed",
            "retryable": False,
            "attempt": 1,
            "attempts": 1,
            "durationMs": 5,
            "endpointRef": "https://[::1]:8443",
            "transportCode": None,
            "httpStatus": None,
            "remediationRefs": [],
            "traceId": None,
            "spanId": None,
        }
        lc.validate_diagnostic(base_diag, "test")
        for bad_endpoint in (
            "http://127.0.0.1:65536",
            "http://127.0.0.1:99999",
            "http://[:::]:8080",
            "http://[127.0.0.1]:8080",
            "http://example..test:8080",
        ):
            with self.assertRaises(lc.ContractFailure) as ctx:
                lc.validate_diagnostic(
                    {**base_diag, "endpointRef": bad_endpoint}, "test"
                )
            self.assertEqual(ctx.exception.rule, "LOGS-EVENT-DIAGNOSTIC")

    def test_self_causation_and_nanosecond_timestamp_and_control_chars(self) -> None:
        lc.require_datetime("2026-09-01T20:01:00.123456789Z", "test")
        with self.assertRaises(lc.ContractFailure):
            lc.require_datetime("2026-02-29T00:00:00Z", "test")

        with tempfile.TemporaryDirectory(prefix="logs-cause-") as raw_tmp:
            repo = Path(raw_tmp) / "repo"
            lc.copy_fixture(REPO_ROOT, repo)
            lc.rewrite_event(
                repo / "logs/control.jsonl",
                lambda ev: ev.update({"causationId": ev["eventId"]}),
            )
            lc.assert_invalid(repo, "LOGS-EVENT-CAUSATION")

            bundle, _ = lc.load_contract(REPO_ROOT)
            with self.assertRaises(lc.ContractFailure) as ctx:
                lc.validate_error_definition(
                    {
                        "schema": "wellmanifest.logs/error/v1",
                        "code": "ONEDEV-TEST-001",
                        "version": 1,
                        "severity": "WARNING",
                        "category": "CONCURRENCY",
                        "title": "Bad\x1b[31mtitle",
                        "meaning": "Valid meaning.",
                        "causes": ["Cause"],
                        "remediation": ["Fix"],
                        "verification": ["Check"],
                        "doNot": ["Avoid"],
                        "owner": "service:onedev",
                        "relatedEventTypes": ["error_raised"],
                    },
                    code="ONEDEV-TEST-001",
                    bundle=bundle,
                    path="errors/ONEDEV-TEST-001.md",
                )
            self.assertEqual(ctx.exception.rule, "LOGS-DOC-TEXT")


if __name__ == "__main__":
    unittest.main()
