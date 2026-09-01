# Logs control-plane logic flow

## Consumer adoption check

A repository that vendors the canonical event schema must prove that its copy
still has the same semantic JSON as the current contract bundle:

```bash
python3 standard/logs_check.py adoption \
  --root /path/to/wellmanifest/logs \
  --event-schema /path/to/consumer/logs-event.schema.v1.json
```

The comparison ignores formatting and object-key order but rejects every
semantic difference, including a missing required field. A consumer that needs
a different shape must publish a separately versioned projection and a
declared mapping; it must not reuse `wellmanifest.logs/event/v1`.

An adopter validates its own stable error codes and runbooks separately:

```bash
python3 standard/logs_check.py error-adoption \
  --root /path/to/wellmanifest/logs \
  --catalog /path/to/consumer/logs-error-catalog.v1.json
```

The catalog is closed and contains `schema`, `namespace`,
`contractSha256`, `errorsDirectory` and a sorted `diagnosticCodes` list. The
namespace may not be `LOGS`; product codes remain HOME in their product
repository. The directory cannot escape the catalog root or be a symlink, and
its exact Markdown page set must match the declared codes. Digest drift,
namespace substitution, missing or extra pages and malformed embedded error
DSL all fail closed before publication.

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
                        +--> event type: reserved core or namespaced deployment
                        +--> mode, source, subjectState, inputHash, receiptRef
                        +--> optional closed operational diagnostic
                        +--> typed continuity payload + causal digest match
                        +--> event code resolves to error catalog
              |
              v
stable LOGS-VALIDATION-001 findings or PASS
```

Validation is read-only and deterministic. One malformed line does not cause
the checker to trust later chain state. The report names a safe path and rule,
but does not echo rejected payload values.

When present, `diagnostic` makes failure progression queryable without a raw
message: phase/status, retryability, coherent attempt counters, bounded
duration, a secret-free endpoint origin/reference, transport or HTTP status,
runbook/error/knowledge references and optional W3C-sized trace identifiers.
Unknown fields, credential-bearing URLs, path/query-bearing URLs and inverted
attempt counters fail as `LOGS-EVENT-DIAGNOSTIC`.

## Crash recovery and Git streaming

```text
agent.session_started
        |
        v
agent.intent_compiled -------> agent.tool_requested
                                      |
                                      v
                              agent.tool_completed
                                      |
                                      v
                            agent.snapshot_recorded
                                      |
                                      v
                             agent.resume_observed
                                      |
                                      v
                              agent.resume_decided
                                      |
                                      v
work.split_requested -------> work.split_materialized
                                      |
                                      v
git.slice_checkpointed -----> git.commit_created
                                      |
                                      v
                               git.push_started
                                      |
                                      v
                              git.push_completed
```

Every arrow is an event-ID causation reference within one correlation. The
checker resolves it only against earlier events in the same stream, verifies
the expected parent type for paired transitions and compares the relevant
digest. NL input becomes durable only as `sourceDigest` plus the compiled
`intentDigest`. A restart first emits `resume_observed` and only then
`resume_decided`; the decision is resume when state digests match and divergence
when they do not. It never infers success from a raw transcript.

`logs/continuity.jsonl` is the canonical thirteen-event fixture. It covers every
declared boundary exactly once, including a divergent resume decision, one
materialized split and distinct slice checkpoint, commit creation, push start
and push completion. Its payloads contain no content or filesystem location.
Local `.subactor/sessions/*/events.jsonl` files may remain large and ignored;
durable publication is restricted to correlation/causation, digests, bounded
envelope metadata and immutable receipt references.

## Protobuf and projections

Protobuf owns message names, field numbers, enums and service separation.
The current versioned contract bundles the closed JSON projection schemas,
request grammar, process URIs and standard diagnostic catalog. Historical
contract paths remain byte-stable so evidence in an existing JSONL event never
changes underneath its digest. JSONL and embedded error DSL are projections of
those types, not competing semantic definitions.

Buf lint verifies Protobuf syntax and style. The Python conformance runtime
also checks that required messages, service methods, enum vocabulary and the
contract bundle remain mutually complete.

## Adopting the contract in a deployment

A deployment does not extend the reserved vocabulary; it uses its own namespace
next to it. The mapping that `maskservice/c2004` would need is the worked
example:

| c2004 field | Contract field | Note |
| --- | --- | --- |
| `oql` = `ticket.status_change` | `eventType` | Already namespaced, so it validates unchanged. |
| `source` = `planfile.history` | `source` | Direct. |
| `actor` = `cursor` | `producer` = `agent:cursor` | The actor kind becomes the producer prefix. |
| `uri` = `planfile://tickets/PLF-2070/command/status_change` | `subjectRef` | The POA Process URI is the subject. |
| `status` = `done` | `subjectState` | Lifecycle state, not `outcome`. |
| — | `outcome` | New fact: did this append succeed, not what the ticket became. |
| `mode` = `apply` | `mode` = `APPLY` | Uppercased; `PLAN` becomes expressible. |
| `input_hash` | `inputHash` | Direct. |
| `data.payload` | *(dropped)* | No arbitrary payload exists; `inputHash` binds it instead. |
| `receipt_ref` = `"-"` | `receiptRef` = `null` | The sentinel is rejected. |
| `causation_id` = `"-"` | `causationId` = `null` | The sentinel is rejected. |
| `replayable`, `kind` | *(dropped)* | Constant across 315 events, so they carried no information. |
| — | `sequence`, `previousHash` | The deployment had no chain; adoption must add one. |

The last row is the real cost of adoption. Everything else is a rename; the
hash chain has to be produced by the writer and cannot be reconstructed from a
stream that never had it.

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

For automation, keep the transition explicit:

```text
ERROR (fact) -> Strategy candidates (target-owned proposals)
             -> Policy filter (invariants + prohibitions)
             -> authorized execution or safe terminal exit
             -> verification -> receipt
```

A policy filter may return `retry-later`, `degraded`, `no-change` or
`escalation-required`; those are valid exits, not governance failures. It must
not reinterpret ERROR as success, prescribe one hardcoded recovery command or
reserve work forever after independently verifiable terminal evidence exists.
