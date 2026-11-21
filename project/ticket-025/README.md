# Ticket 025: Extend wellmanifest/logs with opt-in urtlog bridge and decision-slicing profile

- **ID**: ticket-025
- **Owner**: agent:antigravity (`SESSION_EXECUTION_AUTHORIZATION`)
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-21

## Goal and scope

Extend the existing `wellmanifest/logs` standard (without modifying immutable
v0.2–v0.5 contracts or `proto/v0.5`) with a closed machine-readable profile,
deterministic conformance checker, adversarial unit tests and normative
information document specifying how adopters implement opt-in `uritime/urtlog`
telemetry bridges, `URT x URI x URN_IN x URN_OUT` DAG lineage, `UnifiedRegistry`
URI/URL/URN projections, `blocked -> unknown/audit` status mapping and compact
prefix/single-URN decision context slicing (`<= 600` B for small decision LLMs).

## Acceptance criteria

- [ ] AC-01: Closed schema `contracts/urtlog-bridge.schema.v1.json` and canonical
      profile `contracts/urtlog-bridge.profile.v1.json` validate cleanly with
      `python3 standard/logs_check.py urtlog-bridge --root .`.
- [ ] AC-02: Existing `logs_check.py validate --root .`, `self-test`, and all
      unit tests under `standard/` (including adversarial tests for the new
      profile validator) pass with zero regressions and zero changes to immutable
      v0.2–v0.5 contracts.
- [ ] AC-03: `docs/information/urtlog-bridge-and-decision-slicing.md` passes
      `wellmanifest/docs` checks, is indexed in `docs/README.md`, and
      `./project/governance-check.sh --base origin/main` passes.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
