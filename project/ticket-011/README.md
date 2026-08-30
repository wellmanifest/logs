# Ticket 011: Validate adopter-owned error catalogs

- **ID**: ticket-011
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-08-30

## Goal and scope

Let Subactor runtime repositories ADOPT the canonical
`wellmanifest.logs/error/v1` shape while retaining ownership of their own stable
codes and runbooks. Add a read-only command that validates one closed adopter
catalog, its immutable standard digest, namespace and exact Markdown page set.

Before extending that contract, adopt immutable `wellmanifest/new-project`
0.19.11. Its dynamic activity registry makes the integrated tickets 007 and
009 non-blocking from verified, clone-external merge receipts without rewriting
their historical `IN_PROGRESS` prose. Invalid, missing or stale evidence remains
active and has a managed recovery runbook.

This standard owns the reusable shape and conformance rules. It does not own
`ONEDEV-*`, `SUBLLM-*`, `CONFIG-*` or other runtime diagnoses, and it grants no
authority to execute a remediation.

## Acceptance criteria

- [x] AC-01: The user's instruction to continue the audited standardization is
      `SESSION_EXECUTION_AUTHORIZATION` for this bounded implementation.
- [ ] AC-02: a valid adopter-owned catalog and exact runbook set pass against
      the canonical contract digest.
- [ ] AC-03: digest drift, namespace substitution, missing pages, extra pages
      and invalid error definitions fail closed with stable `LOGS-ADOPTION-*`
      findings.
- [ ] AC-04: the closed category vocabulary represents configuration,
      concurrency, dependency, resource and runtime failures without an
      arbitrary category string.
- [ ] AC-05: host, Docker, Buf and governance gates pass.
- [ ] AC-06: the adoption lock pins published `new-project` 0.19.11 and
      verified receipts release only the integrated ticket reservations.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
