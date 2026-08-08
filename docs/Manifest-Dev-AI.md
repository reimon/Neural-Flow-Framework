# Manifesto Neural-Flow Framework

## 1. Proposito

Este manifesto define o Neural-Flow Framework como um Sistema de Controle Autonomo para engenharia assistida por IA.

O objetivo e substituir o modelo de documentacao manual reativa por um ciclo continuo e verificavel de:

- planejamento orientado a risco
- execucao assistida por agentes
- validacao por evidencias
- rastreabilidade operacional e tecnica
- aprendizagem institucional acumulativa

Neste modelo, documento nao e arquivo estatico. Documento e interface de controle do sistema.

## 2. Tese Central

Toda mudanca de software passa a ser tratada como um loop de controle.

O loop minimo e:

1. definir intencao
2. executar acao
3. medir resultado
4. comparar com criterio
5. corrigir desvio
6. consolidar memoria

Se nao houver medicao e criterio, nao ha conclusao. Ha apenas atividade.

## 3. Principios Inegociaveis

1. Governanca por evidencia
   Toda decisao relevante precisa de rastro verificavel.

2. Autonomia com limites explicitos
   Agente pode agir com liberdade operacional apenas dentro de politicas declaradas.

3. Falha segura por padrao
   Na duvida, reduz escopo, interrompe automacao e pede decisao humana.

4. Memoria como ativo de engenharia
   Aprendizado sem registro e regressao futura.

5. Padrao antes de velocidade
   Escala sem padrao gera caos acelerado.

6. Controle distribuido, verdade unica
   Times e agentes atuam localmente, mas seguem um conjunto canonico de regras.

## 4. Arquitetura do Sistema de Controle

O Neural-Flow opera em quatro planos sincronizados.

### 4.1 Plano de Politica (o que e permitido)

Define fronteiras, obrigacoes, niveis de risco e criterios minimos.

Artefato principal:

- este manifesto

### 4.2 Plano de Execucao (o que sera feito agora)

Traduz politica em entregas concretas por sprint, fluxo ou incidente.

Artefatos principais:

- sprints detalhadas
- checklist de portfolio
- planos de execucao do agente

### 4.3 Plano de Evidencia (como provar que funcionou)

Registra validacoes, resultados, commits, logs, artefatos e desvios.

Artefatos principais:

- secoes de evidencias
- secoes de validacao
- historico de commits e CI

### 4.4 Plano de Memoria (como evitar repeticao de erro)

Consolida decisoes, limites, padroes e licoes reutilizaveis.

Artefatos principais:

- MEMORY institucional
- memoria de sessao por sprint
- notas de excecao

### 4.5 Plano de Protocolos Nucleares (como operacionalizar controle)

Os controles nucleares do Neural-Flow sao implementados pelos protocolos:

- State Protocol
- Circuit Breaker de Tokens
- Vetor de Contexto do Repositorio
- Evidencia Sintetica
- Aegis Protocol

Referencia canonica de implementacao:

- `docs/protocols/README.md`
- `docs/protocols/state-protocol.md`
- `docs/protocols/token-circuit-breaker.md`
- `docs/protocols/context-vector.md`
- `docs/protocols/synthetic-evidence.md`
- `docs/protocols/aegis-security.md`
- `docs/protocols/auditoria-mensal-template.md`

Cadencia minima de auditoria:

- 1 auditoria mensal obrigatoria dos 5 protocolos nucleares.
- Auditoria extraordinaria em caso de incidente de seguranca, nao conformidade critica ou estouro recorrente de budget de tokens.

### 4.6 Documentacao como Contexto Funcional

No Neural-Flow, artefatos de governanca nao sao historico passivo; sao contexto operacional ativo.

Regra:

- toda decisao tecnica relevante deve referenciar contexto funcional vigente (sprint, delta, memoria e evidencias)
- documentacao de sprint e interface de controle da execucao
- ausencia de contexto funcional invalida inicio de execucao

### 4.7 FinOps de Tokens como Controle de Engenharia

