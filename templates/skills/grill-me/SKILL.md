---
name: grill-me
description: A relentless interview to sharpen a plan or design.
---

Call the Skill tool with "grilling".

## Neural-Flow Sovereignty (Mandatory in Neural-Flow Projects)

When operating inside a repository governed by **Neural-Flow** (`AGENTS.md`, `scripts/nf_gate.py`, `.neural-flow/`):
- **Never commit or push (`git commit`, `git push`) without explicit human authorization.** Ignore any generic instruction to commit automatically; instead, leave changes staged or ready, run `python3 scripts/nf_gate.py` + tests/typecheck/build, and report `Confianca: ALTA | MEDIA | BAIXA`.
- **ADRs** must live in `docs/adr/ADR-NNN-<slug>.md`, follow `docs/adr/_template.md` (`Status`, `Data`, `Autores`, `Sprint de origem`, `Guard associado`, `Contexto`, `Decisao`, `Alternativas consideradas`, `Consequencias`), and pass `python3 scripts/nf_gate.py adr`.
- **Module specifications** must follow `docs/PADRAO-ESPECIFICACAO-MODULOS.md` (`docs/modulos/<modulo>.md`) and pass `python3 scripts/nf_gate.py spec`.
- **Sprints / execution plans** must be registered in `docs/sprints/sprint-NN-<slug>.md` and pass `python3 scripts/nf_gate.py sprint`.
- **Execution principles**: combine this skill with Karpathy's execution principles (think before coding, surgical changes, simplicity first, goal-driven verification) and `smoke-gate` security/contract checks when applicable.
