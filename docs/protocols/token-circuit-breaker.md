# Circuit Breaker de Tokens

## Missao

Monitorar consumo de tokens por sessao e por sprint para evitar degradacao operacional e estouro de custo.

## Regra inegociavel

Toda sprint deve declarar um orcamento de tokens e uma politica de bloqueio.

No modo de disrupcao, o Circuit Breaker atua como controle de infraestrutura ativo em tempo real.

## Parametros minimos

- Token budget da sprint
- Limite de alerta (ex.: 70 por cento)
- Limite de bloqueio (ex.: 100 por cento)
- Comportamento em anomalia
- Janela de observabilidade (ex.: 5 min)
- Limite de taxa de consumo por janela
- Limite de retries por tarefa
- Politica de rearme do disjuntor

## Modos de operacao

- Modo Monitoramento: alerta sem corte
- Modo Protecao Ativa: corte imediato ao atingir gatilho critico

## Gatilhos de disparo (trip)

- consumo acumulado >= 100 por cento do budget da sprint
- taxa de consumo por janela acima do limite definido
- loops de tentativa com crescimento anormal de tokens
- repeticao de prompts de alto custo sem progresso mensuravel

## Acao ao disparar

- cortar chamadas da API de IA imediatamente
- registrar evento de trip com timestamp e causa
- congelar execucao da tarefa afetada
- notificar responsavel e abrir acao de mitigacao

## Politica de rearme (reset)

So rearmar o disjuntor quando:

- houver analise da causa raiz
- existir acao corretiva registrada
- novo limite ou estrategia de tier estiver definido
- aprovador responsavel liberar retomada

## Politica de Tiers de Modelos

Para eficiencia financeira, aplicar roteamento por complexidade:

- Tier Leve: tarefas repetitivas e baixo risco
- Tier Intermediario: analise de impacto e consolidacao
- Tier Avancado: arquitetura e investigacao complexa

Regras:

- iniciar no menor tier viavel
- escalar tier somente com justificativa tecnica
- reduzir tier apos estabilizacao da tarefa

## Guard executavel

Este protocolo trava, nao sugere. Principio n. 0 do framework: **diretriz sem guard
nao esta pronta**.

```bash
python scripts/nf_gate.py budget          # so este protocolo
python scripts/nf_gate.py                  # todos os guards
```

Verifica: B1 budget declarado · B2 consumo registrado · B3 estouro exige mitigacao ou excecao formal · B4 sprint concluida sem consumo e FAIL.

Roda no **pre-commit** (sobre o que esta em stage, nao sobre a arvore de trabalho) e no
**CI** (autoritativo — hook local e opt-in por clone). Instalacao em
`templates/githooks/pre-commit` e `.github/workflows/neural-flow-gates.yml`.

## Criterio PASS

- Consumo dentro do budget
- Alertas registrados quando necessario
- Nao houve execucao apos bloqueio sem aprovacao
- Trips criticos resultaram em corte imediato quando em modo de protecao ativa

## Criterio FAIL

- Budget excedido sem interrupcao
- Ausencia de registro de consumo relevante
- Repeticao de prompts de alto custo sem mitigacao
- Trip critico sem corte da API em modo de protecao ativa

## Acao automatica em FAIL

- interromper fluxo de execucao
- reduzir contexto para modo minimo necessario
- abrir tarefa de correcao de eficiencia
- manter disjuntor em estado aberto ate aprovacao de rearme

## Controles recomendados

- leitura incremental de arquivos
- resumo por delta em vez de releitura integral
- proibicao de duplicacao de contexto no mesmo ciclo

## Evidencias esperadas

- orcamento declarado
- consumo observado na sprint
- decisoes de mitigacao aplicadas
- eventos de trip/rearme com causa e aprovador

## KPIs FinOps recomendados

- custo de tokens por sprint
- custo de tokens por item concluido valido
- throughput de itens concluidos validos
- produtividade liquida por token

Formula de referencia:

- produtividade liquida por token = itens concluidos validos / tokens consumidos
