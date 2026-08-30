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

The prerequisite `wellmanifest/new-project` 0.19.11 adoption was delivered
separately by ticket 012 and merged as PR 17. This ticket consumes that merged
base; it does not own governance policy or its managed files.

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
- [ ] AC-06: the merged ticket-012 base is present and its verified terminal
      receipt releases the completed governance reservation.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
