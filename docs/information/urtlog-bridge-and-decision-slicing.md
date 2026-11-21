---
{
  "schema": "wellmanifest.docs/document/v1",
  "id": "urtlog-bridge-and-decision-slicing",
  "kind": "information",
  "version": 1,
  "title": "Opt-in URTLog telemetry bridge, UnifiedRegistry projection, and bounded decision-context slicing",
  "status": "accepted",
  "owner": "wellmanifest/logs",
  "scope": "repository",
  "created": "2026-11-21",
  "updated": "2026-11-21",
  "review_after": "2026-12-21",
  "source_revision": "b5c8790cdf3c25142264727a6b57ff6780279af7",
  "affected_repositories": [
    "wellmanifest/logs"
  ],
  "evidence": [
    "https://github.com/wellmanifest/logs/blob/b5c8790cdf3c25142264727a6b57ff6780279af7/contracts/logs.contract.v0.5.json",
    "https://github.com/heyasa/heyasa/pull/953",
    "https://github.com/semcod/planfile/pull/449",
    "https://github.com/oqllm/proxy/pull/38",
    "https://github.com/heyasa/willmux/pull/1008",
    "https://github.com/heyasa/willgui/pull/18"
  ]
}
---

# Opt-in URTLog telemetry bridge, UnifiedRegistry projection, and bounded decision-context slicing

<!-- docs:section purpose -->
## Purpose

Standardize how product repositories adopt opt-in `uritime/urtlog` operational
telemetry bridges (`URT × URI × URN_IN × URN_OUT`), `UnifiedRegistry`
URI/URL/URN projections, and bounded decision-context slices for fast small
LLMs (`roles.decision`, such as `d1:3b`). This profile extends
`wellmanifest/logs` additively through
`contracts/urtlog-bridge.schema.v1.json` and
`contracts/urtlog-bridge.profile.v1.json` without mutating immutable v0.2–v0.5
contracts or `proto/v0.5`.

<!-- docs:section scope -->
## Scope

`HOME wellmanifest`, `SHAPE domain_pack`: `wellmanifest/logs` owns the closed
profile schema, reference profile, conformance checker (`logs_check.py urtlog-bridge`),
and normative invariants. Concrete runtime stores, CLI hooks, HTTP endpoints,
and decision routers remain owned by adopting product repositories
(`uritime/urtlog`, `semcod/planfile`, `oqllm/proxy`, `heyasa/*`, `dockuri/*`,
`semcod/*`, `subactor/*`). Profile conformance proves contract alignment only;
it grants no execution, review, merge, or secret-access authority.

<!-- docs:section evidence -->
## Evidence

This contract codifies lessons from the 2026-11-21 cross-ecosystem rollout
(26 independently validated PRs across 16 repositories, including
`semcod/planfile#449`, `oqllm/proxy#38`, `heyasa/willmux#1008`,
`heyasa/willgui#18/#19`, and `heyasa/heyasa#953`) and a live A/B/C benchmark
against `oqllm-proxy` (`http://127.0.0.1:11439`, `d1:3b` via
`subllm.runtime_profile.GatewayClient`) on a real `planfile` dependency DAG
(`PLF-000`..`PLF-006`) and live registry entries with blind options:

| Context variant | Accuracy (blind options) | Avg logprob confidence (when correct) | Median latency | Median payload |
| --- | ---: | ---: | ---: | ---: |
| **A: Baseline (no `urtlog`)** | 2/7 (28.6%) | 0.7592 | 451.4 ms | 283 B |
| **B: Unfiltered `urtlog` dump** | 6/7 (85.7%) | 0.9743 | 1 069.6 ms (3.2x slower) | 9 738 B |
| **C: Compact B-tree prefix slice** | 6/7 (85.7%) | 0.9772 | 337.3 ms | 547 B (17.8x smaller) |
| **C+: Entity-scoped single-URN lookup (`B5`)** | 7/7 (100.0%) | 0.9214 | 345.2 ms (`B5`) | 402 B (`B5`) |

Three empirical failure modes drove the normative rules below:

1. **Invalid lifecycle status values:** `UrtEventRecord.status` accepts only
   `{"planned", "started", "succeeded", "failed", "unknown", "canceled"}`.
   Emitting `"blocked"` directly silently failed validation during `planfile block`.
2. **Small-model context overload and cross-ticket interference:** 3–10 KB
   unfiltered dumps slowed `d1:3b` 3.2x–7.7x and caused cross-ticket blocker
   confusion (`PLF-001` vs `PLF-002` in `B5`).
3. **Validator security and test-hygiene rejections:** `@pytest.mark.skip*`
   decorators and secret-like query literals (`token=`, `secret=`) in unit test
   fixtures were rejected by the independent Validator.

<!-- docs:section content -->
## Content

### 1. Opt-in packaging and fail-open host boundary

Adopters MUST keep `uritime-urtlog` strictly optional:

