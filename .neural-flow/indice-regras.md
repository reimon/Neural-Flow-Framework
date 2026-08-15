# Indice de regras

> Gerado por `python3 scripts/nf_indice_regras.py`. **Nao edite a mao** —
> edite a fonte de cada regra e regere. O guard `agentes` trava a divergencia.

Consulte este indice **antes** de ler os arquivos. Cada linha traz a fonte
(`arquivo:linha`) — leia so o que a resposta exigir.

- regras indexadas: **64**
- impressao digital das fontes: `0146459e2144aaec`

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
| `SEG-003` | 3. NUNCA versionar segredo | `.github/AI_SAFETY.md:44` | — |
| `SEG-004` | 4. NUNCA relaxar um guard para fazer o gate passar | `.github/AI_SAFETY.md:58` | — |
| `SEG-005` | 5. NUNCA marcar item de sprint como [x] sem execucao verificada | `.github/AI_SAFETY.md:66` | — |
| `SEG-006` | 6. NUNCA editar artefato gerado a mao | `.github/AI_SAFETY.md:72` | — |
| `SEG-007` | 7. NUNCA commitar as imagens de tema | `.github/AI_SAFETY.md:78` | — |
| `SEG-008` | Commit ou push. Regra fixa do usuario: nunca sem autorizacao explicita. | `.github/AI_SAFETY.md:89` | — |
| `SEG-009` | Remover ou renomear um guard, um codigo de verificacao (S1, V3, P2...) ou um campo obrigatorio de template — e mudanca MAJOR: quebra projeto que ja adotou. | `.github/AI_SAFETY.md:94` | — |
| `SEG-010` | Nomes de recursos derivados em runtime, nunca fixos em docs/scripts — sufixos mudam e invalidam tudo de uma vez. | `.github/AI_SAFETY.md:128` | — |
| `SEG-011` | Operacao critica imprime evidencia do que realmente fez — nunca afirmar limpeza, remocao ou execucao que nao aconteceu. | `.github/AI_SAFETY.md:130` | — |

## Arquitetura

| ID | Regra | Fonte | Guard |
| --- | --- | --- | --- |
| `ARQ-001` | Todo script instalavel carrega NFGUARDASSINATURA — sem ela o nfgate se recusa a executar o arquivo, para nao chamar um homonimo do projeto com os nossos argumentos. | `AGENTS.md:45` | — |
| `ARQ-002` | O instalador nunca sobrescreve artefato existente sem --force; colisao vira instalacao lado a lado (nf<nome>) ou anexo, sempre com aviso. | `AGENTS.md:47` | — |
| `ARQ-003` | O instalador escreve na arvore de terceiros. Mudanca ali opera em A1 e so fecha com instalacao ponta a ponta executada, nunca com leitura do diff. | `AGENTS.md:59` | — |
| `ARQ-004` | BAIXA e acao irreversivel (perder dado, expor dado pessoal, gastar dinheiro, mexer em producao) ⇒ pare e pergunte. | `AGENTS.md:92` | — |
| `ARQ-005` | BAIXA e acao reversivel ⇒ siga conservador e registre a divergencia. Nao pergunte. | `AGENTS.md:94` | — |
| `ARQ-006` | Nao pergunte o que a spec ja responde — isso e falha de leitura, nao prudencia. | `AGENTS.md:95` | — |
| `ARQ-007` | Numeracao de ADR e sequencial e nunca reutilizada; ADR aceito e imutavel — mudanca de rumo gera ADR que o supera → guard: nfgate.py adr. | `AGENTS.md:109` | `nfgate` |
| `ARQ-008` | Nunca commitar ou dar push sem autorizacao explicita. | `AGENTS.md:118` | — |
| `ARQ-009` | Stage apenas os proprios arquivos — nunca o WIP de outra sessao/terminal. | `AGENTS.md:120` | — |

## Execucao

