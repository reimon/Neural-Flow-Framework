# ADR-012 — Validacao local sem executor de acoes

## Status

Aceito (Sprint 10)

Supera ADR-006, ADR-007, ADR-008 e ADR-011 no contrato de execucao.

## Decisao

Retirar o Action Gateway, sua politica e seu guard. A validacao do projeto usa
os testes e `scripts/nf_gate.py`, incluindo o hook local sobre os arquivos em
stage. Commit e push continuam sujeitos a autorizacao explicita.

## Evidencia (Neural-Flow)

- Sprint de origem: [Sprint 10](../sprints/sprint-10-retirar-action-gateway.md).
- Guard associado: `python3 scripts/nf_gate.py`.

## Referencias historicas

- `ADR-006-gateway-de-acoes.md` [docs/protocols/action-gateway.md](https://github.com/reimon/Neural-Flow-Framework/blob/c41cedd44c22ef023e6b243100100a81be705141/docs/protocols/action-gateway.md)
- `ADR-006-gateway-de-acoes.md` [scripts/nf_action_gateway.py](https://github.com/reimon/Neural-Flow-Framework/blob/c41cedd44c22ef023e6b243100100a81be705141/scripts/nf_action_gateway.py)
- `ADR-006-gateway-de-acoes.md` [scripts/validate_action_policy.py](https://github.com/reimon/Neural-Flow-Framework/blob/c41cedd44c22ef023e6b243100100a81be705141/scripts/validate_action_policy.py)
- `ADR-006-gateway-de-acoes.md` [.neural-flow/action-policy.json](https://github.com/reimon/Neural-Flow-Framework/blob/c41cedd44c22ef023e6b243100100a81be705141/.neural-flow/action-policy.json)
- `ADR-007-sandbox-do-gateway.md` [docs/protocols/action-gateway.md](https://github.com/reimon/Neural-Flow-Framework/blob/c41cedd44c22ef023e6b243100100a81be705141/docs/protocols/action-gateway.md)
- `ADR-007-sandbox-do-gateway.md` [scripts/nf_action_gateway.py](https://github.com/reimon/Neural-Flow-Framework/blob/c41cedd44c22ef023e6b243100100a81be705141/scripts/nf_action_gateway.py)
- `ADR-007-sandbox-do-gateway.md` [scripts/validate_action_policy.py](https://github.com/reimon/Neural-Flow-Framework/blob/c41cedd44c22ef023e6b243100100a81be705141/scripts/validate_action_policy.py)
- `ADR-007-sandbox-do-gateway.md` [.neural-flow/action-policy.json](https://github.com/reimon/Neural-Flow-Framework/blob/c41cedd44c22ef023e6b243100100a81be705141/.neural-flow/action-policy.json)
- `ADR-008-adaptadores-de-sandbox-validados.md` [scripts/nf_action_gateway.py](https://github.com/reimon/Neural-Flow-Framework/blob/c41cedd44c22ef023e6b243100100a81be705141/scripts/nf_action_gateway.py)
- `ADR-008-adaptadores-de-sandbox-validados.md` [docs/protocols/action-gateway.md](https://github.com/reimon/Neural-Flow-Framework/blob/c41cedd44c22ef023e6b243100100a81be705141/docs/protocols/action-gateway.md)
- `ADR-006-gateway-de-acoes.md` [tests/test_action_gateway.py](https://github.com/reimon/Neural-Flow-Framework/blob/c41cedd44c22ef023e6b243100100a81be705141/tests/test_action_gateway.py)
- `ADR-007-sandbox-do-gateway.md` [tests/test_action_gateway.py](https://github.com/reimon/Neural-Flow-Framework/blob/c41cedd44c22ef023e6b243100100a81be705141/tests/test_action_gateway.py)
- `ADR-008-adaptadores-de-sandbox-validados.md` [tests/test_action_gateway.py](https://github.com/reimon/Neural-Flow-Framework/blob/c41cedd44c22ef023e6b243100100a81be705141/tests/test_action_gateway.py)
