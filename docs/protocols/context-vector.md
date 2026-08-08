# Vetor de Contexto do Repositorio

## Missao

Substituir memoria linear por contexto recuperavel orientado a relevancia e rastreabilidade.

## Regra inegociavel

Toda decisao tecnica relevante deve estar ancorada em pelo menos uma fonte de contexto verificavel.

## Fontes canonicas de contexto

Consulta via banco vetorial Azure AI Search (busca semântica RAG — protocolo Neural-Memory):

1. **Azure AI Search index `neural-memory`** — fonte primaria de recuperacao de contexto (substituiu leitura linear)
2. Manifesto (`docs/Manifest-Dev-AI.md`) — seed document indexed
3. NEURAL-MEMORY institucional (`docs/NEURAL-MEMORY.md`) — seed document indexed
4. Sprint ativa — indexada automaticamente
5. Historico de commits — indexado via git log
6. Evidencias tecnicas e logs de sessao — indexados de `docs/sessoes/`

Interface de consulta: MCP tool `query_neural_memory(question, top)` via `.vscode/mcp.json`

## Indice antes de leitura (regra de entrada)

**Pergunta sobre o projeto comeca no indice, nunca no `grep`.** Vale para o agente
principal e para todo subagente.

Quando o corpus e majoritariamente documental (spec, contratos, base de conhecimento), um
**grafo de conhecimento** e o ponto de entrada mais barato e mais completo que a busca
vetorial pura, porque expoe relacoes que ninguem pensaria em consultar. Benchmark medido
em campo sobre um corpus documental de porte medio (algumas centenas de arquivos):

| Consulta | Ganho de tokens vs. ler o corpus |
| --- | --- |
| Consulta tipica ao grafo | **48,4x menos tokens** |
| "Qual e o ponto de entrada" | **371x menos tokens** |

O ganho real, porem, nao e economia — e **encontrar o que ninguem procurou**. Num caso
real, a deteccao de comunidades revelou que dois modulos haviam chegado ao mesmo
invariante sem se citarem, que tres convergiram no principio "o LLM propoe, o motor
deterministico decide", e que um mesmo controle de custo aparecia duas vezes com nomes
diferentes.

Arestas marcadas **AMBIGUOUS** viram a lista de pendencias mais honesta do projeto: sao
exatamente os pontos onde a especificacao deixou uma relacao sem fechar.

Ordem de entrada:

1. `graphify query "<pergunta>"` (ou consulta equivalente ao indice)
2. `graphify-out/wiki/index.md` — navegavel, um artigo por comunidade
3. `graphify-out/GRAPH_REPORT.md` — god nodes e comunidades
4. Só entao abrir o `.md` bruto, e apenas para o texto exato que o grafo apontou (DDL,
   contrato de API, criterio de aceite)

Duas armadilhas registradas em campo:

- **Verificar o artefato final, nao a presenca do diretorio.** Uma extracao que parou no
  meio deixa intermediarios que dao a impressao de indice pronto; consultar ali devolve
  uma fatia arbitraria do corpus — pior que ler os arquivos direto, porque parece completa.
- **Comando parecido nao e o comando certo.** `graphify update` (CLI, rebuild so de AST
  sobre todos os arquivos) e `/graphify --update` (skill, incremental com semantica) tem
  nomes quase identicos e efeitos opostos: o primeiro destruiu um grafo curado de 2.155
  nos/160 comunidades, trocando-o por 4.452 nos/2.016 comunidades estruturais. Em
  repositorio que contem documentacao, use a skill.

> **Ferramenta disponivel nao e ferramenta usada.** Preferencia de processo precisa estar
> escrita em lugar lido no inicio de cada trabalho — nao na cabeca de ninguem. E
> **instrucao escrita nao e instrucao verificada**: num caso real o comando destrutivo
> estava escrito dentro do proprio protocolo do loop; so a execucao revelou o erro.

## Selecao de ferramenta por classe de pergunta

**A ferramenta errada nao da resposta errada — da resposta cara.** Varredura para
"entender" custa ~48x mais tokens que a consulta ao indice, e leitura para "confirmar
comportamento" custa uma resposta plausivel onde a execucao daria uma verdadeira.

