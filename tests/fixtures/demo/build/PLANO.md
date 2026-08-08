# Plano de construcao — AgendaMed

## Definicao de Pronto

1. `docker compose up -d` sobe o Postgres.
2. `make verificar` fica verde.

## Fase E — Esqueleto que roda

- [x] **E1 — Scaffold do projeto.**
- [x] **E2 — Health check com versao e status do banco.**
- [x] **E3 — Migrations com Alembic.**
- [ ] **E4 — Motor de slots.**
- [ ] **E5 — API de disponibilidade.**
- [BLOQUEADO: aguarda decisao de fuso horario] **E6 — Agendamento recorrente.**
