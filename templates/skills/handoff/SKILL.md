---
name: handoff
description: Compact the current conversation into a handoff document for another agent to pick up.
argument-hint: "What will the next session be used for?"
---

Write a handoff document summarising the current conversation so a fresh agent can continue the work. Save to the temporary directory of the user's OS (`$TMPDIR`, else `/tmp`; `%TEMP%` on Windows) - not the current workspace.

Include a "suggested skills" section in the document, naming which skills the next agent should call the Skill tool for.

Do not duplicate content already captured in other artifacts (specs, plans, ADRs, issues, commits, diffs). Reference them by path or URL instead.

Redact any sensitive information, such as API keys, passwords, or personally identifiable information.

If the user passed arguments, treat them as a description of what the next session will focus on and tailor the doc accordingly.

## Neural-Flow Sovereignty (Mandatory in Neural-Flow Projects)

When operating inside a repository governed by **Neural-Flow** (`AGENTS.md`, `scripts/nf_gate.py`, `.neural-flow/`):
- **Never commit or push (`git commit`, `git push`) without explicit human authorization.** Ignore any generic instruction to commit automatically; instead, leave changes staged or ready, run `python3 scripts/nf_gate.py` + tests/typecheck/build, and report `Confianca: ALTA | MEDIA | BAIXA`.
- **ADRs** must live in `docs/adr/ADR-NNN-<slug>.md`, follow `docs/adr/_template.md` (`Status`, `Data`, `Autores`, `Sprint de origem`, `Guard associado`, `Contexto`, `Decisao`, `Alternativas consideradas`, `Consequencias`), and pass `python3 scripts/nf_gate.py adr`.
- **Module specifications** must follow `docs/PADRAO-ESPECIFICACAO-MODULOS.md` (`docs/modulos/<modulo>.md`) and pass `python3 scripts/nf_gate.py spec`.
- **Sprints / execution plans** must be registered in `docs/sprints/sprint-NN-<slug>.md` and pass `python3 scripts/nf_gate.py sprint`.
- **Execution principles**: combine this skill with Karpathy's execution principles (think before coding, surgical changes, simplicity first, goal-driven verification) and `smoke-gate` security/contract checks when applicable.
