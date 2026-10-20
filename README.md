# wellmanifest/logs

Wellmanifest Logs defines auditable events, hash-chained JSONL streams and
actionable error documentation. The implemented standard is **0.5.0**, as
declared in [VERSION](VERSION). Consumer adoption is a separate operation.

## Contracts and ownership

The pack provides Protobuf contracts, closed JSON projections and deterministic
conformance checks. Commands append events; queries inspect and validate them.
Runtime collectors and storage services belong to adopting projects.

| Contract generation | Implemented concern |
| --- | --- |
| v0.2 | Producer and source identities, lifecycle and outcome, PLAN/APPLY and input hashes. |
| v0.3 | Adopter-owned error catalogs and runbooks with immutable digest bindings. |
| v0.4 | Optional operational diagnostic context. |
| v0.5 | Session, tool, checkpoint, resume, split and Git continuity events. |

Versioned contracts coexist under [contracts/](contracts/) and [proto/](proto/).
Use the contract pinned by the adopter; preserve historical event bytes and
hashes when introducing a later generation.

## Validation

```bash
python3 standard/logs_check.py validate --root .
python3 standard/logs_check.py self-test
docker compose run --rm conformance
docker compose run --rm proto
```

Consumer projections can also be checked with the `adoption` and
`error-adoption` commands; use `--help` for their explicit inputs.

## Documentation

- [Documentation index](docs/README.md)
- [Architecture and event contracts](docs/ARCHITECTURE.md)
- [Logic flow and work-result evidence](docs/LOGIC_FLOW.md)
- [Hourly diagnostic storage and adoption boundaries](docs/information/hourly-diagnostic-storage.md)

Wellmanifest Docs owns canonical documentation placement. Wellmanifest Report
owns bounded evidence and publication-state declarations. Log validity and
report conformance grant no execution, review, merge or cleanup authority.
