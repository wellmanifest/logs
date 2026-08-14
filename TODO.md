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

- [x] [`ticket-006`](project/ticket-006/README.md) — publish the v0.2
  documentation and `VERSION` through a plan-first successor. State:
  `DONE / DONE`; classification: `SERVICE / P2 / health`; workstream:
  `integration`. Validator App approved exact head
  `f8ec0d898b722652ae903d33005bfb1aefedca24` and merged PR #11 as
  `3e1bf6e43800a6191700e1a06f5d52a3f31d44bd`; the successor branch was deleted
  and PR #10 received a digest-bound lossless disposition before cleanup.

## Planned work

- [ ] Record the v0.2.0 entry in `CHANGELOG.md` and refresh the `README.md`
  status line. Both are owned by the `governance` workstream, so they cannot
  ride on an `integration` ticket.
- [ ] Close the projection drift found in c2004: `SODL/1` and `PLOG/1` name the
  same field differently (`oql`/`type`, `data.payload`/`logic`) and `PLOG/1`
  drops `input_hash`. A declared projection field map would make the drift
  checkable.
