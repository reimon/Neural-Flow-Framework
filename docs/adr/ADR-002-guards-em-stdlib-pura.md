# ADR-002 — Guards executaveis em Python stdlib puro

## Status

Aceito (Sprint 1)

## Contexto

O principio n. 0 do framework diz que diretriz sem guard nao esta pronta. Para que os
guards sejam adotaveis por qualquer projeto — Node, Python, Go, Rust, ou repositorio so
de documentacao — eles nao podem exigir instalacao de dependencia nem ecossistema
especifico. Um guard que pede `pip install` antes de rodar deixa de ser adotado
justamente nos projetos que mais precisam dele.

## Decisao

Todos os guards sao Python 3.10+ usando exclusivamente a biblioteca padrao, orquestrados
por `scripts/nf_gate.py`. Helpers compartilhados vivem em `scripts/nf_guards.py` — os
validadores nao duplicam parsing.

Regra de comportamento: **ausencia de artefato e PASS (exit 0)**. Projeto sem sprints, sem
ADRs ou com templates ainda nao preenchidos passa direto. O guard trava quem usa o
protocolo errado, nao quem ainda nao o usa.

## Consequencias

Positivas:

- instalacao e copiar arquivos; nenhum gerenciador de pacotes envolvido
- roda igual no hook local e no CI
- adocao incremental: liga-se um protocolo por vez via `NF_GUARDS`

Trade-offs:

- exige Python disponivel na maquina e no runner (universal, mas nao zero)
- sem biblioteca de parsing markdown, o reconhecimento de secao e por regex e tolera
  menos variacao de formato

Fora de escopo nesta etapa:

- port dos guards para outra linguagem

## Evidencia (Neural-Flow)

- Sprint de origem: `Sprint 1`
- Guard associado: `python scripts/nf_gate.py` — a propria suite valida os guards
  (`tests/test_guards.py`, 17 casos nas duas direcoes)
- Artefatos: `scripts/nf_gate.py`, `scripts/nf_guards.py`, `tests/test_guards.py`
