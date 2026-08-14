# Ticket 005: Publish the v0.2 documentation and version bump

- **ID**: ticket-005
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-08-15

## Goal and scope

`ticket-004` raised the contract bundle to `0.2.0`, but its five-file delivery
budget forced `docs/` and `VERSION` out of the diff. `GOV-BUDGET-001` directed a
split rather than a larger PR, so `main` ended up shipping a v0.2 contract while
its documentation still described the v0.1 design and `VERSION` still read
`0.1.0`.

This ticket closes that gap. It is the dependent ticket `ticket-004` named.

Scope is documentation only:

- `docs/ARCHITECTURE.md` — the c2004 deployment evidence table (what 315 events
  changed and why), the revised Event Sourcing field list, and three new
  invariants covering namespacing, null-versus-sentinel and `inputHash`.
- `docs/LOGIC_FLOW.md` — the deployment adoption field mapping, worked through
  c2004's own field names, and the new validation steps.
- `VERSION` — `0.1.0` to `0.2.0`, matching the contract bundle.

No contract, Protobuf, checker or stream change: all of that landed with
`ticket-004`. The evidence was gathered then and is only being published now,
so this introduces no new analysis.

## Out of scope

Projection drift stays open: `SODL/1` and `PLOG/1` name the same field
differently (`oql`/`type`, `data.payload`/`logic`) and `PLOG/1` drops
`input_hash`. A declared projection field map is the next revision.

## Acceptance criteria

- [ ] AC-01: Scope is approved by a human owner.
- [x] AC-1: `python3 standard/logs_check.py validate --root .` still reports
      `LOGS-PASS`; a documentation-only diff must not affect it.
- [x] AC-2: `python3 standard/logs_check.py self-test` still passes 17
      adversarial checks.
- [x] AC-3: `VERSION` and the contract bundle version agree.
- [x] AC-4: `./project/governance-check.sh` reports `GOV-PASS`.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-claude.md](ai-claude.md)