| ID | Regra | Fonte | Guard |
| --- | --- | --- | --- |
| `EXE-001` | Pergunta sobre o projeto comeca no indice, nunca no grep. Varredura para "entender" custa ~48x mais tokens que a consulta ao indice. | `CLAUDE.md:68` | — |
| `EXE-002` | Confianca BAIXA + acao irreversivel (perder dado, expor dado pessoal, gastar dinheiro, mexer em producao) ⇒ pare e pergunte. Reversivel ⇒ siga conservador e registre. | `CLAUDE.md:72` | — |
| `EXE-003` | Nunca commitar ou dar push sem autorizacao explicita. | `CLAUDE.md:77` | — |
| `EXE-004` | Stage com caminhos explicitos. Nunca git add -A nem git add .. | `CLAUDE.md:78` | — |

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
| `PRO-012` | Neural-Memory: docs/adr/.md entra nas fontes indexadas; checkcontradiction deve retornar WARNING/BLOCK para proposta que contradiz ADR aceito. | `docs/protocols/adr-governance.md:42` | — |
| `PRO-013` | Toda decisao arquitetural do periodo possui ADR com status e sprint de origem | `docs/protocols/adr-governance.md:64` | — |
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
| `PRO-025` | Toda conclusao tecnica do periodo carrega nivel de confianca e classe de evidencia | `docs/protocols/calibration.md:147` | — |
| `PRO-026` | Toda combinacao BAIXA + irreversivel resultou em pergunta ao humano | `docs/protocols/calibration.md:151` | — |
| `PRO-027` | nunca prosseguir com acao estrutural sem contexto verificado | `docs/protocols/context-vector.md:155` | — |
| `PRO-028` | Rearme exige revisão e aprovação humana explícita. | `docs/protocols/neural-memory.md:89` | — |
| `PRO-029` | Toda tarefa relevante precedida de chamada a queryneuralmemory | `docs/protocols/neural-memory.md:95` | — |
| `PRO-030` | Todo modulo com codigo possui spec completa no padrao, aprovada antes do codigo | `docs/protocols/spec-first.md:113` | — |
| `PRO-031` | Dado de dominio ausente: item marcado [BLOQUEADO], nunca preenchido com valor plausivel | `docs/protocols/spec-first.md:128` | — |

## Decisao

| ID | Regra | Fonte | Guard |
| --- | --- | --- | --- |
| `ADR-001` | Gatilho de reconsulta: indice fraco exige reformular antes de escalar para varredura; BAIXA + irreversivel exige parar e perguntar; BAIXA + reversivel segue conservador com divergencia registrada. | `docs/adr/ADR-004-protocolo-de-calibracao.md:30` | — |

## Memoria

| ID | Regra | Fonte | Guard |
| --- | --- | --- | --- |
| `MEM-001` | Modelo obrigatorio de execucao: todo desenvolvimento organizado por sprints numeradas. | `MEMORY.md:12` | — |
| `MEM-002` | Padrao de commit: toda mensagem comeca com Sprint N - <descricao>. | `MEMORY.md:15` | — |
| `MEM-003` | Instalador: install.sh (wrapper bash) → scripts/nfinstall.py. Detecta greenfield/brownfield, e idempotente e nunca sobrescreve sem --force. | `MEMORY.md:24` | — |
| `MEM-004` | Toda diretriz forte tem guard (principio n. 0). Guard novo entra pelo dicionario GUARDS de nfgate.py e chega com protocolo em docs/protocols/, testes nas duas direcoes e entrada no diagrama — no mesmo commit. | `MEMORY.md:44` | — |
| `MEM-005` | NFGUARDASSINATURA em todo script instalavel. Sem a assinatura o nfgate se recusa a executar o arquivo: projeto brownfield pode ter homonimo com outra interface. Referencia: nfgate.ehnosso(). | `MEMORY.md:47` | — |
| `MEM-006` | Nunca sobrescrever trabalho do adotante. Colisao de script vira instalacao lado a lado (nf<nome>); porta de entrada que ja existia recebe as diretrizes anexadas. Sempre com aviso no relatorio. | `MEMORY.md:65` | — |
| `MEM-007` | Template vai para o projeto via copiartemplate, nunca readtext direto: o cabecalho > TEMPLATE Neural-Flow desliga ehtemplate() e faz o artefato nascer invisivel para o gate. | `MEMORY.md:68` | — |
| `MEM-008` | Sempre datar (data absoluta, nunca relativa). | `MEMORY.md:135` | — |
