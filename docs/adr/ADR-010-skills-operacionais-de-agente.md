# ADR-010 — Empacotamento e ativacao autonoma de skills operacionais (mattpocock/skills) sob soberania dos guards

## Status

Aceito (Sprint 8)

## Contexto

O Neural-Flow estabelece governanca verificavel por maquina (sprints, ADRs,
especificacao de modulos, base documental do produto, calibracao de confianca,
principios de execucao de Karpathy e auditoria com `smoke-gate`). Contudo, na
execucao cotidiana de descoberta, entrevista de requisitos, decomposicao em
fatias verticais, TDD estrito (red-green-refactor), modelagem de dominio
(*deep modules*), diagnostico de bugs e revisao de codigo, os agentes de IA se
beneficiam de roteiros taticos passo a passo (*skills*).

O repositorio `https://github.com/mattpocock/skills` consolida 27 skills
operacionais promovidas (`skills/engineering` e `skills/productivity`). Porem,
no repositorio de origem:

1. A maioria das skills traz `disable-model-invocation: true` no frontmatter de
   `SKILL.md` e `allow_implicit_invocation: false` em `agents/openai.yaml`, o
   que impede que o agente as acione proativamente sem que o humano digite um
   slash command manual.
2. Algumas instrucoes originais assumem formatos de artefato ou acoes de git que
   divergem da governanca do Neural-Flow (por exemplo, ADRs de um paragrafo sem
   secoes em `domain-modeling`, ou instrucoes de commitar diretamente em
   `implement` e `implement-spec`).

Precisamos que todo projeto onde o Neural-Flow for instalado ja receba essas
skills prontas para uso imediato por qualquer agente (Claude Code, Cursor,
Codex, Gemini, Antigravity, Windsurf, Cline, Copilot), operando de forma
autonoma em conjunto com as diretrizes e skills que o framework ja possui, sem
depender de rede durante `nf_install.py` e sem violar nenhum guard.

## Decisao

1. **Empacotamento offline no kit (`templates/skills/`):** incorporamos as 27
   skills do pacote oficial promovido de `mattpocock/skills` (`engineering` +
   `productivity`) em `templates/skills/<skill-name>/`. O instalador
   (`scripts/nf_install.py`) e o gerador de portas (`scripts/nf_agentes.py --escrever`)
   distribuem esse catalogo tanto em `.agents/skills/` (padrao multi-agente /
   Agent Skills) quanto em `.claude/skills/` (descoberta nativa do Claude Code).
2. **Ativacao autonoma pelo modelo:** removemos `disable-model-invocation: true`
   dos `SKILL.md` e `allow_implicit_invocation: false` dos `agents/openai.yaml`,
   para que os agentes selecionem e apliquem as skills automaticamente conforme
   a fase do trabalho:
   - **Descoberta e alinhamento:** `grill-me`, `grill-with-docs`, `grilling`,
     `wait-what`, `to-questionnaire`, `research`, `wayfinder`, `ask-matt`, `teach`.
   - **Especificacao, arquitetura e planejamento:** `to-spec`, `domain-modeling`,
     `codebase-design`, `to-tickets`, `writing-for-agents`.
   - **Implementacao, TDD e manutencao:** `tdd`, `implement`, `implement-spec`,
     `improve-codebase-architecture`, `diagnosing-bugs`, `triage`, `prototype`,
     `wizard`, `setup-matt-pocock-skills`.
   - **Revisao, entrega e continuidade:** `code-review`, `pr`, `handoff`, `retro`.
3. **Soberania dos contratos e guards do Neural-Flow:** adaptamos as skills
   empacotadas e determinamos nas portas de entrada (`AGENTS.md`, `CLAUDE.md` e
   portas geradas por `scripts/nf_agentes.py`) que as skills fornecem o
   **metodo tatico**, enquanto o Neural-Flow detem o **contrato de artefato e
   seguranca**:
   - ADRs seguem `templates/adr-template.md` (`docs/adr/ADR-<NNN>-<slug>.md`) e
     passam em `python3 scripts/nf_gate.py adr`.
   - Especificacoes de modulo seguem `templates/spec-modulo-template.md`
     e passam em `python3 scripts/nf_gate.py spec`.
   - Planejamento de execucao registra sprint em `docs/sprints/sprint-<NN>.md` e
     passa em `python3 scripts/nf_gate.py sprint`.
   - Implementacao combina `tdd` + principios de Karpathy + `smoke-gate` +
     `python3 scripts/nf_gate.py`, e **nunca** executa `git commit` ou `git push`
     sem autorizacao humana explicita.
4. **Verificacao automatica (`P6`):** `scripts/validate_agent_entrypoints.py`
   verifica que todas as skills obrigatorias estao instaladas nos diretorios de
   skills presentes no projeto e que nenhuma delas bloqueia a invocacao pelo
   modelo com `disable-model-invocation: true`.

## Consequencias

Positivas:

- Qualquer projeto que instale o Neural-Flow recebe imediatamente o arsenal de
  27 skills taticas em `.agents/skills/` e `.claude/skills/`, compativel com
  Claude Code, Cursor, Codex, Gemini/Antigravity e demais ferramentas.
- Os agentes combinam os principios de execucao ja existentes (Karpathy,
  calibracao, `smoke-gate`, gates) com metodologias taticas maduras (TDD
  red-green-refactor, *deep modules*, *grilling*, fatias verticais).
- O guard `agentes` (`P6`) impede que skills obrigatorias sejam removidas ou
  tenham sua invocacao automatica desativada por acidente.

Trade-offs:

- Aumenta o numero de arquivos copiados pelo instalador em `.agents/skills/` e
  `.claude/skills/`, exigindo que `scripts/nf_product_docs.py` ignore esses
  diretorios ocultos na descoberta de documentos de produto.

Fora de escopo nesta etapa:

- Skills experimentais (`skills/laboratory`) ou especificas de Obsidian (`skills/obsidian`).

## Evidencia (Neural-Flow)

- Sprint de origem: `Sprint 8`
- Guard associado: `python3 scripts/nf_gate.py agentes` (`scripts/validate_agent_entrypoints.py` — P1–P6) e `tests/test_guards.py`
- Artefatos: `scripts/nf_agentes.py`, `scripts/nf_install.py`, `scripts/validate_agent_entrypoints.py`, `docs/protocols/agent-entrypoints.md`
