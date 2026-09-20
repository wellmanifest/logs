# Ticket 019: Resolve stale ticket activity projections

- **ID**: ticket-019
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-20

## Goal and scope

Seven merged tickets (007, 009, 011, 012, 013, 014, 018) keep stale
`IN_PROGRESS` status projections, so the managed governance gate reports
overlapping active scopes and carrier-only findings on `main`. Add the
target-owned `.governance/ticket-activity.override.json` with
`missingPolicy: git-ancestry` so tickets whose delivery is already on the
target branch resolve inactive by Git ancestry instead of a missing
clone-local terminal receipt.

## Acceptance criteria

- [x] `.governance/ticket-activity.override.json` validates against the
  managed override schema.
- [x] `ticket_activity.py resolve` reports every listed ticket as inactive
  (`verified-terminal` / `delivery-on-target`).
- [x] `project/governance-check.sh` passes with zero findings.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
