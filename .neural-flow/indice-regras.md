# Indice de regras

> Gerado por `python3 scripts/nf_indice_regras.py`. **Nao edite a mao** —
> edite a fonte de cada regra e regere. O guard `agentes` trava a divergencia.

Consulte este indice **antes** de ler os arquivos. Cada linha traz a fonte
(`arquivo:linha`) — leia so o que a resposta exigir.

- regras indexadas: **68**
- impressao digital das fontes: `14eb1bcad914f539`

## Guards executaveis

Rode todos com `python3 scripts/nf_gate.py`. Nunca use `--no-verify`.

| Guard | Protocolo | O que trava |
| --- | --- | --- |
| `sprint` | `state-protocol` | snapshot completo, status sem ambiguidade, escopo sensivel em A0/A1 |
| `budget` | `token-circuit-breaker` | budget declarado, consumo registrado, estouro com mitigacao |
| `context` | `context-vector` | referencia resolve, decisao cita fonte, evidencia real |
| `adr` | `adr-governance` | numeracao unica, sem referencia pendurada nem ciclo de supersecao |
| `spec` | `spec-first` | estrutura minima de spec, invariantes com ID, aceite numerado |
| `calibration` | `calibration` | confianca declarada, BAIXA nao fecha item, irreversivel nao vira registro |
| `agentes` | `agent-entrypoints` | toda ferramenta de IA tem porta de entrada apontando para AGENTS.md; indice de regras em dia |

## Seguranca

| ID | Regra | Fonte | Guard |
| --- | --- | --- | --- |
| `SEG-001` | 1. NUNCA executar apply/destroy de Terraform | `.github/AI_SAFETY.md:22` | — |
| `SEG-002` | 2. NUNCA alterar randomstring.suffix | `.github/AI_SAFETY.md:34` | — |
| `SEG-003` | 3. NUNCA versionar segredo | `.github/AI_SAFETY.md:45` | — |
| `SEG-004` | 4. NUNCA relaxar um guard para fazer o gate passar | `.github/AI_SAFETY.md:59` | — |
| `SEG-005` | 5. NUNCA marcar item de sprint como [x] sem execucao verificada | `.github/AI_SAFETY.md:67` | — |
| `SEG-006` | 6. NUNCA editar artefato gerado a mao | `.github/AI_SAFETY.md:73` | — |
| `SEG-007` | 7. NUNCA commitar as imagens de tema | `.github/AI_SAFETY.md:79` | — |
| `SEG-008` | Commit ou push. Regra fixa do usuario: nunca sem autorizacao explicita. | `.github/AI_SAFETY.md:94` | — |
| `SEG-009` | Remover ou renomear um guard, um codigo de verificacao (S1, V3, P2...) ou um campo obrigatorio de template — e mudanca MAJOR: quebra projeto que ja adotou. | `.github/AI_SAFETY.md:99` | — |
| `SEG-010` | Nomes de recursos derivados em runtime, nunca fixos em docs/scripts — sufixos mudam e invalidam tudo de uma vez. | `.github/AI_SAFETY.md:133` | — |
| `SEG-011` | Operacao critica imprime evidencia do que realmente fez — nunca afirmar limpeza, remocao ou execucao que nao aconteceu. | `.github/AI_SAFETY.md:135` | — |

## Arquitetura

