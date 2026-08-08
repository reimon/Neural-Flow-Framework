# ADR-002 — Slots gerados sob demanda

## Status

Aceito (Sprint 2)

## Contexto

Materializar todos os slots futuros gera milhoes de linhas mortas e invalida a cada mudanca de agenda.

## Decisao

Calcular a disponibilidade sob demanda a partir das regras, materializando apenas o que foi reservado.

## Consequencias

Positivas:

- menor custo de escrita e de invalidacao

Trade-offs:

- leitura um pouco mais cara

## Evidencia (Neural-Flow)

- Sprint de origem: `Sprint 2`
- Guard associado: teste de propriedade sobre o gerador