Tokens sao custo variavel de engenharia e devem ser governados com a mesma disciplina de custo de infraestrutura.

Diretrizes obrigatorias:

- toda sprint declara token budget e consumo observado
- toda anomalia de consumo dispara mitigacao ou bloqueio
- toda equipe acompanha custo de tokens com metrica de entrega
- em modo de protecao ativa, trip critico do disjuntor corta a API de IA em tempo real

Regra de disrupcao:

- FinOps de tokens nao e apenas revisao periodica; e controle financeiro operacional em tempo real.

#### Politica de Tiers de Modelos

Uso orientado por complexidade para eficiencia financeira:

- tier leve para tarefas repetitivas e de baixo risco
- tier intermediario para analise e consolidacao
- tier avancado para problemas de alta complexidade

Escalonamento de tier deve ser justificado por complexidade, risco ou qualidade insuficiente.

## 5. Niveis de Autonomia Operacional

Cada mudanca deve declarar nivel de autonomia permitido.

- Nivel A0 - Manual Assistido
  Agente sugere; humano executa tudo.

- Nivel A1 - Execucao Supervisionada
  Agente executa tarefas de baixo risco com revisao humana antes de consolidar.

- Nivel A2 - Execucao Semi-Autonoma
  Agente executa fluxo completo em escopo pre-aprovado e apresenta evidencias para aceite.

- Nivel A3 - Execucao Autonoma Controlada
  Agente aplica mudancas dentro de politicas estritas, com gates obrigatorios e rollback preparado.

Regra:

- Qualquer alteracao em seguranca, dados sensiveis, infraestrutura, autenticacao, billing ou integracoes externas deve operar em A0 ou A1, salvo aprovacao explicita de excecao.

## 6. Protocolo Canonico de Mudanca

Toda mudanca deve seguir este protocolo, sem salto de etapa.

1. Contextualizar
   Definir objetivo, escopo incluido, fora do escopo, risco e criterio de pronto.

2. Planejar
   Registrar sprint ou plano com checklist numerado e dependencias.

3. Executar
   Aplicar mudanca tecnica conforme escopo autorizado.

4. Validar
   Executar testes, verificacoes e checagens operacionais aplicaveis.

5. Evidenciar
   Registrar o que foi feito, onde foi feito, como foi validado e qual resultado foi obtido.

6. Consolidar memoria
   Atualizar memoria institucional e memoria de sessao com o delta relevante.

7. Encerrar
   Somente marcar concluido quando criterios e evidencias estiverem completos.

## 7. Gates de Controle Obrigatorios

Nenhum fluxo e considerado concluido sem passar nos gates abaixo.

1. Gate de Escopo
   Escopo incluido e fora do escopo definidos.

2. Gate de Risco
   Riscos e impacto documentados.

3. Gate de Validacao
   Validacoes executadas com resultado registrado.

4. Gate de Evidencia
   Evidencia minima anexada por item concluido.

5. Gate de Memoria
   Aprendizado e mudancas de baseline registrados.

6. Gate de Integridade Historica
   Nao apagar historico concluido; apenas acrescentar deltas.

7. Gate de Seguranca
   Classificacao de dados aplicada e politica de zero segredo atendida.

8. Gate de FinOps em Tempo Real
   Circuit Breaker habilitado, gatilhos definidos e politica de corte/rearme validada.

## 8. Regras de Rastreabilidade

1. Toda acao concluida precisa de evidencia verificavel.
2. Toda evidencia deve apontar para artefato objetivo: arquivo, teste, log, commit, pipeline, screenshot ou deploy.
3. Toda sprint deve manter linha do tempo de atualizacoes por data em formato ISO `YYYY-MM-DD`.
4. Toda decisao relevante deve registrar contexto, alternativa descartada e criterio escolhido.
5. Toda pendencia deve possuir proxima acao clara.
6. Em escala (100+ devs), leitura padrao de execucao deve priorizar Snapshot Operacional + Delta da sprint ativa.
7. Reescrita narrativa integral deve ser excecao; atualizacao incremental por delta e o padrao oficial.

