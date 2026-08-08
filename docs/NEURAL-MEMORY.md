---
seed: true
description: "Documento semente da memória institucional do Neural-Flow Framework. É indexado no banco vetorial (Azure AI Search) e serve como âncora de políticas e estado operacional. Não possui limite de linhas — busca semântica cirúrgica substitui a leitura linear."
---

# NEURAL-MEMORY — Memória Institucional Neural-Flow

> Este arquivo é o **seed document** do banco vetorial neural-memory.
> Ele não é lido inteiro no prompt — é indexado e consultado via busca semântica.
> Edite livremente. O pipeline de ingestão (`scripts/ingest.py`) reindexará automaticamente.

## Snapshot Operacional

- Projeto: Neural-Flow Framework
- Foco atual: implementação do protocolo Neural-Memory + banco vetorial RAG
- Stack principal: Python, Azure AI Search, Azure OpenAI, Terraform, MCP
- Manifesto: `docs/Manifest-Dev-AI.md`
- Última atualização: 2026-03-23

## Regras Operacionais Estáveis

- Sprint-primeiro: nenhuma mudança inicia fora de sprint definida
- Agente não lê `NEURAL-MEMORY.md` inteiro no prompt — usa `query_neural_memory` via MCP
- Nunca registrar segredos, credenciais ou dados sensíveis neste arquivo (Aegis Protocol)
- Terraform é a abordagem padrão para infraestrutura
- Histórico nunca é apagado — apenas acrescenta-se deltas (Política de Integridade Histórica)
- Toda conclusão exige evidência mínima verificável (Política de Evidência Mínima)

## Comandos Essenciais

```bash
# Busca semântica na memória (CLI)
python scripts/search.py "<consulta em linguagem natural>"

# Reindexar tudo
python scripts/ingest.py

# Reindexar apenas mudanças do último commit
python scripts/ingest.py --changed-only

# Dry-run: ver o que seria indexado sem subir
python scripts/ingest.py --dry-run

# Instalar git hook de ingestão automática
bash scripts/setup-hooks.sh

# Provisionamento de infra (Azure AI Search + OpenAI)
cd infra/terraform && terraform init && terraform plan && terraform apply
```

## Estado Atual por Domínio

### Protocolo Neural-Memory (Sprint Atual)

- Status: `em andamento`
- Últimas alterações: implementação completa — Terraform, scripts, MCP server, CI, protocolos
- Arquivos principais:
  - `infra/terraform/main.tf` — Azure AI Search + OpenAI resources
  - `scripts/ingest.py` — pipeline de ingestão com chunking, embeddings e upload
  - `scripts/search.py` — CLI de busca semântica
  - `mcp/neural-memory-server/server.py` — MCP server com `query_neural_memory` e `check_contradiction`
  - `.vscode/mcp.json` — registro do MCP server no VS Code Copilot
  - `.github/prompts/context-retrieval.prompt.md` — Neural-Prompt pré-task
  - `.github/prompts/sprint-intent.prompt.md` — Neural-Prompt de intent extractor
  - `.github/workflows/reindex.yml` — CI auto-reindex
  - `docs/protocols/neural-memory.md` — 6º protocolo nuclear

## Decisões Técnicas Registradas

### 2026-03-23 — Adoção de Azure AI Search como banco vetorial

- **Decisão**: Azure AI Search (hybrid keyword + vector) substituindo leitura linear de MEMORY.md
- **Alternativas descartadas**: LanceDB local (sem suporte MCP nativo), Qdrant Cloud (custo adicional), Pinecone (fora do ecossistema Azure já adotado)
- **Critério de escolha**: integração nativa com Azure OpenAI, Terraform suportado, hybrid search sem custo extra de servidor
- **Impacto esperado**: eliminação do limite de 200-300 linhas, ROI positivo após 2 sessões/semana

### 2026-03-23 — text-embedding-3-small como modelo de embedding

- **Decisão**: usar `text-embedding-3-small` (1536 dims) via Azure OpenAI
- **Alternativa cogitada**: `text-embedding-ada-002` (1536 dims, mais disponível, mais caro)
- **Critério**: menor custo por token; maior disponibilidade em East US / Sweden Central
- **Risco aceito**: menor disponibilidade de quota em regiões novas; mitigação: usar East US

### 2026-03-23 — MCP como interface primária de consulta

- **Decisão**: GitHub Copilot acessa a memória via MCP tool, não por leitura de arquivo
- **Impacto**: agente formula queries em linguagem natural antes de agir; chunks cirúrgicos substituem leitura de arquivo completo
- **Gate de adoção**: Copilot deve chamar `query_neural_memory` antes de tarefas A2/A3

## Protocolo de Atualização deste Arquivo

1. Edite livremente — sem limite de linhas
2. Execute `python scripts/ingest.py --changed-only` (ou aguarde post-commit hook)
3. O conteúdo novo será indexado automaticamente e disponível nas próximas buscas

## Histórico de Sprints

### Sprint Atual — Neural-Memory + Banco Vetorial RAG

- Data: 2026-03-23
- Objetivo: substituir modelo de memória linear por RAG com Azure AI Search
- Status: em andamento
- Arquivos alterados: ver "Estado Atual" acima

> Sprints anteriores serão registradas abaixo à medida que forem concluídas.
> Não há limite de histórico neste arquivo — busca semântica torna o tamanho irrelevante para custo de contexto.
