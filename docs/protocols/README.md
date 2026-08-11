# Protocolos Operacionais Neural-Flow

Este diretorio contem a implementacao operacional dos 10 protocolos nucleares do framework.

## Objetivo

Transformar principios de governanca em controles executaveis, auditaveis e repetiveis.

Os 10 protocolos nucleares governam o **trabalho**; `agent-entrypoints.md` governa a
**porta**: de nada adianta a regra existir se o agente que abriu o projeto nunca chegou
ate ela.

## Matriz de Protocolos

| Protocolo           | Objetivo                                       | Gate primario     | Falha critica                       |
| ------------------- | ---------------------------------------------- | ----------------- | ----------------------------------- |
| State Protocol      | Garantir intencao valida antes de executar     | Gate de Escopo    | Execucao sem sprint validada        |
| Circuit Breaker     | Proteger consumo de tokens e custo operacional | Gate de Risco     | Orcamento excedido sem bloqueio     |
| Vetor de Contexto   | Reduzir perda de contexto e inflacao de tokens | Gate de Memoria   | Decisao sem contexto minimo         |
| Evidencia Sintetica | Exigir prova tecnica de conclusao              | Gate de Evidencia | Item concluido sem prova            |
| Aegis Protocol      | Evitar exposicao de dados sensiveis e segredos | Gate de Seguranca | Segredo em prompt/artefato          |
| Neural-Memory       | Substituir leitura linear por RAG vetorial     | Gate de Memoria   | Agente le arquivo inteiro no prompt |
| ADR Governance      | Registrar decisao arquitetural auditavel       | Gate de Contexto  | Decisao estrutural sem ADR          |
| Spec-First          | Especificar e passar em gate antes de codificar | Gate de Escopo   | Codigo sem spec; dado inventado     |
| Loop Autonomo       | Execucao prolongada com estado em disco        | Gate de Evidencia | Estado so na conversa; item pronto sem verde |
| Calibracao          | Tornar grau de certeza explicito e auditavel   | Gate de Confianca | Inferencia afirmada como verificacao |
| Portas de Entrada   | Levar toda ferramenta de IA a mesma diretriz   | Gate de Contexto  | Agente operando sem ter lido `AGENTS.md` |

## Ordem de aplicacao recomendada

1. state-protocol.md
2. token-circuit-breaker.md
3. context-vector.md
4. synthetic-evidence.md
5. aegis-security.md
6. neural-memory.md
7. adr-governance.md
8. spec-first.md
9. autonomous-loop.md
10. calibration.md
11. agent-entrypoints.md

### Ordem de execucao num projeto novo (a ordem importa mais que a ferramenta)

| Etapa | Artefato | Gate |
| --- | --- | --- |
| Especificar | specs no padrao obrigatorio | validador no pre-commit (spec-first) |
| Inventariar | mapa de cobertura ativo x modulo | decisao registrada, adocao adiada |
| Indexar | grafo de conhecimento + wiki + relatorio | consulta antes de leitura (context-vector) |
| Planejar | `build/PLANO.md` com criterio de aceite por item | Definicao de Pronto explicita |
| Construir | loop de uma iteracao por item | comando de verificacao verde |
| Registrar | diario, divergencias, memoria, indice atualizado | fim de agente arruma a casa |

Especificar antes de inventariar produz reuso ruim. Indexar antes de especificar indexa o
vazio. Construir antes de planejar produz codigo que ninguem consegue verificar — e num
projeto assistido por IA, codigo nao verificavel e o unico tipo que se produz rapido demais
para ser revisado.

## Regra de auditoria

Uma sprint e considerada aderente quando todos os 10 protocolos estao em estado `PASS` ou possuem excecao formal registrada com data e aprovador.

## Template oficial de auditoria mensal

- Modelo: `docs/protocols/auditoria-mensal-template.md`
- Local recomendado para execucoes: `docs/protocols/auditorias/`
- Padrao de nome: `YYYY-MM-auditoria.md`

## Checklist de Auditoria Mensal

Preencher este checklist 1 vez por mes para validar aderencia continua.

### Metadados da auditoria

