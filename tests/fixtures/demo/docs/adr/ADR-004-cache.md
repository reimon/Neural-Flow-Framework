# ADR-004 — Cache compartilhado com invalidacao por evento

## Status

Aceito (Sprint 2)

## Contexto

Com mais de uma instancia, o cache local divergia e mostrava horario ja reservado.

## Decisao

Cache compartilhado, invalidado pelo evento de reserva em vez de TTL.

## Consequencias

Positivas:

- menor custo de escrita e de invalidacao

Trade-offs:

- leitura um pouco mais cara

## Evidencia (Neural-Flow)

- Sprint de origem: `Sprint 2`
- Guard associado: teste de isolamento entre instancias
