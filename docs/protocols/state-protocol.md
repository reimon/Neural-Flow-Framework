# State Protocol

## Missao

Garantir que nenhuma execucao tecnica comece sem estado de sprint validado.

## Regra inegociavel

Nenhuma mudanca inicia sem um arquivo de sprint com snapshot operacional completo e status valido.

## Campos obrigatorios de validacao de estado

- App/Escopo
- Status
- Data de inicio
- Data planejada de conclusao
- Ultima atualizacao
- Nivel de autonomia (A0-A3)
- Blocker principal
- Proxima acao

## Guard executavel

Este protocolo trava, nao sugere. Principio n. 0 do framework: **diretriz sem guard
nao esta pronta**.

```bash
python scripts/nf_gate.py sprint          # so este protocolo
python scripts/nf_gate.py                  # todos os guards
```

Verifica: S1 snapshot completo · S2 status sem ambiguidade · S3 autonomia valida · S4 escopo sensivel em A0/A1 · S5 fronteira de escopo · S6 checklist numerado e coerente com o status.

Roda no **pre-commit** (sobre o que esta em stage, nao sobre a arvore de trabalho) e no
**CI** (autoritativo — hook local e opt-in por clone). Instalacao em
`templates/githooks/pre-commit` e `.github/workflows/neural-flow-gates.yml`.

## Criterio PASS

- Sprint existe e foi atualizada na data da sessao
- Escopo incluido e fora do escopo estao preenchidos
- Checklist numerado existe
- Criterio de pronto esta explicito

## Criterio FAIL

- Mudanca tecnica iniciada sem sprint
- Sprint sem snapshot operacional
- Sprint com status ambiguo

## Acao automatica em FAIL

- bloquear execucao
- registrar evento no delta da sprint
- solicitar regularizacao de estado antes de continuar

## Evidencias esperadas

- referencia ao arquivo de sprint
- data da ultima validacao de estado
- identificador da sessao responsavel
