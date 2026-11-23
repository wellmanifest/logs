---
{
  "schema": "wellmanifest.docs/document/v1",
  "id": "uritime-project-integration",
  "kind": "information",
  "version": 1,
  "title": "Project integration standard for uritime, uritime-urt, and uritime-urtlog across Polycell, Autonom, Forge, and Autonomy controllers",
  "status": "accepted",
  "owner": "wellmanifest/logs",
  "scope": "repository",
  "created": "2026-11-23",
  "updated": "2026-11-23",
  "review_after": "2026-12-23",
  "source_revision": "45b9672c3ae413f3b05af5c90986c478a899e3b3",
  "affected_repositories": [
    "wellmanifest/logs"
  ],
  "evidence": [
    "https://github.com/wellmanifest/logs/pull/35",
    "https://github.com/heyasa/heyasa/pull/877",
    "https://github.com/heyasa/heyasa/pull/953",
    "https://github.com/heyasa/heyasa/pull/1028",
    "https://github.com/heyasa/heyasa/pull/1029",
    "https://github.com/subactor/registry/pull/62",
    "https://github.com/subactor/validator-agent/pull/863"
  ]
}
---

# Project integration standard for uritime, uritime-urt, and uritime-urtlog across Polycell, Autonom, Forge, and Autonomy controllers

<!-- docs:section purpose -->
## Purpose

Define the complete normative adoption and integration standard
(`wellmanifest.logs/uritime-integration-profile/v1`) for deploying `uritime`,
`uritime-urt`, and `uritime-urtlog` inside product repositories. Whereas
`wellmanifest.logs/urtlog-bridge-profile/v1` specifies the wire shape of an
opt-in `urtlog` telemetry bridge and bounded decision slice, this standard closes
the operational gaps observed in multi-daemon autonomy loops: temporal
ownership, dual-mode `PLAN` → `LOG` execution lineage, cross-process ledger
durability, model alias normalization for small decision LLMs, PSI-aware host
admission, and clean separation from `wellmanifest/polycell`, `uritime/autonom`,
`Forge`, execution controllers, and the independent Validator App.

<!-- docs:section scope -->
## Scope

`HOME wellmanifest`, `SHAPE domain_pack`: `wellmanifest/logs` owns the closed
profile schema (`contracts/uritime-integration.schema.v1.json`), reference
profile (`contracts/uritime-integration.profile.v1.json`), dependency-free
checker (`standard/logs_check.py uritime-integration`), and normative rules.
Concrete runtime schedulers, event stores, classifiers, synthesizers, and
execution controllers remain owned by adopting repositories (`uritime/uritime`,
`uritime/urt`, `uritime/urtlog`, `uritime/autonom`, `uritime/autodo`,
`heyasa/heyasa`, `heyasa/willman`, `semcod/planfile`, `oqllm/proxy`,
`subactor/coding-agent`). Profile conformance checks structural alignment only;
it grants zero execution, lease, review, merge, or secret-access authority.

<!-- docs:section evidence -->
## Evidence

Empirical failures between 2026-11-18 and 2026-11-23 showed that partial
`urtlog` logging without full `uritime` temporal discipline fails to unlock
reliable autonomy:

1. **Competing timelines and passive log-only `urtlog` adoption:** Production
   telemetry recorded `4 785` passive `LOG` events against only `1` `PLAN`
   (`kind="intent"`), `0` `causation_id` DAG links, and `0` `access_audit`
   rows. Meanwhile, duplicated scheduling emitted `283` identical trigger storms
   in `heyasa` and `655` redundant `pr-index-refresh` runs in `urilog.sqlite3`
   for three unchanged PRs (`coding-agent` wasted `75.6%` of 24h runs). ADR
   HEY-07 (`heyasa/heyasa#877`) established `uritime` as the sole time owner.
2. **Concurrent companion file corruption and `.tmp` leaks:** Unlocked writes
   to companion JSON/JSONL state corrupted lines in `daemon_ticks.jsonl` and
   `trigger_events.jsonl` and leaked `18+` zero-byte `plans.json.*.tmp` files
   on `OSError`. Fixed via cross-process `fcntl.flock` + `os.fsync` + atomic
   `os.replace` in `heyasa/heyasa#1028` and `#1029`.
3. **Small decision-model (`roles.decision`) alias crashes and blind context:**
   Passing logical scope names (`mesh/d1`) instead of local runtime tags
   (`d1:3b`) caused `19/20` `ValueError` crashes in `decide_resource_operation`;
   normalizing at the decision boundary (`normalized_d1_decision_scope()` in
   `heyasa/heyasa#1029`) restored live inference (`d1:3b` via Ollama/SubLLM),
   complementing the A/B/C benchmark where `<= 600` B URTLog slices lifted
   accuracy from `28.6%` to `85.7%–100.0%` at `337 ms` median latency.
