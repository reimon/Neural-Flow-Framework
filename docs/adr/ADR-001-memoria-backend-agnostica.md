# ADR-001 — Protocolo Neural-Memory backend-agnostico

## Status

Aceito (Sprint 1)

## Contexto

A primeira versao do protocolo Neural-Memory prescrevia Azure AI Search + Azure OpenAI
como implementacao unica. Um projeto irmao
chegou ao mesmo resultado com PostgreSQL + pgvector dentro de um monolito Node ja existente,
eliminando um servico gerenciado, uma linguagem extra e o custo fixo correspondente.
Prescrever tecnologia num framework de governanca acopla o adotante a uma nuvem que ele
pode nao usar.

## Decisao

O protocolo define **contratos**, nao tecnologia: indexacao com metadados minimos, busca
hibrida, MCP tools `query_neural_memory` e `check_contradiction`, reindex incremental e
indice sempre reconstruivel a partir do git.

A stack Azure deste repositorio (`scripts/ingest.py`, `scripts/search.py`,
`mcp/neural-memory-server/`) permanece como **implementacao de referencia**, nao como
requisito. Projeto que ja possui PostgreSQL deve preferir pgvector.

## Consequencias

Positivas:

- adocao possivel em qualquer stack, sem provisionar nuvem
- custo fixo do servico de busca cai a zero quando o projeto ja tem banco
- o indice deixa de ser fonte primaria em qualquer implementacao

Trade-offs:

- o framework passa a manter contrato + uma referencia, e nao um produto unico
- comparabilidade entre adotantes fica menor (backends diferentes, latencias diferentes)

Fora de escopo nesta etapa:

- reescrever a implementacao de referencia em Node/pgvector

## Evidencia (Neural-Flow)

- Sprint de origem: `Sprint 1`
- Guard associado: aspiracional — uso efetivo do MCP nao e verificavel automaticamente;
  o reindex e coberto por `.github/workflows/reindex.yml`
- Artefatos: `docs/protocols/neural-memory.md`