- Mes de referencia: `YYYY-MM`
- Responsavel pela auditoria: `a preencher`
- Escopo auditado: `sprints do periodo`
- Data da revisao: `YYYY-MM-DD`

### 1. State Protocol

- [ ] Toda execucao tecnica do periodo possui sprint valida antes do inicio.
- [ ] Snapshot operacional estava completo nas sprints auditadas.
- [ ] Status de sprint foi atualizado sem ambiguidade.

Evidencia:

- arquivos de sprint auditados e datas.

### 2. Circuit Breaker de Tokens

- [ ] Toda sprint auditada declarou token budget.
- [ ] Houve registro de consumo observado.
- [ ] Excesso de budget gerou bloqueio, mitigacao ou excecao formal.

Evidencia:

- budget, consumo e acoes de mitigacao por sprint.

### 3. Vetor de Contexto do Repositorio

- [ ] Decisoes relevantes citam fontes de contexto.
- [ ] Nao houve execucao fora de escopo por falta de contexto.
- [ ] Delta de contexto foi registrado quando necessario.

Evidencia:

- referencias documentais usadas nas decisoes.

### 4. Evidencia Sintetica

- [ ] Itens concluidos possuem evidencia tecnica verificavel.
- [ ] Fechamento de sprint nao ocorreu com itens sem prova.
- [ ] Evidencias apontam para artefatos reais.

Evidencia:

- tabela acao x evidencia e artefatos associados.

### 5. Aegis Protocol

- [ ] Nao houve segredo em prompt, memoria ou artefato operacional.
- [ ] Dados sensiveis foram mascarados quando aplicavel.
- [ ] Sprints sensiveis contem notas de seguranca atualizadas.

Evidencia:

- validacao de seguranca e registros de contencao quando aplicavel.

### Resultado consolidado

- Aprovado: `SIM | NAO`
- Protocolos em nao conformidade: `nenhum | listar`
- Plano de correcao: `a preencher`
- Prazo de regularizacao: `YYYY-MM-DD`
- Revisor final: `a preencher`

## Cadencia recomendada

- Executar 1 auditoria mensal obrigatoria.
- Em meses com incidentes de seguranca ou estouro de budget, executar auditoria extraordinaria.

### 6. Neural-Memory

- [ ] Toda tarefa relevante do periodo precedida de chamada a `query_neural_memory`.
- [ ] Nenhuma proposta executada apos `check_contradiction` retornar `BLOCK` sem aprovacao humana.
- [ ] Index neural-memory atualizado (CI reindex executou sem falha).
- [ ] `NEURAL-MEMORY.md` reflete estado operacional atual.

Evidencia:

- logs do CI reindex e registro de consultas MCP realizadas no periodo.

### 7. ADR Governance

- [ ] Toda decisao arquitetural do periodo possui ADR numerado com status e sprint de origem.
- [ ] Nenhum ADR aceito foi editado (mudancas via novo ADR de superacao).
- [ ] ADRs impositivos possuem guard automatizado ou declaracao de guard aspiracional.

Evidencia:

- lista de ADRs criados/superados no periodo e guards associados.

### 8. Spec-First

- [ ] Todo modulo com codigo possui spec completa aprovada antes do codigo.
- [ ] Validador de spec verde no pre-commit, validando o stage e descobrindo modulos pelo diretorio.
- [ ] Nenhum dado de dominio regulado foi inventado onde a base de referencia nao tinha.
- [ ] Planos do periodo declaram secao "Fora do escopo" nominalmente.

Evidencia:

- saida do validador e mapa de cobertura de reuso do periodo.

### 9. Loop Autonomo

- [ ] Estado do loop integralmente em disco (plano, diario, divergencias, protocolo).
- [ ] Nenhum item marcado pronto sem verificacao verde; nenhum teste afrouxado/desabilitado.
- [ ] Divergencias registradas em vez de spec editada pelo executor.
- [ ] Commits escopados (sem `git add -A`, sem `--no-verify`).

Evidencia:

- `build/DIARIO.md`, `build/DIVERGENCIAS.md` e commits do periodo.

### 10. Calibracao e Incerteza

