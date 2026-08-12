# wellmanifest/logs

`wellmanifest/logs` is a governed contract and conformance tool for creating
auditable log events and actionable error documentation.

The planned v0.1 design combines:

- Process-Oriented Architecture (POA) for exact URI Processes and bounded
  validation;
- CQRS for a strict separation between append commands and read-only queries;
- Event Sourcing for ordered, hash-chained JSONL streams in `logs/`;
- Protobuf as the canonical cross-language type contract;
- a closed JSON DSL projection for repository review and LLM-safe planning;
- one structured `errors/{CODE}.md` runbook for every emitted error code.

## Status

Bootstrap and bounded planning. Implementation is owned by
[`project/ticket-001`](project/ticket-001/README.md) after managed allocation.

## Intended validation

```bash
python3 standard/logs_check.py validate --root .
python3 standard/logs_check.py self-test
docker compose run --rm conformance
docker compose run --rm proto
```

The DSL and a valid repository are evidence only. They never create execution
authority, waive a finding or authorize destructive cleanup.