4. **Transient failure cascades and raw `loadavg` false blocks:** Linux kernel
   `inode_switch_wbs` wait queues inflated `os.getloadavg()` to `~12 971` while
   CPU full PSI was `0.00`, causing `503 WILLMAN-RESOURCE-BLOCKED` rejections;
   simultaneously, transient `503 ticket_index_stale` responses tripped circuit
   breakers into `paused` on all `5/5` housekeeping plans. Bounded `3`-attempt
   transient retries (`subactor/registry#62`, `subactor/validator-agent#863`)
   stabilized external metadata reads.

<!-- docs:section content -->
## Content

### 1. Six-layer ownership architecture

Every adopting project MUST preserve these strict responsibility boundaries:

| Layer | Owner | Owns | Forbidden to own |
| --- | --- | --- | --- |
| **Time & Materialization** | `uritime` / `uritime-urt` | Horizons `H0_REFLEX`..`H3_ETERNAL`, cron/RRULE, `ScheduledTicket`, `Materializer` cursor & fence, `DeliveryLedger` | Direct business mutation, model execution, PR merge authority |
| **Temporal Telemetry & Memory** | `uritime-urtlog` | `URT x URI x URN_IN x URN_OUT` dual-mode `PLAN`/`LOG`, DAG lineage, `UnifiedRegistry`, `UrnVault`, `access_audit`, `<= 600` B briefs | Bypassing ACLs, inventing capabilities, claiming lease/merge rights |
| **Pure Classification** | `wellmanifest/polycell` | Deterministic pure functions (`observe` / `wait` / `blocked` / `ready`) over typed inputs | Network/disk I/O, timers, shadow clocks, direct scheduling |
| **Capability Synthesis** | `uritime/autonom` | Synthesizing candidate operations strictly on D1 `NO_MATCH` via isolated `synth` | Running a competing scheduler inside Heyasa or executing unpromoted code |
| **Qualification & Publication** | `Forge` + `OneDev` + `Validator App` | Isolated container checks, contract parity, independent exact-head approval & merge | Coding agent self-approval or personal `gh pr review`/`merge` |
| **Execution Controllers** | `Willman` / `Subactor` | Worktree/host admission, leases, fencing tokens, idempotent dispatch | Overriding `uritime` schedules or self-extending autonomy grants |

### 2. Phase 0 — Opt-in fail-open packaging

- Declare `uritime`, `uritime-urt`, and `uritime-urtlog` in optional extras
  (`[project.optional-dependencies]`), NEVER in mandatory `dependencies`.
- Load `uritime`, `uritime_urt`, and `urtlog` lazily via
  `importlib.import_module(...)` only when configured (e.g., `URTLOG_STATE_DIR`
  is non-empty for telemetry).
- Missing optional packages, unset env vars, or unreadable state directories MUST
  fail open with a structured disabled receipt and MUST NEVER crash core flows or
  mutate tracked Git files.

### 3. Phase 1 — Single temporal owner & idempotent materialization

- All cyclic, one-shot, deferred, and backoff schedules MUST be represented as
  `uritime` `ScheduledTicket` / `uritime-urt` descriptors (`forbidCompetingScheduler: true`).
- Pass explicit timezone-aware UTC `now` timestamps into `Materializer.tick()`
  and `DeliveryLedger.materialize()` instead of implicit `datetime.now()`.
- Freeze `Materializer` configurations with canonical JSON digests, pin the
  target store by immutable `(UUID, generation)` (`targetIdentityMode: "uuid-and-generation"`),
  and reject silent cursor resets or mutated bindings.
- Deduplicate triggers and dispatch requests with deterministic `occurrence_id`
  keys `(repository, queue, incident_type, window)` and validate observation
  revisions/TTL (`superseded` short-circuits stale replays).

### 4. Phase 2 — Dual-mode telemetry (`PLAN` before effect → `LOG` outcome)

- Passive log-only adoption is FORBIDDEN (`forbidLogOnlyAdoption: true`).
- Before dispatching an effect-capable operation, emit a `PLAN` record
  (`kind="intent"`, `status="planned"`, NEVER `status="succeeded"`, NEVER
  granting authority) describing target `URI`, `URN_IN`, expected `URN_OUT`,
  and budget.
- Emit causal `LOG` events (`kind="event"`) linking `causation_id`, `run_id`,
  `depends_on`, `input_urns`, and `output_urns` so `logic_tree()` reconstructs
  root causes end to end.