- Declare `[project.optional-dependencies] urtlog = ["uritime-urtlog>=0.3.0"]`
  (never in mandatory `dependencies`).
- Load `urtlog` lazily via `importlib.import_module("urtlog")` only when
  `URTLOG_STATE_DIR` is explicitly set in the runtime environment.
- Operate strictly **fail-open**: missing package, unset `URTLOG_STATE_DIR`,
  or transient store errors MUST return a structured disabled/error dict and
  MUST NEVER raise into or alter the primary CLI/service result.
- Never write operational store files into tracked Git repository paths.

### 2. Temporal 4-tuple (`URT × URI × URN_IN × URN_OUT`) and `PLAN` vs `LOG`

- `PLAN` records use `kind="intent"`, NEVER carry `status="succeeded"`, and
  NEVER grant execution authority.
- `LOG` records use `kind="event"` and link causally to prior plans/events via
  `causation_id`, `depends_on`, `input_urns`, and `output_urns`.
- `UrtEventRecord.status` MUST stay within the closed set
  `{"planned", "started", "succeeded", "failed", "unknown", "canceled"}`.
- Domain states such as `blocked` or `waiting_input` (for example
  `planfile ticket block`) MUST map to `status="unknown"` with `log_type="audit"`,
  preserving the domain state in `metadata["status"] = "blocked"` and in the
  corresponding `UnifiedRegistry` URN entry.

### 3. Unified URI/URL/URN registry and secret-free hygiene

- Register stable operational resources in `UnifiedRegistry` using `kind` in
  `{"uri", "url", "urn"}` (for example `urn:planfile:ticket:<ID>`,
  `willmux://cockpit/<kind>`, `proc://...`, or origin-only HTTP(S) URLs).
- Never embed credentials, bearer values, or secret-like query parameters in
  URLs, metadata, or test fixtures.
- Separate opaque `URN` metadata from raw payloads (`UrnVault`) and enforce
  fail-closed `AccessContext` filtering on all reads.

### 4. Bounded decision-context slicing (`<= 600` B for `roles.decision`)

- Small/fast decision roles (`roles.decision`, such as `d1:3b`) MUST NOT receive
  unfiltered JSON dumps of the store or registry.
- Keep injected decision state within `decisionContextSlice.maxSliceBytes`
  (**600 UTF-8 bytes** recommended, hard ceiling **1 024 B**), matching
  `wellmanifest/llm`'s `limits.maxDecisionSliceBytes`.
- Query via B-tree prefix (`op/planfile/ticket/...`, `kind="uri"`) for queue
  selection, and isolate to a **single entity URN** (`urn:planfile:ticket:<ID>`)
  plus direct DAG neighbors for entity-specific queries to eliminate
  cross-ticket attention interference.
- Sliced context is advisory observation only and grants no execution authority.

### 5. Dual-mode verification and Validator hygiene

- Every adopter bridge MUST provide both offline fail-open tests (verifying
  clean no-op when `URTLOG_STATE_DIR` is unset or `urtlog` is absent) and live
  integration tests against `UrtLogStore` / `UnifiedRegistry`.
- Guard live tests inside the test body using
  `if importlib.util.find_spec("urtlog") is None: return` — NEVER use
  `@pytest.mark.skip` or `@pytest.mark.skipif`.
- Use neutral query strings in URL sanitization tests (e.g. `?page=2&sort=asc#frag`),
  never secret-like parameter names.

### 6. Deterministic conformance check

Validate the bundled schema and reference profile (or an adopter's profile) via:

```bash
python3 standard/logs_check.py urtlog-bridge --root .
python3 standard/logs_check.py urtlog-bridge --root . --profile /path/to/profile.json --format json
```

<!-- docs:section limitations -->
## Limitations

1. `logs_check.py urtlog-bridge` validates profile structure, bounds, and
   invariants deterministically without inspecting an adopter's live Python
   runtime or SQLite store; runtime opt-in and fail-open behavior remain verified
   by each adopter's offline and live integration test suite.
2. The 2026-11-21 A/B/C benchmark evidence was measured on a single local
   `oqllm-proxy` instance (`d1:3b`) over 7 blind-option scenarios; larger models
   may tolerate larger slices but still benefit from prefix/single-URN scoping.
3. Adopting this profile does not modify immutable v0.2–v0.5 canonical event
   contracts or grant execution, review, or merge authority.

<!-- docs:section next_actions -->
## Next actions

1. Adopters integrating `uritime-urtlog` pin `contracts/urtlog-bridge.profile.v1.json`
   and run `python3 standard/logs_check.py urtlog-bridge --root .` in local checks
   alongside their offline/live bridge test suite.
2. Align small-model decision routing budgets (`<= 600` B) with `wellmanifest/llm`
   `limits.maxDecisionSliceBytes` during runtime canary rollouts.
3. Review this document by `2026-12-21` after production `URTLOG_STATE_DIR`
   canary telemetry is collected across `planfile`, `oqllm-proxy`, `willgui`,
   and `heyasa`.
