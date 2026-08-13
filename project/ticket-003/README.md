# Ticket 003: Protect main with trusted governance approval

- **ID**: ticket-003
- **Owner**: unresolved:human
- **Status**: DONE
- **Workflow state**: DONE
- **Created**: 2026-08-12

## Goal and scope

Repair the repository protection bootstrap discovered during publication of
ticket 001. Add one immutable caller for the adopted `wellmanifest/new-project`
reusable governance workflow, allowlist only the installed Validator App, and
activate a no-bypass default-branch ruleset that requires pull requests,
independent approval, current-head governance evidence and remote lifecycle
validation.

## Acceptance criteria

- [x] AC-01: The human explicitly authorized a separate infrastructure ticket,
  protected governance workflow, `main` protection, revalidation and merge.
- [x] AC-02: The caller pins both the reusable workflow and `standard-ref` to
  adopted published revision `63a03d0c2ec417f8eab9a6edb3c4ed654937a1ac`.
- [x] AC-03: Approval resolution accepts only exact login
  `ifuri-validator-agent[bot]`, current HEAD and the ticket owning the diff;
  evidence is created in protected runner temporary storage outside checkout.
- [x] AC-04: An active ruleset protects the default branch with no bypass,
  blocks deletion/non-fast-forward changes, requires a pull request, one
  independent current-head approval, resolved review threads and both
  governance status contexts.
- [x] AC-05: `delete_branch_on_merge=true` remains enabled and remote lifecycle
  validation passes with every non-default branch owned by an open PR.
- [x] AC-06: The bootstrap PR receives exact-head Validator App review; after
  integration, a governance-only closure PR proves the new resolver and ruleset
  before the ticket becomes `DONE / DONE`.

## Authorization

The user's explicit `tak` authorizes this bounded infrastructure remediation,
including the caller workflow, repository ruleset, protected verification,
ticket branch push, PR, merge after independent approval, revalidation of PR #2
and lifecycle cleanup. It does not authorize secrets, tag/release publication,
direct pushes to `main`, bypass actors or self-approval.

One bootstrap merge is unavoidable because a workflow and ruleset cannot
retroactively protect the PR that introduces them. That PR still requires the
existing remote-lifecycle check and exact-head Validator App approval. All
subsequent PRs must pass the new protected resolver.

## Participants

- Human participant: unresolved; no user-* file was created by this script.
- Agent participant: [ai-codex.md](ai-codex.md)

## Closure evidence

Bootstrap PR #4 received exact-head Validator App approval for
`b4f645d3b91a55a2114aa5957feec7cc6a93e062` and merged into `main` as
`099bc40b7c962523a5b7266734573362dd769329`; GitHub then deleted its remote
ticket branch. Ruleset `20795590` is active for the default branch with no
bypass actors and requires an independent current-head approval plus both
governance contexts. This governance-only closure, created from that integrated
`main`, becomes canonical only after those protections accept and merge it.