- [ ] Conclusoes tecnicas do periodo declaram nivel de confianca e classe de evidencia.
- [ ] Nenhum item foi fechado com confianca `BAIXA`.
- [ ] Escada de verificacao percorrida antes de registrar lacuna (fonte buscada, execucao tentada).
- [ ] Consulta fraca ao indice gerou reformulacao, nao escalada direta para varredura.
- [ ] Toda combinacao `BAIXA` + acao irreversivel parou para aprovacao humana.

Evidencia:

- registros de confianca nos itens concluidos e divergencias abertas por lacuna de contexto.

## Mapa: comportamento esperado do agente x protocolo que o garante

Checklist de aderencia comportamental — o que muda na pratica depois de adotar o framework.

| O agente... | Protocolo que garante | Mecanismo concreto |
| --- | --- | --- |
| Planeja antes de agir | State Protocol + Loop Autonomo | Sprint validada / `PLANO.md` com Definicao de Pronto e ordem por dependencia |
| Possui indice | Neural-Memory + Vetor de Contexto | RAG backend-agnostico + grafo de conhecimento versionado |
| Sabe escolher ferramentas | Vetor de Contexto | Tabela classe de pergunta x ferramenta; escalada da mais barata |
| Le apenas o necessario | Vetor de Contexto + Circuit Breaker | Indice antes de leitura, gestao por deltas, teto de 50% de contexto |
| Valida antes de responder | Evidencia Sintetica + Calibracao | Verde e unica condicao; escada de verificacao proporcional |
| Mede confianca | Calibracao | Nivel derivado da classe de evidencia, declarado em toda conclusao |
| Sabe quando perguntar de novo | Calibracao | Gatilho de reconsulta (incerteza) + gatilho de irreversibilidade (risco) |
| Aprende com execucoes anteriores | Neural-Memory + Loop Autonomo | Solutions Log datado, divergencias, reindex incremental, fim de agente arruma a casa |
| Nao inventa dado de dominio | Spec-First | Dado ausente bloqueia o item; nunca vira valor plausivel |
| Nao contradiz decisao vigente | ADR Governance + Neural-Memory | ADR imutavel + `check_contradiction` com BLOCK |
| Nao expoe segredo nem destroi producao | Aegis + AI_SAFETY | Proibicoes absolutas e acoes que exigem confirmacao |

## Guards executaveis por protocolo — estado honesto

Diretriz sem guard depende de qual modelo leu o que. Guard aspiracional deve ser declarado
como tal, **nunca apresentado como se travasse algo**.

Rodar tudo: `python scripts/nf_gate.py` · listar: `python scripts/nf_gate.py --list`

| Protocolo | Guard | Codigos | Situacao |
| --- | --- | --- | --- |
| State Protocol | `nf_gate.py sprint` | S1-S6 | Executavel — pre-commit + CI |
| Circuit Breaker | `nf_gate.py budget` | B1-B4 | Executavel — pre-commit + CI |
| Vetor de Contexto | `nf_gate.py context` | V1-V3 | Executavel — pre-commit + CI |
| ADR Governance | `nf_gate.py adr` | A1-A6 | Executavel — pre-commit + CI |
| Spec-First | `nf_gate.py spec` | P1-P4 | Executavel — pre-commit + CI |
| Calibracao | `nf_gate.py calibration` | C1-C6 | Executavel — pre-commit + CI |
| Evidencia Sintetica | `smoke-gate audit` + Action `fail-on: critical` | — | Executavel — PR + CI |
| Loop Autonomo | Coberto por C1-C3 (coerencia plano x diario) | — | Parcial |
| Neural-Memory | Reindex no CI (`.github/workflows/reindex.yml`) | — | Parcial — uso efetivo do MCP nao e verificavel automaticamente |
| Aegis | Proibicoes em `AI_SAFETY.md` + scanner de segredo do projeto | — | Parcial — depende de scanner que o projeto adiciona |

O que **nao** e automatizavel e continua na auditoria mensal: se o agente de fato consultou
o indice antes de decidir, se a leitura foi minima, se o tier de modelo escolhido era o mais
barato viavel. Guard cobre artefato; intencao ainda se audita.