## 9. Regras de Memoria Operacional

### 9.1 Modelo de Memoria: Banco Vetorial RAG

O Neural-Flow opera com memoria institucional baseada em recuperacao semantica ativa (RAG — Retrieval-Augmented Generation) via Azure AI Search.

O agente **nao le arquivos de memoria inteiros no prompt**. Ele faz buscas semanticas cirurgicas que retornam apenas os chunks necessarios para a tarefa atual.

Vantagens sobre o modelo linear anterior:

- historico ilimitado (sem corte de 200-300 linhas)
- custo de contexto proporcional a relevancia (nao fixo)
- consciencia total de decisoes de meses atras sem inflar o prompt
- ingestao automatica a cada commit e push

Implementacao: protocolo `docs/protocols/neural-memory.md`

### 9.2 Seed Document

- arquivo canonico: `docs/NEURAL-MEMORY.md`
- funcao: seed do indice vetorial + registro de decisoes de alto nivel
- sem limite de linhas (busca semantica elimina o gargalo de leitura linear)
- nunca registrar segredo, credencial ou dado sensivel

### 9.3 Memoria de Sessao por Sprint

- pasta padrao: `docs/sessoes/sprints/`
- nome padrao: `sprint-<numero>-<escopo-curto>-YYYY-MM-DD.md`
- foco: delta da sessao, validacoes, commits e pendencias da proxima iteracao
- indexada automaticamente pelo pipeline de ingestao

### 9.4 Interface de Consulta

Consulta via MCP (modo primario — Copilot no VS Code):

```
query_neural_memory(question="<intencao da tarefa>", top=5)
check_contradiction(proposal="<proposta de mudanca>")
```

Consulta via CLI (fallback):

```bash
python scripts/search.py "<consulta em linguagem natural>"
```

### 9.5 Regra de Qualidade da Memoria

- registrar apenas o que orienta decisao futura
- evitar narrativa redundante — delta, nao reescrita
- nunca registrar segredo, credencial ou dado sensivel

### 9.6 FinOps de Memoria

| Operacao                                               | Custo estimado           |
| ------------------------------------------------------ | ------------------------ |
| 3 queries por sessao de sprint                         | USD 0,000045             |
| Reindex incremental (1 commit)                         | USD 0,000012             |
| Reindex completo (~200 chunks)                         | USD 0,001                |
| Leitura de MEMORY.md inteiro no prompt (modelo antigo) | ~2.000 tokens por sessao |

ROI positivo a partir de 2 sessoes de sprint por semana.

## 10. Politica de Evidencia Minima

Cada item marcado como concluido deve ter ao menos um destes comprovantes:

- arquivo alterado
- comando de validacao com resultado
- teste automatizado ou manual documentado
- commit associado
- log tecnico relevante
- link de PR, release ou deploy

Sem evidencia minima, o item volta para estado pendente.

## 11. Politica de Seguranca e Conformidade

1. Mudancas com impacto em auth, segredo, permissao, integracao externa, dados sensiveis ou infraestrutura exigem secao de seguranca.
2. Quando nao aplicavel, registrar explicitamente: `Nao se aplica`.
3. Toda excecao a politica deve registrar:

- motivo
- risco aceito
- aprovador
- prazo de revisao da excecao

## 12. Politica de Infraestrutura

Em infraestrutura, Terraform e abordagem padrao para provisionamento e ajustes, salvo decisao arquitetural formal em contrario.

Toda mudanca de infra deve registrar:

- modulo ou recurso alterado
- impacto esperado
- plano e aplicacao
- resultado pos-mudanca

## 13. Politica de Integridade Historica

1. Nao remover historico concluido.
2. Nao reescrever decisoes antigas para parecer linear.
3. Corrigir por adicao de delta, nao por apagamento de trilha.
4. Preservar contexto suficiente para auditoria tecnica.

## 14. Estrutura Obrigatoria de Sprint no Neural-Flow

Toda sprint deve respeitar esta ordem:

1. titulo
2. snapshot operacional
3. objetivo
4. escopo incluido
5. fora do escopo
6. entregaveis
7. checklist numerado
8. dependencias tecnologicas
9. notas de seguranca
10. delta desde a ultima atualizacao
11. riscos, blockers e ETA
12. evidencias de implementacao
13. commits executados
14. resumo das atividades
15. pendencias para a proxima sprint
16. referencia ao manifesto

## 15. Template Operacional de Sprint

```markdown
# Sprint N: Titulo

## Snapshot Operacional

- App/Escopo:
- Status: planejada | em andamento | bloqueada | concluida | cancelada
- Data de inicio: YYYY-MM-DD
- Data planejada de conclusao: YYYY-MM-DD
- Data real de conclusao: a preencher
- Ultima atualizacao: YYYY-MM-DD
- Nivel de autonomia: A0 | A1 | A2 | A3
- Blocker principal:
- Proxima acao:

## Controle de Protocolos Nucleares

- State Protocol: PASS | FAIL | EXCEPTION
- Circuit Breaker: PASS | FAIL | EXCEPTION
- Context Vector: PASS | FAIL | EXCEPTION
- Evidencia Sintetica: PASS | FAIL | EXCEPTION
- Aegis Protocol: PASS | FAIL | EXCEPTION
- Token budget da sprint: <valor>
- Consumo observado: <valor>

## Objetivo

## Escopo incluido

## Fora do escopo

## Entregaveis

- [ ] E1
- [ ] E2

## Checklist de Acoes

- [ ] 1.1 Acao
  - Arquivo(s):
  - Validacao:
  - Evidencia:

## Dependencias Tecnologicas

## Notas de Seguranca

## Delta desde a ultima atualizacao

- YYYY-MM-DD:

## Riscos / Blockers / ETA

## Evidencias de Implementacao

## Commits Executados

## Resumo das Atividades

| Acao | O que foi feito | Arquivos alterados |
| ---- | --------------- | ------------------ |

## Pendencias para a Proxima Sprint

## Regras

- Seguir este manifesto.
```

## 16. Metricas de Saude do Sistema

O Neural-Flow deve monitorar, no minimo:

- taxa de itens concluidos com evidencia valida
- lead time por sprint
- taxa de retrabalho por regressao
- volume de pendencias carregadas
- idade media de blockers
- cobertura de memoria (sprints com memoria atualizada)
- custo de tokens por sprint
- custo de tokens por item concluido valido
- produtividade liquida por token

Formula de referencia para produtividade liquida:

- produtividade liquida por token = itens concluidos validos / tokens consumidos

Se metrica piora por 2 ciclos seguidos, abrir sprint de correcao de processo.

## 17. Condicoes de Conclusao Real

Uma sprint ou mudanca so pode ser marcada como concluida quando:

1. todos os gates obrigatorios foram atendidos
2. evidencias minimas foram registradas
3. memoria institucional e memoria de sessao foram atualizadas
4. pendencias residuais foram explicitadas com proxima acao

Conclusao sem esses criterios e considerada fechamento administrativo, nao conclusao tecnica.

## 18. Regra de Conflito

Se houver conflito entre velocidade e controle, prevalece o controle.

Se houver conflito entre opiniao e evidencia, prevalece a evidencia.

Se houver conflito entre automacao e seguranca, prevalece a seguranca.

## 19. Escopo de Aplicacao

Este manifesto se aplica a todo ciclo de engenharia assistida por IA no repositorio, incluindo:

- planejamento de sprints
- execucao tecnica por agentes e humanos
- atualizacao de memoria institucional
- registro de evidencias e validacoes
- governanca de mudancas em aplicacao e infraestrutura

## 20. Clausula de Evolucao

O manifesto e vivo.

Toda melhoria de governanca deve:

1. registrar problema observado
2. registrar regra proposta
3. registrar impacto esperado
4. registrar data de adocao

Sem clausula de evolucao, governanca vira dogma. Com evolucao controlada, governanca vira vantagem competitiva.
