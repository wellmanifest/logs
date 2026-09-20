# Ticket 020: Align governance workflow pin with adopted standard

- **ID**: ticket-020
- **Owner**: unresolved:human
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-09-20

## Goal and scope

`.github/workflows/governance.yml` still pins the pre-adoption reusable
workflow `wellmanifest/new-project@e65857ea`, whose gate predates the
ticket-activity override and the adopted package manifest format. Pin it to
the revision adopted by ticket-018 (`b6ba9c21`, new-project 0.20.32) so the
push-time gate on `main` matches the adopted standard.

## Acceptance criteria

- [x] The `uses:`/`standard-ref` pins reference `b6ba9c21a65a6a5648ecf904b64c3b75295e136f`.
- [x] `project/governance-check.sh` passes with zero findings.
- [ ] Push-time `governance` run on `main` succeeds after merge.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