| ID | Regra | Fonte | Guard |
| --- | --- | --- | --- |
| `ARQ-001` | Todo script instalavel carrega NFGUARDASSINATURA — sem ela o nfgate se recusa a executar o arquivo, para nao chamar um homonimo do projeto com os nossos argumentos. | `AGENTS.md:46` | — |
| `ARQ-002` | O instalador nunca sobrescreve artefato existente sem --force; colisao vira instalacao lado a lado (nf<nome>) ou anexo, sempre com aviso. | `AGENTS.md:49` | — |
| `ARQ-003` | O instalador escreve na arvore de terceiros. Mudanca ali opera em A1 e so fecha com instalacao ponta a ponta executada, nunca com leitura do diff. | `AGENTS.md:61` | — |
| `ARQ-004` | BAIXA e acao irreversivel (perder dado, expor dado pessoal, gastar dinheiro, mexer em producao) ⇒ pare e pergunte. | `AGENTS.md:94` | — |
| `ARQ-005` | BAIXA e acao reversivel ⇒ siga conservador e registre a divergencia. Nao pergunte. | `AGENTS.md:96` | — |
| `ARQ-006` | Nao pergunte o que a spec ja responde — isso e falha de leitura, nao prudencia. | `AGENTS.md:97` | — |
| `ARQ-007` | Numeracao de ADR e sequencial e nunca reutilizada; ADR aceito e imutavel — mudanca de rumo gera ADR que o supera → guard: nfgate.py adr. | `AGENTS.md:131` | `nfgate` |
| `ARQ-008` | Nunca commitar ou dar push sem autorizacao explicita. | `AGENTS.md:140` | — |
| `ARQ-009` | Stage apenas os proprios arquivos — nunca o WIP de outra sessao/terminal. | `AGENTS.md:142` | — |

## Execucao

| ID | Regra | Fonte | Guard |
| --- | --- | --- | --- |
| `EXE-001` | Pergunta sobre o projeto comeca no indice, nunca no grep. Varredura para "entender" custa ~48x mais tokens que a consulta ao indice. | `CLAUDE.md:90` | — |
| `EXE-002` | Confianca BAIXA + acao irreversivel (perder dado, expor dado pessoal, gastar dinheiro, mexer em producao) ⇒ pare e pergunte. Reversivel ⇒ siga conservador e registre. | `CLAUDE.md:94` | — |
| `EXE-003` | Nunca commitar ou dar push sem autorizacao explicita. | `CLAUDE.md:99` | — |
| `EXE-004` | Stage com caminhos explicitos. Nunca git add -A nem git add .. | `CLAUDE.md:100` | — |

## Protocolo

