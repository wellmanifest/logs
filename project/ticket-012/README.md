# Ticket 012: Adopt recoverable ticket activity policy

- **ID**: ticket-012
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-08-30

## Goal and scope

Adopt immutable `wellmanifest/new-project` 0.19.11 as a separate governance
transaction. A managed activity policy and clone-external receipt registry
replace stale status prose as the only reservation authority after a protected
terminal outcome.

The resolver verifies repository identity, ticket, target branch, full Git
ancestry and later branch advancement. Missing, malformed, unsupported or
stale evidence fails closed and points to the managed ERROR runbook. Historical
ticket Markdown and unmerged work remain unchanged.

## Acceptance criteria

- [x] AC-01: The user authorized implementation and publication in this session.
- [ ] AC-02: The lock pins published `new-project` 0.19.11 exactly.
- [ ] AC-03: Verified merge receipts release tickets 007 and 009 without
      rewriting historical Markdown.
- [ ] AC-04: Invalid evidence remains active and every failure has a safe exit.
- [ ] AC-05: Governance and immutable-adoption checks pass.

## Tracking boundary

This directory records bounded intent; the managed runtime, policy, schemas and
runbook are the material delivery.
