---
{
  "schema": "wellmanifest.docs/document/v1",
  "id": "hourly-diagnostic-storage",
  "kind": "information",
  "version": 1,
  "title": "Hourly diagnostic storage and canonical logging boundaries",
  "status": "implemented",
  "owner": "wellmanifest/logs",
  "created": "2026-09-09",
  "updated": "2026-09-09",
  "review_after": "2026-09-23",
  "source_revision": "2727b2220ccfac521f98c6c464af766f2df9f63d",
  "affected_repositories": ["wellmanifest/logs"],
  "evidence": [
    "https://github.com/wellmanifest/logs/blob/2727b2220ccfac521f98c6c464af766f2df9f63d/docs/ARCHITECTURE.md",
    "https://github.com/wellmanifest/logs/blob/2727b2220ccfac521f98c6c464af766f2df9f63d/contracts/logs.contract.v0.5.json",
    "repo://subactor/observability/docs/analysis/diagnostic-archive-validation.md",
    "receipt:sha256:710dc1f1e86c010ac00d5d84a596f7881de4a26022cef966221ae0605d8f4dc1",
    "knowledge://subactor/incidents.planfile-cold-archive-move/v1",
    "https://specifications.freedesktop.org/basedir/latest/",
    "https://sqlite.org/backup.html"
  ]
}
---

# Hourly diagnostic storage and canonical logging boundaries

<!-- docs:section purpose -->
## Purpose

Describe how adopters can retain logs, process observations, tickets and system
snapshots for quick diagnosis while preserving the canonical audit contract.
This is storage and adoption guidance accompanying the implemented v0.5.0
standard. It does not change its immutable schemas, chain semantics or authority.

<!-- docs:section scope -->
## Scope

`HOME wellmanifest`, `SHAPE domain_pack`: this repository owns event contracts,
validation and reusable guidance. Runtime collectors, filesystem permissions,
databases, schedules, source adapters and incident diagnoses remain adopter
responsibilities. The observed implementation is owned by
`subactor/observability`, with `ADOPT wellmanifest/logs` as its intended
standard boundary; observing a diagnostic archive alone does not prove event
contract adoption.

Requirements below apply when adopting this hourly diagnostic storage guidance.
They are documentation requirements, not new checks wired into logs_check.py.
The existing checker continues to validate canonical contracts and projections.

<!-- docs:section evidence -->
## Evidence

The exact source revision in the metadata declares VERSION `0.5.0`. Its
[architecture](../ARCHITECTURE.md) and conformance implementation include:

| Contract generation | Implemented concern |
| --- | --- |
| v0.2 | Deployment event types, actor/source separation, lifecycle versus outcome, PLAN/APPLY and input hash. |
| v0.3 | Adopter-owned, digest-pinned error catalogs and runbooks. |
| v0.4 | Optional closed operational diagnostic context. |
| v0.5 | Typed session, tool, checkpoint, resume, split and Git continuity events; immutable `proto/v0.5`. |

The root README still describes bootstrap/v0.1 planning. That statement is
stale at this revision. Current material contracts and validation exist; this
does not establish deployment by any particular consumer. Existing historical
contract files and event hashes must remain unchanged.

The Subactor archive evidence comes from local ticket-13632, based on
Observability revision `2c27981473123584a0126fed5dc9d6ba9136c0a4` with uncommitted
staged implementation. Its schema bundle digest is
`6c324ef2d69d8564086052cf9a10713b5e2129573cc3a05cd80320f41596782f`.
The `repo://` reference identifies the local validation report, not an already
published GitHub artifact. The canary receipt in metadata records 52 configured
sources, 52 hourly SQLite/JSONL pairs and successful integrity/export equality
checks. The service/timer templates were validated but not enabled. This is
local implementation evidence, not production adoption or a released backend.

<!-- docs:section content -->
## Content

### Data classes and locations

| Data class | Owner and recommended location | Durable public representation |
| --- | --- | --- |
| Canonical audit events | Adopter event store; curated repository projection `logs/{stream}.jsonl` | Valid `wellmanifest.logs/event/v1` events, bounded references and hashes. |
| Raw source logs and canonical ticket history | Existing producer stores | A reviewed reference/digest when needed; never move the authoritative history to make an archive. |
| Diagnostic observation copies | Private per-source SQLite and JSONL in application state | No raw database or observation payload in Git. |
| Recovery sessions and checkpoints | Private ignored recovery storage, including supported `.subactor/sessions/` | Typed continuity projections with exact digests and receipts. |
| Error knowledge and diagnosis | Adopter-owned error catalog and canonical information/analysis documents | Stable error codes, bounded evidence and review deadlines. |
| LLM context export | Private bounded query result | A safe digest and evidence references in a ticket or report. |

