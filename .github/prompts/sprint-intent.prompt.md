---
description: "Extrai a intenção de execução da sprint ativa e formula uma query semântica para o banco vetorial neural-memory. Usado no início de cada sessão de sprint para carregar contexto relevante sem inflar o prompt."
applyTo: "apps/**/sprints/*.md, docs/sessoes/sprints/*.md"
---

# Neural-Prompt: Sprint Intent Extractor

## Objetivo

Ao iniciar uma sessão de sprint, extrair a intenção operacional do Snapshot e do Objetivo da sprint ativa e traduzi-la em uma consulta semântica otimizada para o banco vetorial neural-memory.

## Instrução ao agente

Leia o Snapshot Operacional e o Objetivo da sprint ativa e execute:

### Passo 1 — Extrair campos-chave do snapshot

Do arquivo de sprint ativo, identifique:

- `App/Escopo`: o domínio técnico da sprint
- `Objetivo`: o resultado esperado em linguagem natural
- `Fora do escopo`: o que NÃO deve ser feito
- `Blocker principal`: qualquer impedimento atual

### Passo 2 — Compor consultas semânticas

Formule até 3 queries distintas para cobrir diferentes ângulos do contexto:

```python
# Query 1 — Intenção principal
query_neural_memory(question=f"<objetivo da sprint em 1 frase>", top=5)

# Query 2 — Segurança e restrições
query_neural_memory(question=f"<escopo> segurança permissões políticas", top=3)

# Query 3 — Erros e blockers anteriores similares
query_neural_memory(question=f"<blocker ou risco conhecido> falha erro", top=3)
```

### Passo 3 — Consolidar em bloco de contexto

Produza um bloco de **Contexto de Sprint** antes de iniciar qualquer execução:

```markdown
## Contexto de Sprint — [YYYY-MM-DD]

Sprint: <título>
Intenção: <objetivo em 1 frase>

### Decisões históricas relevantes

- [fonte] resumo da decisão (data)
- ...

### Restrições e políticas aplicáveis

- [fonte] resumo da política (seed)
- ...

### Riscos e bloqueadores históricos

- [fonte] resumo do erro ou blocker (data)
- ...

### Contradições detectadas

- `check_contradiction` status: CLEAR | WARNING | BLOCK

### Ação recomendada

- prosseguir com execução normal
- ou: aguardar revisão humana antes de continuar (se BLOCK)
```

### Passo 4 — Registrar na memória de sessão

Adicione este bloco no início do arquivo de memória de sessão da sprint atual (`docs/sessoes/sprints/sprint-N-*.md`), na seção `## Contexto recuperado`.

## FinOps de Contexto

Este prompt garante que o agente carrega apenas o contexto necessário (RAG cirúrgico) ao invés de ler `NEURAL-MEMORY.md` inteiro no prompt. Custo estimado:

| Operação                                          | Tokens estimados |
| ------------------------------------------------- | ---------------- |
| 3 queries × embedding                             | ~150 tokens      |
| Top-K chunks retornados                           | ~800 tokens      |
| Leitura completa NEURAL-MEMORY.md (modelo antigo) | ~2.000+ tokens   |

Economia por sessão: **~60-75% de tokens de contexto**.