| ID | Regra | Fonte | Guard |
| --- | --- | --- | --- |
| `PRO-001` | [ ] Toda execucao tecnica do periodo possui sprint valida antes do inicio. | `docs/protocols/README.md:82` | — |
| `PRO-002` | [ ] Toda sprint auditada declarou token budget. | `docs/protocols/README.md:92` | — |
| `PRO-003` | Executar 1 auditoria mensal obrigatoria. | `docs/protocols/README.md:140` | — |
| `PRO-004` | [ ] Toda tarefa relevante do periodo precedida de chamada a queryneuralmemory. | `docs/protocols/README.md:145` | — |
| `PRO-005` | [ ] Toda decisao arquitetural do periodo possui ADR numerado com status e sprint de origem. | `docs/protocols/README.md:156` | — |
| `PRO-006` | [ ] Todo modulo com codigo possui spec completa aprovada antes do codigo. | `docs/protocols/README.md:166` | — |
| `PRO-007` | [ ] Toda combinacao BAIXA + acao irreversivel parou para aprovacao humana. | `docs/protocols/README.md:192` | — |
| `PRO-008` | Reversao/superacao de decisao anterior (novo ADR com Superado por, nunca edicao) | `docs/protocols/adr-governance.md:20` | — |
| `PRO-009` | Numeracao sequencial ADR-NNN; numero nunca e reutilizado. | `docs/protocols/adr-governance.md:27` | — |
| `PRO-010` | Todo ADR referencia a sprint de origem (rastreabilidade Neural-Flow). | `docs/protocols/adr-governance.md:30` | — |
| `PRO-011` | Se o ADR estabelece regra impositiva, deve nascer com guard (lint/teste/CI) ou declarar explicitamente que o guard e aspiracional — principio "documentacao orienta, guard obriga" (templates/AGENTS-template.md). | `docs/protocols/adr-governance.md:31` | — |
| `PRO-012` | Neural-Memory: docs/adr/.md entra nas fontes indexadas; checkcontradiction deve retornar WARNING/BLOCK para proposta que contradiz ADR aceito. | `docs/protocols/adr-governance.md:61` | — |
| `PRO-013` | Toda decisao arquitetural do periodo possui ADR com status e sprint de origem | `docs/protocols/adr-governance.md:83` | — |
| `PRO-014` | Sensivel: exige mascaramento | `docs/protocols/aegis-security.md:15` | — |
| `PRO-015` | Segredo: proibido em prompt e documentacao operacional | `docs/protocols/aegis-security.md:16` | — |
| `PRO-016` | [ ] Toda execucao tecnica do periodo possui sprint valida antes do inicio. | `docs/protocols/auditoria-mensal-template.md:20` | — |
| `PRO-017` | [ ] Toda sprint auditada declarou token budget. | `docs/protocols/auditoria-mensal-template.md:30` | — |
| `PRO-018` | Um item por iteracao. Nunca dois. Um item pequeno que termina verde vale mais que tres pela metade. | `docs/protocols/autonomous-loop.md:50` | — |
| `PRO-019` | Verde no comando de verificacao e a unica condicao para marcar pronto. Explicitamente proibido: teste desabilitado, skip/xfail novo ou assercao afrouxada para passar. Num loop nao ha revisor — ou a regra esta escrita, ou nao existe. | `docs/protocols/autonomous-loop.md:52` | — |
| `PRO-020` | Nenhuma credencial externa. Todo servico externo entra como interface + implementacao falsa deterministica, ativa por padrao. O sistema tem que subir numa maquina sem nenhuma chave. | `docs/protocols/autonomous-loop.md:59` | — |
| `PRO-021` | Falha fechada. Caminho degradado nunca relaxa autorizacao, consentimento ou mascaramento. | `docs/protocols/autonomous-loop.md:62` | — |
| `PRO-022` | Continua BAIXA apos os dois degraus: a lacuna e real. Registrar como divergencia (em loop) ou pendencia de contexto (em sprint) com a decisao mais conservadora tomada para seguir — nunca preencher com o valor plausivel. | `docs/protocols/calibration.md:52` | — |
| `PRO-023` | Evidencia Sintetica: define se ha prova; este protocolo define quanto ela prova. Item so fecha com ALTA quando o criterio de aceite exige execucao. | `docs/protocols/calibration.md:93` | — |
| `PRO-024` | Loop Autonomo: BAIXA + reversivel ⇒ DIVERGENCIAS.md; BAIXA + irreversivel ⇒ parar e perguntar. Item nunca e marcado [x] com BAIXA. | `docs/protocols/calibration.md:97` | — |
| `PRO-025` | Toda conclusao tecnica do periodo carrega nivel de confianca, verificacao executada e resultado observado | `docs/protocols/calibration.md:148` | — |
| `PRO-026` | Toda combinacao BAIXA + irreversivel resultou em pergunta ao humano | `docs/protocols/calibration.md:152` | — |
| `PRO-027` | nunca prosseguir com acao estrutural sem contexto verificado | `docs/protocols/context-vector.md:165` | — |
| `PRO-028` | Rearme exige revisão e aprovação humana explícita. | `docs/protocols/neural-memory.md:89` | — |
| `PRO-029` | Toda tarefa relevante precedida de chamada a queryneuralmemory | `docs/protocols/neural-memory.md:95` | — |
| `PRO-030` | Descobrir equivalencia por nome conhecido ou cobertura de secoes. Empate vira ambiguidade e pede mapeamento, nunca escolha silenciosa. | `docs/protocols/product-documentation.md:28` | — |
| `PRO-031` | Cada linha de implementacao do plano mestre usa ID IMP-NNN, ordem unica, dependencia explicita, requisitos REQ-NNN e criterios CA-NNN. Dependencia deve anteceder o item; referencias precisam existir. | `docs/protocols/product-documentation.md:79` | — |
| `PRO-032` | Todo modulo com codigo possui spec completa no padrao, aprovada antes do codigo | `docs/protocols/spec-first.md:113` | — |
| `PRO-033` | Dado de dominio ausente: item marcado [BLOQUEADO], nunca preenchido com valor plausivel | `docs/protocols/spec-first.md:128` | — |

