# ADR-001 — Paginacao por cursor

## Status

Aceito (Sprint 1)

## Contexto

Offset degrada em tabelas grandes.

## Decisao

Adotar paginacao por cursor em todas as listagens publicas.

## Consequencias

Positivas:

- desempenho estavel independente da profundidade

Trade-offs:

- nao permite salto direto para pagina N

## Evidencia (Neural-Flow)

- Sprint de origem: `Sprint 1`
- Guard associado: teste de contrato em CI
