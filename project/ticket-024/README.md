# Ticket 024: Modularize and harden logs conformance checker

- **ID**: ticket-024
- **Owner**: agent:antigravity
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-12
- **Authorization**: SESSION_EXECUTION_AUTHORIZATION

## Goal and scope

Split the 2,271-line `standard/logs_check.py` monolith into cohesive `< 500`-line
modules under `standard/` while preserving every CLI command, flag, diagnostic
rule, and public symbol, and harden JSON, path/symlink/FIFO, diagnostic endpoint,
and self-causation validation against crash and traversal edge cases.

## Acceptance criteria

- [x] AC-01: Every Python file under `standard/` is strictly `< 500` lines after `ruff format` and passes `ruff check --no-cache` with 0 findings.
- [x] AC-02: Descriptor-safe bounded file reads (`O_NOFOLLOW | O_NONBLOCK` + regular-file & inode check), lexical symlink-ancestor rejection, strict JSON decoding (duplicate keys, float overflow, lone UTF-16 surrogates, nesting depth), diagnostic endpoint port/IPv6 validation, and control-character/self-causation checks fail closed without unhandled exceptions.
- [x] AC-03: `python3 standard/logs_check.py validate --root .`, `python3 standard/logs_check.py self-test`, `python3 -m unittest discover -s standard -p 'test_*.py'`, `./project/governance-check.sh --base origin/main`, and `wellman check` pass.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