- Map blocked domain states (`blocked`, `waiting_input`) to `status="unknown"`,
  `log_type="audit"`, `metadata["status"]="blocked"` and update the `UnifiedRegistry`
  URN entry.
- Enforce fail-closed `SecurityPolicy` (`DENY > ALLOW`) and record non-recursive
  `access_audit` telemetry on all URN/vault reads.

### 5. Phase 3 — Storage durability & cross-process concurrency

- Any companion JSON or JSONL ledger alongside SQLite MUST synchronize writes
  with cross-process file locking (`fcntl.flock` or OS equivalent) plus
  `os.fsync`, same-directory temp files, atomic `os.replace`, and guaranteed temp
  cleanup on `OSError`.
- Configure SQLite stores (`urilog.sqlite3`, cursor/ledger stores) in `WAL` mode
  with bounded busy retry loops (`2..8` attempts, recommended `4`).

### 6. Phase 4 — Decision LLM (`roles.decision`) runtime contract

- Inject live `fetch_urtlog_brief()` context into `roles.decision` calls within
  `<= 600` UTF-8 bytes (hard ceiling `1 024` B); isolate entity queries to a
  single URN + direct DAG neighbors and forbid unfiltered store dumps.
- Normalize logical routing scopes (such as `mesh/d1`) to qualified local model
  tags (`d1:3b`) at the decision boundary (`requireModelAliasNormalization: true`).
- Apply exponential backoff to both `GatewayError` and repeated `model_abstained`
  outcomes, and trigger `uritime/autonom` synthesis ONLY on `NO_MATCH` (never on
  `CLARIFY` or `PLAN_REQUIRED`, and never execute unpromoted candidates).
- Every decision output MUST carry `advisory_only: true` and
  `execution_allowed: false`; controller auto-execution without separate human or
  Validator gate MUST stay restricted to qualified read-only effects
  (`pure`, `read`, `query`, `fs:read`, `docker:read`).

### 7. Phase 5 — Operational resilience & host admission

- Circuit breakers MUST distinguish transient dependency outages (`503`, gateway
  timeouts, rate limits) from permanent contract or schema errors so healthy
  cyclic plans do not lock into permanent `paused` states.
- Host admission probes MUST inspect kernel PSI and runnable thread contention
  (`psi-and-runnable-contention`) rather than raw `os.getloadavg()` alone.
- External metadata read clients (GitHub API, inventory sync, publication
  watchdogs) MUST apply bounded transient retries (`2..5` attempts, recommended
  `3`) with exponential backoff before failing closed.

### 8. Phase 6 — Required verification & conformance gate

Every adopter MUST supply:

1. **Offline fail-open tests** proving clean no-op when `uritime`/`urtlog` or
   `URTLOG_STATE_DIR` is absent.
2. **Live integration tests** against real `UrtLogStore` / `UnifiedRegistry` /
   `Materializer` guarded in-body via `importlib.util.find_spec(...)` (NEVER
   `@pytest.mark.skip*`) with neutral, secret-free fixtures.
3. **Concurrent write tests** (multi-process/multi-thread) verifying zero torn
   JSONL lines and zero leaked `.tmp` files.
4. **Profile validation**:
   ```bash
   python3 standard/logs_check.py uritime-integration --root .
   python3 standard/logs_check.py urtlog-bridge --root .
   python3 standard/logs_check.py validate --root .
   python3 standard/logs_check.py self-test
   ```

<!-- docs:section limitations -->
## Limitations

1. Static validation of `contracts/uritime-integration.profile.v1.json` checks
   normative declarations and bounds; live concurrency, model alias translation,
   and circuit-breaker separation still depend on each adopter's test suite and
   runtime telemetry.
2. Kernel PSI probes (`/proc/pressure/*`) are Linux-specific; non-Linux hosts
   MUST substitute equivalent runnable-CPU contention metrics while keeping raw
   `loadavg` non-authoritative on its own.
3. Profile conformance proves architectural alignment only and NEVER grants
   execution, lease, review, merge, or credential authority.

<!-- docs:section next_actions -->
## Next actions

1. Adopters integrating `uritime`, `uritime-urt`, or `uritime-urtlog` pin both
   `contracts/urtlog-bridge.profile.v1.json` and
   `contracts/uritime-integration.profile.v1.json` and run `logs_check.py` in CI.
2. Migrate existing passive `LOG`-only bridges (including `heyasa` and `coding-agent`)
   to emit pre-effect `PLAN` intents with `causation_id`, `occurrence_id`
   deduplication, and `access_audit` tracking.
3. Re-evaluate thresholds (`sqliteBusyRetryMaxAttempts`, `maxSliceBytes`,
   `externalReadRetryMaxAttempts`) by `2026-12-23` after 30 days of production
   canary runs.
