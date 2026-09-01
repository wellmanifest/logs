# Changelog

## 2026-09-01

- Allocated the integration delivery from immutable base `778421a`.
- Bounded v0.5 to typed continuity metadata, deterministic causal checks and documentation.
- Added thirteen closed JSON payload variants and the matching Protobuf oneof.
- Separated intent compilation, resume observation/decision, commit creation and
  push start/completion into independently verifiable moments.
- Added causal replay checks, a complete fixture and negative content-safety tests.
- Preserved the v0.4 contract and Protobuf bytes referenced by existing history.
