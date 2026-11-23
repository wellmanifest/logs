# Ticket 026: Extend wellmanifest/logs with uritime project integration profile and guide

- **ID**: ticket-026
- **Owner**: agent:antigravity (`SESSION_EXECUTION_AUTHORIZATION`)
- **Status**: IN_PROGRESS
- **Workflow state**: EDIT
- **Created**: 2026-11-23

## Goal and scope

Extend the existing `wellmanifest/logs` standard additively (without modifying
immutable v0.2–v0.5 contracts, `urtlog-bridge.*.v1.json`, `proto/v0.5`,
`README.md`, or `CHANGELOG.md`) with a closed machine-readable profile
(`wellmanifest.logs/uritime-integration-profile/v1`), dependency-free
conformance checker wired into `logs_check.py` and `logs_selftest.py`,
adversarial unit tests, and a comprehensive normative information guide
describing how projects adopt and integrate `uritime`, `uritime-urt`, and
`uritime-urtlog` alongside `wellmanifest/polycell`, `uritime/autonom`, `Forge`,
and `wellmanifest/autonomy` execution controllers.

## Acceptance criteria

- [ ] AC-01: Closed schema `contracts/uritime-integration.schema.v1.json` and
      canonical profile `contracts/uritime-integration.profile.v1.json` validate
      cleanly with `python3 standard/logs_check.py uritime-integration --root .`.
- [ ] AC-02: Existing `logs_check.py validate --root .`, `urtlog-bridge --root .`,
      `self-test` (exercising both `urtlog-bridge` and `uritime-integration`
      adversarial mutations), and all unit tests under `standard/` pass with
      zero regressions and zero skipped tests.
- [ ] AC-03: `docs/information/uritime-project-integration.md` passes
      `wellmanifest/docs` checks (`--prepare` and `--deliverable`), is indexed in
      `docs/README.md`, and `./project/governance-check.sh --base origin/main`
      plus `wellman check --root .` pass cleanly.

## Tracking boundary

This directory contains the minimal reviewed intent. Optional participant prose
and raw command logs are not required delivery output.
