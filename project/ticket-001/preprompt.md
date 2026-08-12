# Ticket preprompt

- **Task ID**: ticket-001
- **Task title**: Define logs DSL control plane
- **Created**: 2026-08-12T18:15:02Z

Keep executable implementation outside this governance/evidence directory.
Read a human-owned user-*.md file only when one exists.
The request to execute this work creates SESSION_EXECUTION_AUTHORIZATION;
proceed within the recorded intent without a redundant confirmation prompt.
Require new authority for destructive action, secrets, external coordination,
material objective expansion and trusted merge approval.

Technical references inspected before planning:

- `wellmanifest/poa` POA v1 closed authoring and receipt contracts;
- `wellmanifest/wellm/docs/SOA_POA_CQRS_ES.md` command/query/event mappings;
- `wellmanifest/wellm/proto/wellmanifest/v1/wellmanifest.proto` Protobuf
  envelope conventions;
- `wellmanifest/dsl/spec/DSL_STANDARD.md` canonical/projection, ownership and
  discoverable diagnostic rules.

Implementation directives:

- protobuf is canonical; JSONL and Markdown are deterministic projections;
- LLM generation remains propose-only and cannot create authority;
- source/tests/scripts stay outside this ticket directory;
- use stable `LOGS-*` codes with exact `errors/{CODE}.md` routes;
- preserve unknown repository data and never auto-clean user work.
