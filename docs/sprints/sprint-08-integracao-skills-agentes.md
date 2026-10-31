# Sprint 8: Integracao do pacote oficial mattpocock/skills sob soberania do Neural-Flow

## Snapshot Operacional

- App/Escopo: `empacotamento, instalacao e guard das 27 skills de mattpocock/skills em conjunto com as diretrizes do Neural-Flow`
- Status: `em andamento`
- Tipo de trabalho: `implementacao`
- Data de inicio: `2026-10-19`
- Data planejada de conclusao: `2026-10-19`
- Data real de conclusao: `a definir`
- Ultima atualizacao: `2026-10-19`
- Nivel de autonomia: `A1`
- Blocker principal: `nenhum`
- Proxima acao: `validar suite completa de testes e nf_gate.py antes da revisao do usuario`

## FinOps de Tokens

- Token budget: `250k`
- Limite de alerta: `70%`
- Consumo observado: `85k`
- Mitigacao aplicada: `nao se aplica`

## Objetivo

Incorporar o pacote oficial promovido de `mattpocock/skills` (`skills/engineering` +
`skills/productivity`, 27 skills) ao Neural-Flow para que, ao instalar o framework em
qualquer projeto, os agentes de IA sigam as diretrizes do Neural-Flow e usem sempre essas
skills em conjunto com as ja existentes (Karpathy, calibracao, `smoke-gate` e guards).

## Escopo incluido

- Empacotamento offline das 27 skills em `templates/skills/<skill>/` com invocacao autonoma
  pelo modelo habilitada (sem `disable-model-invocation: true`) e notas de soberania do
  Neural-Flow.
- Instalacao automatica e idempotente em `.agents/skills/` e `.claude/skills/` via
  `scripts/nf_install.py` e sincronizacao via `scripts/nf_agentes.py --escrever`.
- Diretrizes de uso obrigatorio por fase (Descoberta, Especificacao/Planejamento,
  Implementacao/TDD/Arquitetura/Bugs, Revisao/Handoff) em `AGENTS.md`, `CLAUDE.md`,
  `templates/AGENTS-template.md`, `templates/CLAUDE-template.md` e corpo canonico das
  portas de entrada (`scripts/nf_agentes.py`).
- Verificacao automatica `P6` em `scripts/validate_agent_entrypoints.py` e documentacao em
  `docs/protocols/agent-entrypoints.md` e `docs/adr/ADR-010-skills-operacionais-de-agente.md`.
- Exclusao de `.agents`, `.claude`, `.neural-flow`, `.cursor` e `.github` na descoberta de
  documentos de produto em `scripts/nf_product_docs.py`.

## Fora do escopo

- Skills experimentais (`skills/laboratory`) ou especificas de Obsidian (`skills/obsidian`).
- Dependencia de rede no momento de `nf_install.py` para baixar skills externas.
- Commitar ou fazer push sem autorizacao explicita do usuario.

## Criterios de aceite

- CA-001: `templates/skills/` contem as 27 skills oficiais sem `disable-model-invocation: true`.
- CA-002: `python3 scripts/nf_install.py` instala as 27 skills em `.agents/skills/` e `.claude/skills/` de forma idempotente e respeitando `--dry-run`.
- CA-003: `python3 scripts/nf_gate.py` passa todos os 8 guards com `exit 0`, incluindo `P6`.
- CA-004: `python3 -m unittest discover -s tests` passa integralmente com cobertura de instalacao e guard `P6`.

## Checklist de Acoes

- [x] 1.1 Registrar `docs/adr/ADR-010-skills-operacionais-de-agente.md` e `docs/sprints/sprint-08-integracao-skills-agentes.md`.
- [x] 1.2 Incorporar e adaptar as 27 skills de `mattpocock/skills` em `templates/skills/`.
- [x] 1.3 Estender `scripts/nf_agentes.py`, `scripts/nf_install.py`, `scripts/validate_agent_entrypoints.py` (`P6`) e `scripts/nf_product_docs.py`.
- [x] 1.4 Atualizar `AGENTS.md`, `CLAUDE.md`, `templates/AGENTS-template.md`, `templates/CLAUDE-template.md`, `docs/protocols/agent-entrypoints.md`, `MEMORY.md` e `README.md`.
- [x] 1.5 Regerar portas de agente, sincronizar `.agents/skills/` e `.claude/skills/` e regerar `.neural-flow/indice-regras.md`.
- [x] 1.6 Adicionar testes em `tests/test_guards.py` e executar `python3 -m unittest discover -s tests` e `python3 scripts/nf_gate.py`.

## Evidencias

- `python3 -m unittest discover -s tests`: 106 testes executados com sucesso (`OK`).
- `python3 scripts/nf_gate.py`: todos os 8 guards conformes (`PASS`).