## Decisao

| ID | Regra | Fonte | Guard |
| --- | --- | --- | --- |
| `ADR-001` | Gatilho de reconsulta: indice fraco exige reformular antes de escalar para varredura; BAIXA + irreversivel exige parar e perguntar; BAIXA + reversivel segue conservador com divergencia registrada. | `docs/adr/ADR-004-protocolo-de-calibracao.md:30` | — |
| `ADR-005` | Implementacao combina tdd + principios de Karpathy + smoke-gate + python3 scripts/nfgate.py, e nunca executa git commit ou git push sem autorizacao humana explicita. | `docs/adr/ADR-010-skills-operacionais-de-agente.md:67` | — |

## Memoria

| ID | Regra | Fonte | Guard |
| --- | --- | --- | --- |
| `MEM-001` | Modelo obrigatorio de execucao: todo desenvolvimento organizado por sprints numeradas. | `MEMORY.md:12` | — |
| `MEM-002` | Padrao de commit: toda mensagem comeca com Sprint N - <descricao>. | `MEMORY.md:15` | — |
| `MEM-003` | Instalador: install.sh (wrapper bash) → scripts/nfinstall.py. Detecta greenfield/brownfield, e idempotente e nunca sobrescreve sem --force. | `MEMORY.md:24` | — |
| `MEM-004` | Toda diretriz forte tem guard (principio n. 0). Guard novo entra pelo dicionario GUARDS de nfgate.py e chega com protocolo em docs/protocols/, testes nas duas direcoes e entrada no diagrama — no mesmo commit. | `MEMORY.md:44` | — |
| `MEM-005` | NFGUARDASSINATURA em todo script instalavel. Sem a assinatura o nfgate se recusa a executar o arquivo: projeto brownfield pode ter homonimo com outra interface. Referencia: nfgate.ehnosso(). | `MEMORY.md:47` | — |
| `MEM-006` | Nunca sobrescrever trabalho do adotante. Colisao de script vira instalacao lado a lado (nf<nome>); porta de entrada que ja existia recebe as diretrizes anexadas. Sempre com aviso no relatorio. | `MEMORY.md:71` | — |
| `MEM-007` | Template vai para o projeto via copiartemplate, nunca readtext direto: o cabecalho > TEMPLATE Neural-Flow desliga ehtemplate() e faz o artefato nascer invisivel para o gate. | `MEMORY.md:74` | — |
| `MEM-008` | Sempre datar (data absoluta, nunca relativa). | `MEMORY.md:151` | — |
| `MEM-009` | [ ] Rodar python3 scripts/nfazuresmoke.py num ambiente autenticado - trava o bloco 2 inteiro da Sprint 4; exige az login, nao ha como agente sem tenant fechar | `MEMORY.md:158` | — |

## Vigencia das decisoes

