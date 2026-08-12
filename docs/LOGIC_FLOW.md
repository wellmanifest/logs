# Logs control-plane logic flow

## Event creation

```mermaid
sequenceDiagram
    actor Author as Human / LLM
    participant DSL as Request validator
    participant Planner as POA planner
    participant Control as Policy / grant / intent
    participant Command as CQRS command handler
    participant Store as logs/ JSONL stream
    participant Check as Deterministic validator
    participant Query as Projection query

    Author->>DSL: inspect or plan_append request
    DSL-->>Planner: typed, closed AST
    Planner-->>Author: exact plan + digest (no effect)
    Author->>Control: request bounded authority
    Control-->>Command: plan-bound execution envelope
    Command->>Store: append one immutable event at expected version
    Store->>Check: replay canonical lines and hash chain
    Check-->>Query: verified stream projection or stable finding
```

The authored request stops at planning. A controller outside the LLM boundary
must bind subject, target, exact plan, grant, intent and expected stream version
before an append command can exist.

## Repository validation

```text
load contract bundle + Protobuf source
              |
              v
check closed schemas, request grammar and catalog
              |
              +--> validate errors/{CODE}.md identity and embedded DSL
              |
              +--> replay each logs/*.jsonl stream
                        |
                        +--> canonical bytes
                        +--> exact fields and safe flags
                        +--> sequence + previousHash + eventHash
                        +--> evidence confinement and digest
                        +--> event code resolves to error catalog
              |
              v
stable LOGS-VALIDATION-001 findings or PASS
```

Validation is read-only and deterministic. One malformed line does not cause
the checker to trust later chain state. The report names a safe path and rule,
but does not echo rejected payload values.

## Protobuf and projections

Protobuf owns message names, field numbers, enums and service separation.
`contracts/logs.contract.json` bundles the closed JSON projection schemas,
request grammar, process URIs and diagnostic catalog. JSONL and embedded error
DSL are projections of those types, not competing semantic definitions.

Buf lint verifies Protobuf syntax and style. The Python conformance runtime
also checks that required messages, service methods, enum vocabulary and the
contract bundle remain mutually complete.

## Failure handling

All deterministic failures use `LOGS-VALIDATION-001` plus a bounded rule and
help path `errors/LOGS-VALIDATION-001.md`. Examples include contract drift,
non-canonical JSON, broken chains, unsafe flags, missing evidence, malformed
error pages and an authority-bearing model request.

The safe recovery order is:

1. stop append activity for the affected stream;
2. classify whether bytes are uncommitted, committed or externally published;
3. correct the producer or add a compensating event rather than rewriting
   published history;
4. repair the error definition when the catalog is incomplete;
5. rerun host, Docker, Buf and governance checks.

Never disable hash checks, delete unknown history, redact by overwriting a
published event or treat an LLM explanation as proof that a chain is valid.

