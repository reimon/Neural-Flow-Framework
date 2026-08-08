# ADR-001 — PostgreSQL em vez de banco de documentos

## Status

Aceito (Sprint 1)

## Contexto

Agenda e um problema relacional: conflito de horario e uma restricao de integridade, nao uma consulta.

## Decisao

Adotar PostgreSQL com constraint de exclusao por intervalo (`EXCLUDE USING gist`).

## Consequencias

Positivas:

- integridade garantida pelo banco, nao pela aplicacao

Trade-offs:

- depende de extensao do PostgreSQL

## Evidencia (Neural-Flow)

- Sprint de origem: `Sprint 1`
- Guard associado: constraint no schema + teste de integracao