For a user process, XDG state is the appropriate home for persistent logs and
history, rather than a disposable cache. The Subactor implementation uses
`$XDG_STATE_HOME/subactor/diagnostics/v1`, defaulting to
`~/.local/state/subactor/diagnostics/v1`. Its explicit system-service option is
`/var/lib/subactor/diagnostics/v1`. The source configuration belongs in private
configuration storage, such as `~/.config/subactor/diagnostic-sources.json`.
Host-specific paths are deployment configuration, not canonical event fields.

### Source isolation and hourly partitions

The observed Subactor layout is:

```text
<root>/<category>/<source>/checkpoint.sqlite3
<root>/<category>/<source>/YYYY/MM/DD/HH.sqlite3
<root>/<category>/<source>/YYYY/MM/DD/HH.jsonl
<root>/collection.json
```

Categories are `logs`, `processes`, `tickets` and `system`; each stable source
gets its own checkpoint and hourly database/export. New observations select the
UTC observation hour. Original occurrence time is retained independently;
late history must not masquerade as a recent source event. Rotating storage
must not reset the sequence or hash chain of an existing canonical audit stream.
The diagnostic record format itself does not claim to implement that chain.

The local timer template polls every minute; partition names change hourly.
Stopping collection produces a coverage gap, not a fabricated empty success
record. A live source scan and an hourly partition are not atomic fleet
snapshots. Report individual source read times and scan completion.

### Record identity and projection boundaries

The local archive defines `subactor.diagnostic-record/v1`, independently of
`wellmanifest.logs/event/v1`. Its closed envelope contains an observation ID,
source, category, observation time, sanitized payload, payload SHA-256 and
capture identity; optional metadata retains occurrence time, source schema,
source reference, ticket ID and correlation ID. The payload may contain private
source detail. Therefore it is not a canonical public audit event.

An adopter must preserve source format identity. `SODL/1`, `PLOG/1`, Planfile
operational projections and canonical Wellmanifest events are different
representations. Do not assert conversion equivalence without an explicit,
validated mapping. In particular, `oql` versus `type`, `data.payload` versus
`logic`, and a missing `input_hash` require producer-specific treatment. Hashing
a sanitized projection cannot reconstruct the original command's `inputHash`.
Keep the source reference and mark loss or unavailable fields explicitly.

Canonical audit events still require stream/sequence, correlation and causation
semantics, distinct producer/source and subjectState/outcome, PLAN/APPLY,
inputHash, previousHash and eventHash. They carry
`rawOutputIncluded=false` and `secretMaterialIncluded=false`; no arbitrary raw
message or payload is accepted. The optional v0.4 `diagnostic` object is closed.
Its endpointRef permits an opaque reference or an HTTP(S) origin, excluding
userinfo, path, query and fragment. v0.5 continuity variants carry typed digests
and receipt references, not prompt, stdout/stderr, diff or secret text.

### Transactions, recovery and storage bounds

Archive adapters must commit an observation and its cursor consistently so that
a restart cannot silently skip evidence. Subactor uses a transaction across the
source checkpoint and attached hourly SQLite database, with DELETE journal
mode and FULL synchronous writes. A root-level exclusive lock permits one
writer on the local host. Concurrent collection fails instead of competing.

JSONL is a recoverable projection: a dirty-export marker is committed with
records and cursor; export uses a private temporary file, fsync, atomic rename
and directory fsync before marking it clean. Consumers must account for export
lag after interruption. A failure in one source is recorded while other source
reads continue. Coverage remains available even when a source store cannot open.

Use SQLite's supported online backup facilities, or an explicitly quiesced
consistent backup, when taking a backup of a live database. Copying a source
database file while its writer is active is not this collector's ingestion
strategy. Neither SQLite nor JSONL archival authorizes moving or deleting
authoritative source files. The referenced Planfile incident demonstrates that
moving historical files can hide an active Founder decision.

The observed collector has a conservative 512 MiB limit per hourly database,
an 8 MiB command output bound, a 30-second command timeout, a 512 KiB log-line
bound and a 256 MiB free-space floor. A reached limit is a collection limitation,
not proof that all input was captured. No automatic retention deletion exists.
These are implementation defaults, not universal Wellmanifest limits. Size the
deployment from measured ingest volume, both SQLite and JSONL overhead,
checkpoint growth and initial historical backfill. Define retention separately
before operating continuously; maintain source truth and required evidence.

