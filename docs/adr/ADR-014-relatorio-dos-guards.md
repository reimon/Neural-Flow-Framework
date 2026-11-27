# ADR-014 - Evidencia compartilhada dos guards

## Status

Aceito (Sprint 12)

## Contexto

O gate contabilizava como conforme um guard sem artefato. O painel mantinha
um registro proprio e omitia o guard de portas dos agentes.

## Decisao

Gerar o relatorio de execucao no gate. Cada guard registra estado, arquivos,
achados e motivo. Terminal, painel e resumo do CI apresentam esses resultados.
O painel pode abrir um relatorio salvo, inclusive o de uma execucao reprovada.

## Alternativas consideradas

Manter contadores independentes no painel exigiria sincronizar o registro e
as regras de classificacao em cada alteracao.

## Consequencias

O JSON v1 passa a ser uma interface publica. O projeto ainda pode iniciar sem
artefatos. Comandos locais de validadores proprios participam da execucao
explicita do gate.

## Evidencia

- Data: 2026-11-27
- Autores: Codex
- Sprint de origem: Sprint 12
- Guard associado: `python3 scripts/nf_gate.py` e regressao em `tests/test_evidencia.py`.
