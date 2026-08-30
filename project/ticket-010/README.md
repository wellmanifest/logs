# Ticket 010: Pin governance workflow to new-project 0.19.9

- **ID**: ticket-010
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-08-30

## Goal and scope

Update the target-owned GitHub Actions wrapper to the published immutable SHA
for `wellmanifest/new-project` 0.19.9. This file belongs to the manifest's
`infrastructure` workstream; it is not part of the managed adoption payload.

## Acceptance criteria

- [x] AC-01: `uses` and `standard-ref` point to the same full publication SHA
      `e750af09ef3d3731e4f57c59d21d7d262057cb88`.
- [ ] AC-02: governance and hosted required checks pass.

## Risk

The SHA is intentionally a fixed supply-chain trust pin. Lifecycle,
workstream and package-content registries are dynamic; the trust boundary is
not.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
