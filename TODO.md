# TODO

## Active work

- [x] [`ticket-001`](project/ticket-001/README.md) — define the canonical
  Protobuf model, closed JSON/GBNF projections, hash-chained `logs/*.jsonl`,
  structured `errors/{CODE}.md`, deterministic conformance and POA/CQRS/Event
  Sourcing documentation. State: `DONE / DONE`; classification:
  `FEATURE / P1 / requested`; workstream: `integration`.
  `ifuri-validator-agent` approved and merged
  `855f26215e79787b43f40c94176802f353962582`.

- [x] [`ticket-004`](project/ticket-004/README.md) — revise the v0.1 event
  contract to v0.2 against the 315-event `maskservice/c2004` deployment: an open
  namespaced `eventType`, `source` split from `producer`, `subjectState` split
  from `outcome`, a `PLAN`/`APPLY` mode, `inputHash` as self-evidence, and
  `null` instead of `"-"` placeholders. State: `DONE / DONE`;
  classification: `FEATURE / P1 / requested`; workstream: `integration`.
  `ifuri-validator-agent` approved exact successor head
  `a52a7f3f12b379847d8fbf4d598649b601f5c708` and merged it as
  `4440e9e9a40423715747a57b86e3d9405be5aa4e`; predecessor PR #7 was closed
  without merge and its branch remains preserved.

## Planned work

- [ ] [`ticket-005`](project/ticket-005/README.md) — publish the v0.2
  documentation and the `VERSION` bump that `GOV-BUDGET-001` cut from
  `ticket-004`. State: `BLOCKED / BLOCKED`; classification:
  `SERVICE / P2 / health`; workstream: `integration`.
  Protected run `31848594548` proved that implementation preceded the ticket
  intent (`GOV-INTENT-003`); delivery moves to a plan-first successor.
- [ ] Record the v0.2.0 entry in `CHANGELOG.md` and refresh the `README.md`
  status line. Both are owned by the `governance` workstream, so they cannot
  ride on an `integration` ticket.
- [ ] Close the projection drift found in c2004: `SODL/1` and `PLOG/1` name the
  same field differently (`oql`/`type`, `data.payload`/`logic`) and `PLOG/1`
  drops `input_hash`. A declared projection field map would make the drift
  checkable.
