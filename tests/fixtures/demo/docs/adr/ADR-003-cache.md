# ADR-003 — Cache local de disponibilidade

## Status

Superado por ADR-004

## Contexto

Primeira tentativa de reduzir latencia mantinha cache em memoria do processo.

## Decisao

Cache em memoria por processo, com TTL de 60s.

## Consequencias

Positivas:

- menor custo de escrita e de invalidacao

Trade-offs:

- leitura um pouco mais cara

## Evidencia (Neural-Flow)

- Sprint de origem: `Sprint 2`
- Guard associado: aspiracional
