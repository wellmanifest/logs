# Ticket 001: Define logs DSL control plane

- **ID**: ticket-001
- **Owner**: unresolved:human
- **Status**: DONE
- **Workflow state**: DONE
- **Created**: 2026-08-12

## Goal and scope

Create the first `wellmanifest/logs` contract and deterministic conformance
runtime. Protobuf is the canonical cross-language type model. Repository-owned
projections use canonical JSONL event streams under `logs/` and structured
Markdown runbooks under `errors/{CODE}.md` with one embedded
`log-error-dsl` object.

The architecture follows POA, CQRS and Event Sourcing:

- POA binds operations to exact `logs://.../(query|command)/...` processes and
  keeps authored planning requests separate from execution authority;
- CQRS keeps append commands distinct from validation and stream-projection
  queries;
- Event Sourcing treats each JSONL line as an immutable fact with a monotonic
  sequence and SHA-256 predecessor chain;
- deterministic validation, not an LLM, decides whether logs and error pages
  conform.

## Acceptance criteria

- [x] AC-01: A single autonomous seed baseline contains only governance,
  required root files and pinned Docker configuration; its real SHA was
  recorded before implementation, then the delivery base was refreshed only
  after the non-overlapping Docker repair merged.
- [x] AC-02: The Protobuf v3 contract defines separate command, query, event,
  error-definition, finding, projection and receipt messages without generic
  shell, credential or transport fields.
- [x] AC-03: Closed JSON Schema and GBNF contracts accept only bounded planning
  requests; model-authored input cannot append, authorize, select a path or
  invent an execution URI.
- [x] AC-04: `logs/*.jsonl` validation enforces canonical encoding, exact
  fields, monotonic sequence, stream identity, predecessor/event hashes,
  bounded evidence and explicit `rawOutputIncluded=false` and
  `secretMaterialIncluded=false`.
- [x] AC-05: Every emitted `LOGS-*` code has exactly one
  `errors/{CODE}.md`; title, filename, required sections and embedded error DSL
  agree, and every event code resolves to that catalog.
- [x] AC-06: The standard-library Python checker returns stable findings and
  adversarial tests reject unknown fields, unsafe flags, broken chains,
  undocumented codes, malformed runbooks and authority-bearing LLM requests.
- [x] AC-07: Architecture and logic-flow documents include POA/CQRS/ES diagrams,
  authority boundaries, Protobuf mapping, failure semantics and safe extension
  rules.
- [ ] AC-08: Host conformance, pinned networkless Docker validation, Buf lint,
  governance gate and protected PR checks pass before trusted merge.

## Authorization

The user's explicit request to create and implement `wellmanifest/logs`
creates `SESSION_EXECUTION_AUTHORIZATION` for this bounded scope. It authorizes
the post-baseline creation of the public GitHub repository, ticket-branch push
and pull request. It does not authorize direct push to `main`, secret access,
tag/release publication or treating the session as trusted merge approval.

The unborn-repository exception authorizes exactly one local governance-only
seed commit. It does not authorize a remote, push, PR, merge, tag or release.

The independent Docker bootstrap defect was corrected and merged under the
non-overlapping infrastructure ticket. The implementation reservation resumed
at `IN_PROGRESS / EDIT` on the exact accepted base before validation and any
further changes to its five implementation paths.

## Participants

- Human participant: unresolved; no `user-*` file was created.
- Agent participant: [ai-codex.md](ai-codex.md)

## Ticket directory boundary

This directory contains governance, decisions and evidence only. Contracts,
source, tests, examples and documentation remain in their normal repository
directories declared by `intent.json`.
