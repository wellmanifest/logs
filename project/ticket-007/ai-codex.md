---
participant-id: agent:codex
participant: codex
role: agent
ticket: ticket-007
---
# Participant: codex (AI agent)

## Understanding

The v0.2 event contract added required fields while consumers continued to use
vendored schemas under the same `wellmanifest.logs/event/v1` identity. Doctor
therefore emitted an older projection that its local schema accepted but the
current standard rejects. The standard needs a deterministic adoption boundary,
not another prose warning.

## Execution plan

1. Add a bounded `adoption` command accepting one consumer event-schema path.
2. Compare the candidate's canonical semantic JSON with the canonical schema
   embedded in the contract bundle and return a typed validation report.
3. Extend self-test with exact and stale schema fixtures.
4. Run conformance, governance and Docker checks before publication.

## Actual changes

- Initialized the bounded ticket and recorded SESSION_EXECUTION_AUTHORIZATION
  from the request to execute this work.
- Added the bounded `adoption --event-schema` conformance command.
- Added positive canonical and negative stale-schema regression fixtures to
  the dependency-free self-test.
- Documented the rule that a divergent consumer must use a separately
  versioned projection rather than reuse the canonical schema identity.
- Verified repository, Docker and governance gates.

## Blockers

- None inside the recorded intent; proceed without a second confirmation.
- New authority remains required for destructive action, secret access, new
  external coordination, material objective expansion and trusted merge.
