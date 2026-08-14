# Ticket Changelog (ticket-004)

## [0.1.0] - 2026-08-14

- Initial governance scaffold created.
- No human participant identity or content was generated.
- Contract bundle raised to `0.2.0` against the 315-event `maskservice/c2004`
  deployment.
- `eventType` opened to a union of the reserved core enum and a namespaced
  deployment pattern; the `logs.` namespace stays reserved.
- `source`, `mode`, `subjectState`, `inputHash` and `receiptRef` added to
  `LogEvent` at Protobuf field numbers 19-23; existing numbers untouched.
- `evidence` relaxed to `minItems: 0`; `inputHash` now carries the binding for
  events with no file artefact.
- Absent optional values must be `null`; the `"-"` sentinel is rejected.
- `errors/LOGS-VALIDATION-001.md` DSL raised to version 2.
- `logs/control.jsonl` re-projected and extended to two chained events, the
  first exercise of the hash chain in this repository.
- Conformance self-test grown from 11 to 17 adversarial checks, plus a positive
  case for a namespaced deployment event type.
- `docs/` and `VERSION` deferred to a dependent ticket after `GOV-BUDGET-001`.

## [0.1.1] - 2026-08-14

- Reissued ticket-004 as a successor with a plan-only first commit after the
  protected gate rejected predecessor PR #7 for missing prior intent history.
