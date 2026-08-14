# Ticket 004: Revise the logs contract from the c2004 deployment evidence

- **ID**: ticket-004
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-08-14

## Goal and scope

v0.1 of `wellmanifest.logs` was designed against a single bootstrap event and
had never met a real producer. `maskservice/c2004` ran an independent event log
(`subactor.operational-event.v1`, projected as `SODL/1` and `PLOG/1`) for three
weeks and produced 315 events. This ticket revises the contract to v0.2 against
that measurement.

Every change below is traced to a counted observation, not to a preference.

| Evidence in c2004 | Count | Change |
| --- | --- | --- |
| `oql` was `ticket.create` / `ticket.update` / `ticket.status_change` | 3 distinct / 315 | `eventType` becomes an open union: the reserved core enum plus a namespaced pattern. The `logs.` namespace is reserved. |
| `actor` varied independently of `source` | 4 x 2 | `source` added beside `producer`; who acted and what emitted are separate facts. |
| `status` carried six lifecycle values | 6 distinct | `subjectState` added so `outcome` keeps its five bounded values. |
| `input_hash` on every event, file evidence on none | 315 / 0 | `evidence` minItems relaxed 1 to 0; `inputHash` added as the binding. |
| `receipt_ref` was `"-"` | 315 / 315 | `receiptRef` is null when absent; the sentinel is rejected. |
| `causation_id` was `"-"` | 315 / 315 | Same rule; sentinels belong to the line projection, not canonical JSON. |
| `mode` was always `apply` | 315 / 315 | `mode` is a required `PLAN`/`APPLY` enum. |
| `replayable` / `kind` never varied | 315 / 315 | Considered and deliberately not adopted. |
| `previous_hash` / `sequence` absent | 0 / 315 | Chain requirement stands. `logs/control.jsonl` now holds two chained events so it is exercised, not assumed. |
| Rotation left three 0-byte segments | 3 of 6 | No change: `LOGS-STORE-EMPTY` already rejects this. |

## Out of scope

Capped by the delivery budget at five implementation files:

- `docs/ARCHITECTURE.md`, `docs/LOGIC_FLOW.md` and `VERSION` move to a dependent
  ticket. The gate rejected the combined diff with `GOV-BUDGET-001` and directed
  a split rather than an enlarged PR.
- Projection drift stays open: `SODL/1` and `PLOG/1` name the same field
  differently (`oql`/`type`, `data.payload`/`logic`) and `PLOG/1` drops
  `input_hash`. A declared projection field map is the next revision.
- No migration tooling for streams written without a hash chain.

## Acceptance criteria

- [ ] AC-01: Scope is approved by a human owner.
- [x] AC-1: `python3 standard/logs_check.py validate --root .` reports
      `LOGS-PASS` over the two-event chained control stream.
- [x] AC-2: `python3 standard/logs_check.py self-test` passes 17 adversarial
      checks, including a positive case for a namespaced deployment type and a
      rejection of the `"-"` receipt placeholder.
- [x] AC-3: `./project/governance-check.sh` reports `GOV-PASS`.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-claude.md](ai-claude.md)
