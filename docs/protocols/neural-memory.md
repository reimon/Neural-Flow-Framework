# Protocolo Neural-Memory

## Missao

Substituir a leitura linear de arquivos de memória por recuperação semântica ativa em um índice vetorial, garantindo que o agente acesse contexto relevante de forma cirúrgica sem inflar o prompt.

## Regra inegociavel

O agente de IA nao deve ler arquivos de memória inteiros no prompt. Toda consulta de contexto histórico deve passar pelo índice vetorial via MCP tool `query_neural_memory`.

## Backend-agnostico por desenho

O protocolo define **contratos**, nao tecnologia. Qualquer backend que cumpra os contratos abaixo e conforme:

| Contrato | Requisito |
| --- | --- |
| Indexacao | Chunks de markdown/git/sessao com `source_file`, `type`, `timestamp` e embedding |
| Busca | Hibrida (keyword + vetorial), top-K, filtros por `type` e `sprint` |
| Interface | MCP tools `query_neural_memory(question, top)` e `check_contradiction(proposal)` |
| Atualizacao | Reindex incremental por commit (hook) e por push (CI) |
| Reconstrucao | Indice 100% derivado do git — nunca fonte primaria de verdade |

Backends validados:

| Backend | Quando usar | Implementacao de referencia |
| --- | --- | --- |
| Azure AI Search + Azure OpenAI | Projeto ja em Azure; busca semantica gerenciada | Este repo: `scripts/ingest.py`, `scripts/search.py`, `mcp/neural-memory-server/` (Python) |
| PostgreSQL + pgvector | Projeto ja tem Postgres; evitar servico e runtime extras | Padrao validado em campo: 100% no monolito Node, HNSW no pgvector, sem container Python |
| Outro (SQLite-vec, Qdrant, etc.) | Cumprir os contratos acima | — |

Licao de campo: a melhor stack de memoria e a que **ja mora dentro do projeto**. Se o projeto tem Postgres, pgvector elimina um servico gerenciado, uma linguagem extra e custo fixo — o descomissionamento do Azure Search la foi consequencia disso. A stack Azure deste repo permanece como implementacao de referencia para projetos que ja operam em Azure.

## Fontes indexadas

| Fonte                           | Tipo              | Descrição                                               |
| ------------------------------- | ----------------- | ------------------------------------------------------- |
| `docs/NEURAL-MEMORY.md`         | `markdown / seed` | Seed document com regras e estado consolidado           |
| `docs/protocols/*.md`           | `markdown`        | Protocolos nucleares indexados como âncoras de política |
| `docs/Manifest-Dev-AI.md`       | `markdown / seed` | Manifesto — fonte de verdade canônica                   |
| `docs/adr/*.md`                 | `markdown / adr`  | Decisões arquiteturais aceitas                          |
| `MEMORY.md`                     | `markdown`        | Memória viva do projeto (Solutions Log datado)          |
| `apps/**/sprints/*.md`          | `markdown`        | Registros detalhados de sprint                          |
| `docs/sessoes/sprints/*.md`     | `session`         | Memória de sessão incremental                           |
| `git log` (últimos 200 commits) | `commit`          | Intenção e delta de cada commit                         |

## Pipeline de ingestão

```
[evento] → [chunker] → [embedding] → [índice vetorial]
    ↑
git commit (post-commit hook)
CI/CD push em docs/** ou apps/**
```

Implementação de referência (Azure): `scripts/ingest.py`

Para ativar o hook local:

```bash
bash scripts/setup-hooks.sh
```

## Interface de consulta

### Via MCP (modo primário — qualquer cliente MCP: Claude Code, Copilot, Cursor)

```
query_neural_memory(question="<intenção da tarefa>", top=5)
check_contradiction(proposal="<proposta de mudança>")
```

Registro do servidor MCP: `.vscode/mcp.json` (VS Code) ou `.mcp.json` (Claude Code)

### Via CLI (fallback — implementação Azure)

```bash
python scripts/search.py "decisão sobre auth JWT" --top 5
python scripts/search.py "estouro de budget" --type commit
python scripts/search.py "permissões de admin" --sprint sprint-3
```

## Integração com Circuit Breaker

Quando `check_contradiction` retorna **BLOCK**:

1. O Circuit Breaker é acionado automaticamente.
2. A execução é interrompida (modo proteção ativa).
3. O agente registra o bloqueio no snapshot operacional da sprint com `status: bloqueada`.
4. Rearme exige revisão e aprovação humana explícita.

`check_contradiction` também deve sinalizar (WARNING/BLOCK) propostas que contradizem ADR aceito (`docs/protocols/adr-governance.md`).

## Criterio PASS

- Toda tarefa relevante precedida de chamada a `query_neural_memory`
- Nenhuma decisão contradiz um chunk `[SEED]` ou ADR aceito sem exceção formal registrada
- Index atualizado após cada commit (post-commit hook ativo) ou push (CI)
- `NEURAL-MEMORY.md` reflete o estado operacional atual do repositório

## Criterio FAIL

- Agente usa leitura de arquivo inteiro em substituição ao MCP tool
- Proposta executada após `check_contradiction` retornar `BLOCK` sem aprovação humana
- Index não atualizado por mais de 5 commits consecutivos
- Backend do índice tratado como fonte primária (não reconstruível a partir do git)

## FinOps de RAG

| Operação                                                    | Custo estimado                        |
| ----------------------------------------------------------- | ------------------------------------- |
| Embedding de 1 chunk (~300 tokens)                          | USD 0,000006                          |
| Full reindex (~200 chunks)                                  | USD 0,001                             |
| 3 queries por sessão de sprint                              | USD 0,000045                          |
| Leitura completa NEURAL-MEMORY.md no prompt (modelo antigo) | ~2.000 tokens = USD 0,006+ por sessão |

**ROI positivo a partir de 2 sessões de sprint por semana.** Com pgvector no banco existente, o custo fixo do serviço de busca gerenciado cai a zero.

## Evidencias esperadas

- Ingestão em dry-run exibe chunks parseados sem erro
- Busca CLI retorna resultados com `source_file` e `timestamp`
- MCP tool `query_neural_memory` responde no cliente com chunks formatados
- `check_contradiction` retorna `BLOCK` para proposta que contradiz o manifesto (teste de sanidade)
- Reindex do CI executa sem falha após push em `docs/**`
