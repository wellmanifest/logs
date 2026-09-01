# Ticket 013: Add typed operational diagnostics to logs

- **ID**: ticket-013
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-01

## Goal and scope

Extend the canonical event with an optional, closed operational diagnostic
context. It must make retries and connectivity failures queryable while keeping
raw responses, query strings, credentials and arbitrary payloads outside logs.

## Acceptance criteria

- [x] AC-01: Bounded intent records the compatible contract extension.
- [ ] AC-02: Valid context passes and unsafe endpoint data fails closed.
- [ ] AC-03: Repository conformance remains green.
- [ ] AC-04: Container conformance remains green.
- [ ] AC-05: Governance and diff checks pass.

## Tracking boundary

This directory contains bounded intent and validation receipts only. The
material outcome is the contract, Protobuf, conformance and architecture change.
