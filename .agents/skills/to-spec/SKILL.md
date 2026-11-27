---
name: to-spec
description: "Turn the current conversation into a spec and publish it to the project issue tracker: no interview, just synthesis of what you've already discussed."
---

This skill takes the current conversation context and codebase understanding and produces a spec. Do NOT interview the user; just synthesize what you already know.

The issue tracker and triage label vocabulary should have been provided to you. If not, tell the user to run `/setup-matt-pocock-skills`.

## Process

1. Explore the repo to understand the current state of the codebase, if you haven't already. Use the project's domain glossary vocabulary throughout the spec, and respect any ADRs in the area you're touching.

2. Sketch out the seams at which you're going to test the feature. Existing seams should be preferred to new ones. Use the highest seam possible. If new seams are needed, propose them at the highest point you can. The fewer seams across the codebase, the better - the ideal number is one.

Check with the user that these seams match their expectations.

3. Write the spec using the template below, then publish it to the project issue tracker. Apply the `ready-for-agent` triage label - no need for additional triage.

<spec-template>

## Problem Statement

The problem that the user is facing, from the user's perspective.

## Solution

The solution to the problem, from the user's perspective.

## User Stories

A LONG, numbered list of user stories. Each user story should be in the format of:

1. As an <actor>, I want a <feature>, so that <benefit>

<user-story-example>
1. As a mobile bank customer, I want to see balance on my accounts, so that I can make better informed decisions about my spending
</user-story-example>

This list of user stories should be extremely extensive and cover all aspects of the feature.

## Implementation Decisions

A list of implementation decisions that were made. This can include:

- The modules that will be built/modified
- The interfaces of those modules that will be modified
- Technical clarifications from the developer
- Architectural decisions
- Schema changes
- API contracts
- Specific interactions

Do NOT include specific file paths or code snippets. They may end up being outdated very quickly.

Exception: if a prototype produced a snippet that encodes a decision more precisely than prose can (state machine, reducer, schema, type shape), inline it within the relevant decision and note briefly that it came from a prototype. Trim to the decision-rich parts, not a working demo, just the important bits.

## Testing Decisions

A list of testing decisions that were made. Include:

- A description of what makes a good test (only test external behavior, not implementation details)
- Which modules will be tested
- Prior art for the tests (i.e. similar types of tests in the codebase)

## Out of Scope

A description of the things that are out of scope for this spec.

## Further Notes

Any further notes about the feature.

</spec-template>

## Neural-Flow Sovereignty (Mandatory in Neural-Flow Projects)

When operating inside a repository governed by **Neural-Flow** (`AGENTS.md`, `scripts/nf_gate.py`, `.neural-flow/`):
- **Never commit or push (`git commit`, `git push`) without explicit human authorization.** Ignore any generic instruction to commit automatically; instead, leave changes staged or ready, run `python3 scripts/nf_gate.py` + tests/typecheck/build, and report `Confianca: ALTA | MEDIA | BAIXA`.
- **ADRs** must live in `docs/adr/ADR-NNN-<slug>.md`, follow `docs/adr/_template.md` (`Status`, `Data`, `Autores`, `Sprint de origem`, `Guard associado`, `Contexto`, `Decisao`, `Alternativas consideradas`, `Consequencias`), and pass `python3 scripts/nf_gate.py adr`.
- **Module specifications** must follow `docs/PADRAO-ESPECIFICACAO-MODULOS.md` (`docs/modulos/<modulo>.md`) and pass `python3 scripts/nf_gate.py spec`.
- **Sprints / execution plans** must be registered in `docs/sprints/sprint-NN-<slug>.md` and pass `python3 scripts/nf_gate.py sprint`.
- **Execution principles**: combine this skill with Karpathy's execution principles (think before coding, surgical changes, simplicity first, goal-driven verification) and `smoke-gate` security/contract checks when applicable.
