# Architecture Decision Record (ADR) Format

## Neural-Flow Projects (Sovereign Format)

When working in a Neural-Flow repository (`docs/adr/_template.md` or `scripts/nf_gate.py` exists), **always** use the Neural-Flow ADR format (`docs/protocols/adr-governance.md`) so `python3 scripts/nf_gate.py adr` passes:

- **File name**: `docs/adr/ADR-NNN-<kebab-case-slug>.md` (3-digit sequential number, never reused)
- **Required sections**:
  - `## Status`: `Proposto | Aceito (Sprint N) | Superado por ADR-MMM | Rejeitado`
  - `## Contexto`: factual problem and forces (1-3 paragraphs)
  - `## Decisao`: active-voice decision and components
  - `## Consequencias`: `Positivas:`, `Trade-offs:`, `Fora de escopo nesta etapa:`
  - `## Evidencia (Neural-Flow)`:
    - `- Sprint de origem: \`Sprint N\``
    - `- Guard associado (se a decisao impoe regra): \`<script/comando ou "nao aplicavel">\``
    - `- Artefatos: \`<commits, PRs, docs>\``
- **Governance rule**: Portuguese without accents (`sem_acento`) in Neural-Flow governance artifacts. Accepted ADRs are immutable; a change of direction requires a new ADR that supersedes the old one.

---

## General Deep-Module ADR Guidance (Domain Modeling Content)

Inside `## Contexto`, `## Decisao`, and `## Consequencias`, include the domain-modeling substance below:

- **Interface**: types, functions/methods, inputs, outputs, and errors exposed by the deep module.
- **Hidden complexity**: internal details, state, storage, or algorithms hidden behind the interface.
- **Dependency direction**: which modules depend on which, and what boundaries are enforced.
- **Testing strategy**: how the module is tested at its public boundary (in-memory / boundary tests vs mocks).
