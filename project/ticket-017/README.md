# Ticket 017: Name a retained value's phase in the invariants

- **ID**: ticket-017
- **Owner**: bot:wellmanifest
- **Status**: DONE
- **Workflow state**: DONE
- **Created**: 2026-09-10

## Goal and scope

Invariant 9 separates an absent value from a present one. It says nothing about
a value that is present but no longer current, so a field that survives an
attempt, cycle or phase boundary is read as describing the present.

Observed 2026-09-10 in an adopting runtime: a ticket kept the previous
attempt's provider payment error while its own timestamp advanced to the new
attempt. The board reported that failure for hours after the account had been
funded, and only an independent spend counter disproved it.

Invariant 18 states the rule. No schema, event type or check changes.

## Acceptance criteria

- [x] AC-01: The invariants name the retained-value case separately from
  absence, and the standard's own validator passes.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