- [ADR-001](../docs/adr/ADR-001-memoria-backend-agnostica.md) — aceito (sprint 1). O protocolo define **contratos**, nao tecnologia: indexacao com metadados minimos, busca hibrida, MCP tools `query_neural_memory` e `check_contradiction`, reindex incremental e indice sempre reconstruivel a partir do git.
- [ADR-002](../docs/adr/ADR-002-guards-em-stdlib-pura.md) — aceito (sprint 1). Todos os guards sao Python 3.10+ usando exclusivamente a biblioteca padrao, orquestrados por `scripts/nf_gate.py`. Helpers compartilhados vivem em `scripts/nf_guards.py` — os validadores nao duplicam parsing.
- [ADR-003](../docs/adr/ADR-003-divida-admin-key-vs-rbac.md) — aceito (sprint 1). Registrar a divida explicitamente em vez de silencia-la ou de bloquear a divulgacao por causa dela:
- [ADR-004](../docs/adr/ADR-004-protocolo-de-calibracao.md) — aceito (sprint 1). Criar o 10o protocolo, com tres mecanismos:
- [ADR-005](../docs/adr/ADR-005-grafo-do-graphify-neste-repositorio.md) — proposto. **Nao subir o grafo do `graphify` sobre este repositorio nesta etapa.** O indice deterministico cobre a regra de entrada, e a medicao mostra que o gargalo aqui e geracao, nao leitura: um grafo reduziria um custo que nao estamos pagando.
- [ADR-006](../docs/adr/ADR-006-gateway-de-acoes.md) — aceito (sprint 5). superacao: ADR-012 (execucao)
- [ADR-007](../docs/adr/ADR-007-sandbox-do-gateway.md) — aceito (sprint 5). superacao: ADR-008 (integral), ADR-011 (isolamento), ADR-012 (execucao)
- [ADR-008](../docs/adr/ADR-008-adaptadores-de-sandbox-validados.md) — aceito (sprint 5). superacao: ADR-011 (isolamento), ADR-012 (execucao)
- [ADR-009](../docs/adr/ADR-009-base-documental-do-produto.md) — aceito (sprint 6). Adotar seis papeis documentais padronizados: PRD, TRD, Fluxo do App, UI/UX Design, Esquema Backend e Plano de Implementacao. Cada projeto pode mapear arquivos e secoes existentes em `.neural-flow.json`; o framework nao renomeia nem sobrescreve esses arquivos.
- [ADR-010](../docs/adr/ADR-010-skills-operacionais-de-agente.md) — aceito (sprint 8). 1. **Empacotamento offline no kit (`templates/skills/`):** incorporamos as 27 skills do pacote oficial promovido de `mattpocock/skills` (`engineering` + `productivity`) em `templates/skills/<skill-name>/`. O instalador (`scripts/nf_install.py`) e o gerador de portas (`scripts/nf_agentes.py --escrever`) distribuem...
- [ADR-011](../docs/adr/ADR-011-gateway-sem-sandbox-interno.md) — aceito (sprint 9). superacao: ADR-012 (execucao)
- [ADR-012](../docs/adr/ADR-012-validacao-local-sem-action-gateway.md) — aceito (sprint 10). Retirar o Action Gateway, sua politica e seu guard. A validacao do projeto usa os testes e `scripts/nf_gate.py`, incluindo o hook local sobre os arquivos em stage. Commit e push continuam sujeitos a autorizacao explicita.
- [ADR-013](../docs/adr/ADR-013-vigencia-no-indice.md) — aceito (sprint 11). Publicar separadamente as regras vigentes, as regras historicas e as relacoes de superacao no indice. Resolver o escopo declarado em Status pelas secoes do documento anterior. Um mapeamento versionado associa titulos antigos ao escopo.
- [ADR-014](../docs/adr/ADR-014-relatorio-dos-guards.md) — aceito (sprint 12). Gerar o relatorio de execucao no gate. Cada guard registra estado, arquivos, achados e motivo. Terminal, painel e resumo do CI apresentam esses resultados. O painel pode abrir um relatorio salvo, inclusive o de uma execucao reprovada.

## Regras historicas

- `docs/adr/ADR-006-gateway-de-acoes.md:22` — ADR-012 (execucao). Toda acao precisa existir em .neural-flow/action-policy.json, com id, comando permitido, sprint, item, risco e prazo.
- `docs/adr/ADR-006-gateway-de-acoes.md:26` — ADR-012 (execucao). Acoes sensitive e irreversible exigem A0/A1 e confirmacao interativa em TTY para o hash exato do comando. Acoes desconhecidas sao rejeitadas, nunca inferidas como seguras.
- `docs/adr/ADR-006-gateway-de-acoes.md:29` — ADR-012 (execucao). Toda tentativa executada gera auditoria sem registrar o comando bruto, segredos ou argumentos sensiveis. A falta de capacidade de auditar tambem bloqueia a execucao.
- `docs/adr/ADR-011-gateway-sem-sandbox-interno.md:20` — ADR-012 (execucao). A politica v1 exige migracao explicita antes de executar ou planejar uma acao.
