# Ticket 007: Reject stale adopted log projections

- **ID**: ticket-007
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-08-28

## Goal and scope

Prevent a consumer from claiming `wellmanifest.logs/event/v1` while validating
against a stale or locally altered event schema. Add a read-only adoption check
that compares a consumer's vendored event schema with the canonical event
schema in `contracts/logs.contract.json` using semantic canonical JSON.

The command reports the canonical contract digest and fails closed on missing,
unreadable or divergent schemas. It does not modify the consumer repository and
does not grant execution authority.

## Acceptance criteria

- [x] AC-01: The user explicitly authorized implementation and direct repair of
      regressions in the owning Wellmanifest standard on 2026-08-28.
- [ ] AC-02: An exact canonical event schema passes the adoption check.
- [ ] AC-03: The pre-v0.2 Doctor schema is rejected as stale.
- [ ] AC-04: Existing repository validation and adversarial self-tests pass.
- [ ] AC-05: Governance and Docker conformance gates pass.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
