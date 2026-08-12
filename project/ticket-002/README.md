# Ticket 002: Remove stale grammar copy from Docker image

- **ID**: ticket-002
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: VALIDATION
- **Created**: 2026-08-12

## Goal and scope

Correct the committed bootstrap `Dockerfile`: it references repository
directories before they exist and specifically contains a stale `grammar/`
copy even though the bounded GBNF contract is embedded in the JSON contract.
Use one repository copy boundary with explicit `COPY --exclude` filters, so
the seed image can be built and the later functional ticket can add runtime
files without changing container assembly again.

## Acceptance criteria

- [x] AC-01: The parent request's session execution authorization covers the
  blocking bootstrap repair; no human-owned participant file is synthesized.
- [x] AC-02: `Dockerfile` no longer names absent implementation directories.
- [x] AC-03: `COPY --exclude` filters exclude Git state, local environments,
  caches, credentials and build products from the image layer.
- [ ] AC-04: A build made from committed bootstrap content succeeds with the
  pinned Python digest, and governance validation passes.

## Authorization

The user's request to create and implement the repository authorizes this
non-overlapping prerequisite repair, commit, public repository creation,
ticket-branch push and pull request. It does not authorize secret access,
tag/release publication, direct implementation push to `main` or self-review.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)
