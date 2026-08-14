---
participant-id: agent:claude
participant: claude
role: agent
ticket: ticket-004
---
# Participant: claude (AI agent)

## Understanding

The user asked to update this standard from the experience and implementation
in `maskservice/c2004`. c2004 does not consume `wellmanifest.logs`; it runs its
own event log under `.planfile/events/`. That makes it an independent
measurement rather than a conformance report, which is the more useful kind of
evidence: it shows what a real producer needed when nothing forced it to follow
this contract.

I read all 315 events and counted the distribution of every dimension before
proposing any change. The counts are in `ai-claude-logs.txt` [2] and drive the
table in `README.md`. Two of them decided most of the design:

- Not one of c2004's three event types could be expressed in the v0.1 closed
  seven-value enum. A closed core vocabulary only works if a deployment has
  somewhere else to put its own names.
- Five dimensions (`replayable`, `kind`, `mode`, `receipt_ref`, `causation_id`)
  were constant across all 315 events. A field that never varies is not audit
  evidence. Two of them were constant because they were placeholders (`"-"`),
  which is worse than absence: validation cannot distinguish an unexecuted
  event from an executed one.

## Execution plan

1. Count every dimension in the c2004 stream before designing. Done.
2. Allocate the ticket only through `./project/new-ticket.sh` (rule 17). Done.
3. Change Protobuf first, then the closed JSON projection, then the checker --
   the order required by `Safe extension rules` in
   `errors/LOGS-VALIDATION-001.md`. Done.
4. Add an adversarial check for every new field, plus a positive case for the
   namespaced type, before bumping the contract version (same runbook, rule 5).
   Done.
5. Re-project `logs/control.jsonl` and extend it to two chained events. Done.
6. Run the conformance validator, the self-test and the governance gate. Done.

## Actual changes

- Initialized the bounded ticket and recorded SESSION_EXECUTION_AUTHORIZATION
  from the request to execute this work.
- `contracts/logs.contract.json` to v0.2.0: open `eventType` union, `source`,
  `mode`, `subjectState`, `inputHash`, `receiptRef`, `evidence` minItems 0.
- `proto/wellmanifest/logs/v1/logs.proto`: `Mode` enum, five new `LogEvent`
  fields at numbers 19-23. Existing field numbers untouched. `event_type`
  becomes a string union; the `EventType` enum stays the reserved registry.
- `standard/logs_check.py`: rules `LOGS-EVENT-MODE`, `-SOURCE`, `-STATE`,
  `-INPUT`, `-RECEIPT`; `eventType` accepts a namespaced type but rejects a
  `logs.` squat; six new adversarial cases and one positive case (11 to 17).
- `errors/LOGS-VALIDATION-001.md` to DSL version 2: causes for namespace
  squatting and placeholder values, and the constant-dimension prohibition.
- `logs/control.jsonl`: re-projected and extended to two chained events, which
  is the first time the chain rule is actually exercised in this repository.

## Blockers

- The gate rejected the combined diff with `GOV-BUDGET-001` (8 files against a
  `maxImplementationFiles: 5` budget) and directed a split. `docs/ARCHITECTURE.md`,
  `docs/LOGIC_FLOW.md` and `VERSION` are therefore written but held back for a
  dependent ticket. They are ready, not unwritten. Because `integration` allows
  one active ticket at a time, that follow-up can only start after this PR
  merges.
- `CHANGELOG.md` and `README.md` are owned by the `governance` workstream, not
  `integration`, so the release note for v0.2.0 needs its own ticket as well.
- New authority remains required for destructive action, secret access, new
  external coordination, material objective expansion and trusted merge.