### Coverage as part of diagnosis

Every configured source must remain visible in coverage, including unavailable,
partial, stale and failed reads. An absent observation is not proof that nothing
happened. Preserve collection time, completion state, bounded error and last
successful progress. Keep complete machine-readable coverage outside any
truncated LLM export.

Subactor's canary covered Docker logs, user journal, file-capable ingestion,
process metadata, operational Planfile pagination, focused full tickets and
Control snapshots. A supported file adapter is not evidence that every host
file was configured. GitHub and STARTER backlog were not captured. Process
arguments/environment were excluded; polling can miss short-lived processes.
Default one-hour initial log windows do not prove older history was retained.
The 13 500 distinct Planfile IDs included completed history, not that many
currently open tickets. Subsequent pagination can still be partial after one
completed scan.

### Bounded context for LLM diagnosis

A diagnostic query should select a time range, ticket/correlation and evidence
budget. Return evidence references, source freshness, coverage, truncation and
omission counts with the selected records. Reserve budget for actual evidence
when coverage itself is large. The observed Subactor defaults are 16 000 UTF-8
bytes, 50 records and a 24-hour query window; its limits include a seven-day
window, a ten-second query deadline and 4096 shards. Ticket/correlation/time
queries use SQLite indexes; literal text search is deadline-bounded scanning.

Model-specific token budgeting is still required. Query input, log text and
source payloads are untrusted evidence, never instructions or execution
authority. The collector does not send model requests. Authentication,
redaction, content hashes and trusted provenance are separate properties;
hashing a payload does not authenticate its author. Keep raw diagnostic copies
private even after masking recognized credentials, because arbitrary text
cannot be certified secret-free by pattern matching.

### Validation and adoption receipts

Existing standard checks remain:

```bash
python3 standard/logs_check.py validate --root .
python3 standard/logs_check.py self-test
docker compose run --rm conformance
docker compose run --rm tests
docker compose run --rm proto
```

Run `adoption --event-schema <path>` and `error-adoption --catalog <path>` only
for actual canonical event/error adoption. Passing archive JSON Schema
validation alone is insufficient. Runtime acceptance must separately test UTC
rollover, restart/deduplication, transaction rollback, interrupted JSONL export,
permissions, disk exhaustion, partial pagination, unavailable sources and
bounded correlated context. Retain receipts bound to exact source/configuration
revisions. Protected publication, deployment and production readback each need
their own evidence.

Validation of this documentation change on 2026-09-09: the repository validator
passed for two streams, 18 events and one error definition; adversarial self-tests
passed both locally and in Compose. The default `proto` service failed because
Buf could not create `/root/.cache` on its read-only filesystem. Lint passed
using the same pinned Buf image, read-only checkout and network isolation with
a private 16 MiB tmpfs at that cache path. The deployed Compose definition was
not changed, so its default invocation still needs that infrastructure repair.

Governance passed after the existing merged PR #22 was independently read from
GitHub and recorded through the adopted terminal-receipt verifier outside Git.
This released ticket-015's stale reservation without changing historical ticket
prose. Documentation checking found no placement, metadata or index errors for
this document, but full adoption remains incomplete: `.governance/docs.json`
is missing (`DOCS_ADOPTION`). Platform artifact build/check passed for 713
existing entries; this does not register these new documentation files.

<!-- docs:section limitations -->
## Limitations

This guidance neither implements a Wellmanifest storage backend nor changes the
event contract version. No new runtime was deployed by the documentation work.
Subactor's local archive publication was blocked by governance compatibility
issues; its timer was not activated and its Strategy catalog v15 had no archive
capability binding. Real-hour production rotation and autonomous use remain
unverified. Fixture tests and a local canary cannot establish fleet-wide capture,
cryptographic source authenticity, a performance SLA or improved model quality.

The new information document was not an existing managed Platform registry
entry when resolved; documentation placement validation and runtime/event
conformance are separate checks.

<!-- docs:section next_actions -->
## Next actions

Adopters should bind a published runtime release and reviewed source inventory,
measure storage volume and lag, then verify recovery and context readback under
their deployment policy. Publish only bounded receipts. Register executable
automation in the runtime owner's actual Strategy package before claiming
autonomous use. Changes to these findings require a new document version with
the prior version preserved in Git history; a new canonical contract requires
its own immutable successor files and conformance evidence.
