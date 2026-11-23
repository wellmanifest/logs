# Logging documentation

- [Hourly diagnostic storage](information/hourly-diagnostic-storage.md) — current contract status, private source archives, UTC rotation, coverage and bounded LLM evidence.
- [Opt-in URTLog bridge and decision slicing](information/urtlog-bridge-and-decision-slicing.md) — closed `wellmanifest.logs/urtlog-bridge-profile/v1` contract for opt-in `uritime/urtlog` telemetry bridges, `UnifiedRegistry`, `blocked -> unknown/audit` status mapping, and `<= 600` B small-LLM decision slicing.
- [Uritime project integration profile and guide](information/uritime-project-integration.md) — closed `wellmanifest.logs/uritime-integration-profile/v1` contract for single `uritime` temporal ownership, dual-mode `PLAN` → `LOG` lineage, flocked atomic ledgers, `roles.decision` model normalization, PSI-aware admission, and Polycell/Autonom/Forge boundaries.
- [Control-plane architecture](ARCHITECTURE.md) — canonical events, diagnostics, continuity and adopter-owned errors.
- [Logic flow](LOGIC_FLOW.md) — planning, validation and execution boundaries.

The contract version at source revision
`2727b2220ccfac521f98c6c464af766f2df9f63d` is **0.5.0**. The root README's
bootstrap/v0.1 status is historical and does not describe that revision.
The new storage guidance documents an adoption boundary; it does not release
a new event schema or install a logging backend.
