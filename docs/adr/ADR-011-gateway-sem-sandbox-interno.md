# ADR-011 — Gateway de acoes sem sandbox interno

## Status

Aceito (Sprint 9)

Supera ADR-007 e ADR-008 no contrato de isolamento.

## Contexto

A politica obrigatoria bloqueia ate testes e guards, pois nenhum adaptador foi validado.
O objetivo do framework e oferecer governanca padronizada para equipes adotantes.

## Decisao

- Remover a integracao de sandbox do gateway. O ambiente de execucao aplica o
  isolamento de arquivos, processos e rede quando exigido pela equipe.
- A politica v2 autoriza apenas o comando completo. O gateway valida sprint, item,
  prazo e risco; acoes sensiveis e irreversiveis exigem confirmacao TTY em A0/A1.
- A politica v1 exige migracao explicita antes de executar ou planejar uma acao.

## Evidencia (Neural-Flow)

- Sprint de origem: [Sprint 9](../sprints/sprint-09-remover-sandbox-do-gateway.md).
- Guard associado: `python3 scripts/nf_gate.py action context`.

## Referencias historicas

- `ADR-007-sandbox-do-gateway.md` [scripts/nf_sandbox.py](https://github.com/reimon/Neural-Flow-Framework/blob/20f61ba419639b60bd627159bdd5691e20a2cb03/scripts/nf_sandbox.py)
- `ADR-008-adaptadores-de-sandbox-validados.md` [scripts/nf_sandbox.py](https://github.com/reimon/Neural-Flow-Framework/blob/20f61ba419639b60bd627159bdd5691e20a2cb03/scripts/nf_sandbox.py)
