# Ticket 014: Add typed continuity and streaming JSONL events

- **ID**: ticket-014
- **Owner**: agent:codex
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-01

## Goal and scope

Publish v0.5 with thirteen typed continuity/streaming events for sessions,
NL→DSL compilation, tools, snapshots, resume observation/decision, work splits
and distinct Git checkpoint/commit/push-start/push-completion boundaries.
Durable payloads contain only bounded digests and receipt references; raw
prompts, diffs, secrets, tool output and host paths remain unrepresentable.

## Acceptance criteria

- [x] AC-01: Bounded intent records the compatible v0.5 extension.
- [x] AC-02: Each of the thirteen continuity events has a closed matched payload.
- [x] AC-03: Causal boundaries and digest continuity validate deterministically.
- [x] AC-04: Raw prompts, diffs, secrets, tool output and host paths fail closed.
- [x] AC-05: Python, Docker, Protobuf and governance checks pass.

## Tracking boundary

This directory contains bounded intent and validation receipts only. The
material outcome is the contract, Protobuf, checker, fixtures and documentation.
