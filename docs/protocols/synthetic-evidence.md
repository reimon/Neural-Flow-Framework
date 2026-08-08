# Evidencia Sintetica

## Missao

Garantir que conclusao tecnica dependa de prova verificavel e nao de declaracao textual.

## Regra inegociavel

Toda acao marcada como concluida precisa de evidencia tecnica minima.

## Tipos validos de evidencia

- arquivo alterado com referencia
- teste executado com resultado
- log de execucao relevante
- commit associado
- artefato de pipeline

## Criterio PASS

- cada item concluido possui pelo menos 1 evidencia
- validacao registrada no mesmo ciclo da mudanca
- evidencias apontam para artefatos reais

## Criterio FAIL

- item concluido sem evidencia
- evidencias nao verificaveis
- validacao declarada sem execucao

## Acao automatica em FAIL

- reabrir item como pendente
- bloquear fechamento da sprint
- registrar causa da falha no delta

## Ferramenta de referencia: smoke-gate

`github:reimon/smoke-gate` e a implementacao de referencia do gate de evidencia
para projetos com HTTP + banco relacional. Ela converte "eu acho que esta pronto"
em prova executada:

| Modo | Evidencia produzida |
| --- | --- |
| Runtime gate | Todos os endpoints batidos contra DB real; falha se algum retorna 500 |
| `smoke-gate audit` | Relatorio deterministico de padroes frageis (drift SQL, IDOR, error leak, race condition, cobertura de smoke) |
| GitHub Action | Audit diff-only no PR, comentario sticky, bloqueio de merge em `critical` |
| MCP (`audit_check_sql`) | Validacao de SQL contra o schema em <50ms, antes do agente gerar a query |

Uso no ciclo Neural-Flow:

- **Antes de executar** (agente): `audit_check_sql` via MCP para nao gerar SQL com drift.
- **Ao fechar item**: `npx smoke-gate audit --since origin/main` — relatorio e o artefato de evidencia.
- **No CI**: Action com `fail-on: critical` — o gate deixa de depender de disciplina humana.

Detalhes de adocao: secao "Camada de Guards" no README.

## Evidencias esperadas

- tabela resumo acao x evidencia
- localizacao do artefato
- resultado da validacao
- relatorio `audit-report.md` (ou saida `--json`) quando o projeto usar smoke-gate
