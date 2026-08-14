# TODO

## Active work

- [x] [`ticket-001`](project/ticket-001/README.md) — define the canonical
  Protobuf model, closed JSON/GBNF projections, hash-chained `logs/*.jsonl`,
  structured `errors/{CODE}.md`, deterministic conformance and POA/CQRS/Event
  Sourcing documentation. State: `DONE / DONE`; classification:
  `FEATURE / P1 / requested`; workstream: `integration`.
  `ifuri-validator-agent` approved and merged
  `855f26215e79787b43f40c94176802f353962582`.

- [ ] [`ticket-004`](project/ticket-004/README.md) — revise the v0.1 event
  contract to v0.2 against the 315-event `maskservice/c2004` deployment: an open
  namespaced `eventType`, `source` split from `producer`, `subjectState` split
  from `outcome`, a `PLAN`/`APPLY` mode, `inputHash` as self-evidence, and
  `null` instead of `"-"` placeholders. State: `IN_PROGRESS / EDIT`;
  classification: `FEATURE / P1 / requested`; workstream: `integration`.

## Planned work

- [ ] Publish the v0.2 documentation: `docs/ARCHITECTURE.md`,
  `docs/LOGIC_FLOW.md` and `VERSION`. Written under `ticket-004` but reverted
  out of its diff after `GOV-BUDGET-001` capped the ticket at five
  implementation files. Depends on `ticket-004` merging, because `integration`
  allows one active ticket at a time.
- [ ] Record the v0.2.0 entry in `CHANGELOG.md` and refresh the `README.md`
  status line. Both are owned by the `governance` workstream, so they cannot
  ride on an `integration` ticket.
- [ ] Close the projection drift found in c2004: `SODL/1` and `PLOG/1` name the
  same field differently (`oql`/`type`, `data.payload`/`logic`) and `PLOG/1`
  drops `input_hash`. A declared projection field map would make the drift
  checkable.
