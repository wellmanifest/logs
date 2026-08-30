# Ticket 009: Adopt new-project 0.19.10 dynamic registries

- **ID**: ticket-009
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: PUBLICATION
- **Created**: 2026-08-30

## Goal and scope

Adopt the immutable `wellmanifest/new-project` 0.19.10 package so ticket
allocation and governance checks resolve lifecycle statuses and workstreams
from the repository manifest instead of stale hardcoded projections.

The upgrade is one hash-bound managed transaction from the currently pinned
0.16.2 revision. It does not rewrite historical ticket carriers and does not
treat Markdown as a terminal receipt.

The ticket uses the manifest-declared `governance` workstream. Managed files
that cross target ownership are not local exceptions: the gate derives their
closed set from the immutable package manifest, base/head locks and verified
content digests. The same managed registry declares the exact revision-bound
workflow path, so the wrapper and both of its immutable SHA pins can advance in
this transaction without a hardcoded runtime exception. Non-managed target
files remain under their own workstreams.

## Acceptance criteria

- [x] AC-01: the lock pins published revision
      `edce26953b46d3ba4096b1942bdf86bcce4edaf0` and version 0.19.10.
- [x] AC-02: every managed target matches its recorded digest and the local
      manifest keeps repository-owned extensions.
- [x] AC-03: governance allocation no longer blocks new work because ticket
      007 remains as historical `IN_PROGRESS` prose on integrated `main`.
- [x] AC-04: Logs conformance, Docker and upgraded governance gates pass.

## Authorization

The user's instruction to repair this class of failures with dynamic
registries is `SESSION_EXECUTION_AUTHORIZATION` for this bounded adoption and
publication. `--force-new` crossed only the stale carrier in the old allocator;
the new standard must make that override unnecessary for this case.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