| A pergunta e... | Ferramenta certa | Por que |
| --- | --- | --- |
| "Onde vive X", "o que depende de X", "como isso se relaciona" | Grafo de conhecimento (`graphify query`) | Estrutura e relacao sao o que o grafo indexa; expoe conexao que ninguem pensaria em consultar |
| "Qual foi a decisao sobre X", "ja discutimos isso", "por que foi assim" | RAG vetorial (`query_neural_memory`) + `docs/adr/` | Historico e rationale sao semanticos, nao estruturais |
| "Esta proposta contradiz algo vigente?" | `check_contradiction` | Unico caminho que aciona o Circuit Breaker |
| "Qual o texto exato" (DDL, contrato de API, criterio de aceite) | Leitura direta do arquivo **que o indice apontou** | Precisao literal; o indice localiza, a leitura transcreve |
| "Este SQL/schema/rota esta correto?" | Guard executavel (`smoke-gate audit_check_sql`) | Deterministico e em <50ms; opiniao aqui e desperdicio |
| "O codigo faz o que diz?" | **Executar** (teste, comando, health check) | Comportamento se prova rodando, nao lendo |
| "Qual o estado atual do trabalho" | Disco (`PLANO.md`, `DIARIO.md`, `DIVERGENCIAS.md`) | O contexto reinicia; o disco nao |
| "Varrer muitos arquivos e me trazer so a conclusao" | Subagente, fatia dimensionada por **volume de conteudo** | Preserva a janela do agente principal |
| Localizar uma string literal que voce ja sabe que existe | `grep` | Unico uso legitimo de varredura |

Anti-padrao central: **`grep` para "entender o modulo"**. Varredura localiza literal
conhecido; ela nao constroi compreensao — e cobra caro por tentar.

Regra de escalada: comece sempre pela ferramenta mais barata que pode responder e só suba
quando a anterior falhar **e** a consulta tiver sido reformulada (ver gatilho de reconsulta
em `docs/protocols/calibration.md`).

## Ordem de recuperacao recomendada

1. chamar `query_neural_memory` com a intencao da tarefa (Neural-Prompt: context-retrieval)
2. chamar `query_neural_memory` com restricoes de seguranca e politica
3. chamar `check_contradiction` se a proposta tocar em seguranca, auth ou infra
4. se resultado BLOCK: interromper e registrar pendencia com revisao humana
5. se resultado CLEAR ou WARNING: prosseguir com contexto recuperado injetado

## Regra de escala (100+ devs)

Padrao de onboarding e retomada:

- primeiro snapshot operacional
- depois delta da sprint ativa
- historico completo apenas quando necessario

Objetivo:

- reduzir tempo para produtividade
- reduzir consumo de tokens
- manter foco no que mudou

## Guard executavel

Este protocolo trava, nao sugere. Principio n. 0 do framework: **diretriz sem guard
nao esta pronta**.

```bash
python scripts/nf_gate.py context          # so este protocolo
python scripts/nf_gate.py                  # todos os guards
```

Verifica: V1 referencia resolve (sem link pendurado) · V2 decisao cita fonte · V3 sprint concluida com evidencia real.

Roda no **pre-commit** (sobre o que esta em stage, nao sobre a arvore de trabalho) e no
**CI** (autoritativo — hook local e opt-in por clone). Instalacao em
`templates/githooks/pre-commit` e `.github/workflows/neural-flow-gates.yml`.

## Criterio PASS

- decisao com referencia explicita de fonte
- ausencia de contradicao com regras ativas
- uso de contexto minimo suficiente
- ferramenta escolhida pela classe da pergunta, comecando pela mais barata que responde

## Criterio FAIL

- decisao sem base documental
- repeticao de leitura desnecessaria
- acao fora do escopo por falta de contexto
- varredura (`grep`/leitura ampla) usada para "entender", com indice disponivel
- escalada para ferramenta mais cara sem reformular a consulta anterior

## Acao automatica em FAIL

- interromper execucao
- chamar `query_neural_memory` para reconstruir contexto minimo
- se nenhum resultado relevante for retornado: registrar lacuna como pendencia no snapshot operacional
- nunca prosseguir com acao estrutural sem contexto verificado

## Evidencias esperadas

- fonte usada na decisao
- resumo do delta aplicado
- impacto da decisao no escopo
