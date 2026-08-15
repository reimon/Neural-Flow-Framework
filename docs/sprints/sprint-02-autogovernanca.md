# Sprint 2: Autogovernanca — o framework instalado nele mesmo

## Snapshot Operacional

- App/Escopo: `neural-flow-framework — portas de entrada de agente, indice de regras e autoinstalacao`
- Status: `em andamento`
- Data de inicio: `2026-08-10`
- Data planejada de conclusao: `2026-08-24`
- Data real de conclusao: `a definir`
- Ultima atualizacao: `2026-08-11`
- Nivel de autonomia: `A1`
- Blocker principal: `nenhum`
- Proxima acao: `revisao humana do escopo da Sprint 3`

> A1 e obrigatoria: o escopo altera o instalador, que escreve na arvore de projetos
> de terceiros. Erro aqui se propaga para todo adotante.

## FinOps de Tokens

- Token budget: `500k`
- Limite de alerta: `70%`
- Consumo observado: `2.2M`
- Leitura do consumo: `faturavel, medido; 439% do budget; limite superior (ver nota)`
- Mitigacao aplicada: `budget corrigido para 2.5M na proxima sprint; causa raiz registrada abaixo`

> **Medicao, nao estimativa.** `python3 scripts/nf_tokens.py --dias 3`, lendo os
> transcripts locais em 2026-08-11. Recorte da sprint: dias 2026-08-10 e 2026-08-11.
>
> | Metrica | Valor |
> | --- | --- |
> | Faturavel (entrada + saida + escrita de cache) | **2.195.040** |
> | Entrada | 431 |
> | Saida | 157.406 |
> | Cache escrito | 2.037.203 |
> | Cache lido | 33.601.806 |
> | Requisicoes | 227 |
> | Provedores | claude-code (Opus 5) e codex (gpt-5.6-terra) |
>
> **Por que "limite superior".** A telemetria e por projeto e por dia, nao por sprint, e
> os dias 10 e 11 contem tambem a cauda da Sprint 1 (tres commits `Sprint 1 - ...` nesse
> intervalo, de outra sessao). Nao ha como separar sem inventar rateio, entao o numero
> registrado e o teto: o consumo da Sprint 2 e **no maximo** este.
> `Confianca: ALTA` para o teto (execucao verificada);
> `Confianca: BAIXA` para qualquer reparticao entre as duas sprints — por isso nao ha uma.
>
> **Causa raiz do estouro:** o budget de `500k` e o default que o instalador escreve, e
> ninguem o ajustou a realidade da sprint. Escopo real — guard novo, dois scripts,
> autoinstalacao, revisao e 77 testes — nao cabia em 500k. O erro foi no planejamento,
> nao na execucao; a linha do budget nao foi reescrita de proposito, para o estouro
> continuar visivel.
>
> **Mitigacao:** (1) budget da Sprint 3 dimensionado a partir desta medicao (2.5M);
> (2) `nf_tokens.py --dias 1` no fim de cada dia de sprint, para o estouro aparecer
> enquanto da para reagir, e nao no fechamento.
>
> **O que o dado mostra e vale manter:** 98,8% do contexto veio de cache, e a entrada
> "fria" foi de 431 tokens em 227 requisicoes. O custo nao esta em reler o repositorio —
> esta na geracao. Reduzir consumo aqui e escrever menos, nao ler menos.

## Objetivo

Fechar a lacuna que fazia o framework governar exatamente um agente: dar porta de entrada
a toda ferramenta de IA, semear o indice que a regra "indice antes de leitura" pressupoe,
e instalar o framework no proprio repositorio — o unico teste de adocao que nao pode ser
simulado.

## Escopo incluido

- Corpo canonico unico das portas de entrada e as oito portas geradas dele
- Guard `agentes` (P1–P5) e o protocolo `agent-entrypoints`
- Indice de regras deterministico, em stdlib pura
- Autoinstalacao do framework neste repositorio

## Fora do escopo

- Subir o grafo do `graphify` sobre este repositorio — o indice deterministico cobre a
  regra de entrada; o grafo entra quando houver decisao sobre custo de reindexacao
- Traduzir as portas de entrada para ingles

## Checklist de Acoes

### Bloco 1: Portas de entrada

- [x] 1.1 Corpo canonico unico para toda porta de entrada
  - Arquivo(s): `scripts/nf_agentes.py`
  - Validacao: `python3 -m unittest tests.test_guards.TestPortasDeAgente`
  - Evidencia: 9 testes verdes; oito portas geradas de uma so fonte

- [x] 1.2 Instalador escreve as portas, sem apagar instrucao do time
  - Arquivo(s): `scripts/nf_install.py`
  - Validacao: `test_instrucoes_do_projeto_nao_sao_apagadas`
  - Evidencia: brownfield com `GEMINI.md` proprio recebe as diretrizes anexadas

- [x] 1.3 Guard `agentes` travando porta ausente, divergente ou pendurada
  - Arquivo(s): `scripts/validate_agent_entrypoints.py`, `scripts/nf_gate.py`
  - Validacao: `python3 scripts/nf_gate.py agentes`
  - Evidencia: P1, P2 e P5 reproduzidos em teste e verdes apos correcao

### Bloco 2: Indice de regras

- [x] 2.1 Gerador deterministico do indice, em stdlib pura (ADR-002)
  - Arquivo(s): `scripts/nf_indice_regras.py`
  - Validacao: `python3 scripts/nf_indice_regras.py --check`
  - Evidencia: 64 regras indexadas neste repositorio, com fonte `arquivo:linha`

- [x] 2.2 Indice versionado e coberto pelo gate
  - Arquivo(s): `.gitignore`, `scripts/validate_agent_entrypoints.py`
  - Validacao: `python3 scripts/nf_gate.py agentes`
  - Evidencia: P5 trava quando a fonte muda sem regeracao

### Bloco 3: Autogovernanca

- [x] 3.1 Instalar o framework neste repositorio
  - Arquivo(s): `AGENTS.md`, `CLAUDE.md`, portas de entrada, `.githooks/pre-commit`
  - Validacao: `python3 scripts/nf_gate.py`
  - Evidencia: 7 guards conforme; hook ativo via `core.hooksPath=.githooks`

- [x] 3.2 Corrigir o `MEMORY.md` que nascia invisivel para o gate
  - Arquivo(s): `scripts/nf_install.py`, `tests/test_guards.py`
  - Validacao: `test_nenhum_artefato_nasce_invisivel_para_o_gate`
  - Evidencia: bug achado ao dogfoodar — o cabecalho de template desligava `eh_template()`

- [x] 3.3 Preencher o mapa de capacidades com o que este repositorio ja tem
  - Arquivo(s): `AGENTS.md`
  - Validacao: revisao humana
  - Evidencia: mapa preenchido com os modulos reais (`nf_guards`, `nf_gate`, `nf_agentes`)

- [x] 3.4 Preencher as proibicoes absolutas deste repositorio
  - Arquivo(s): `.github/AI_SAFETY.md`
  - Validacao: revisao humana
  - Evidencia: 7 proibicoes absolutas escritas a partir do que existe de fato — state
    local sem `prevent_destroy` sobre 10 recursos reais, `tfstate` com chaves em claro,
    instalador que escreve na arvore de terceiros

- [x] 3.5 Consolidar em `MEMORY.md` as decisoes ja vigentes
  - Arquivo(s): `MEMORY.md`
  - Validacao: revisao humana
  - Evidencia: padroes com o porque e o arquivo de referencia, tabela dos 8 modulos e
    Solutions Log com causa raiz de 4 incidentes datados

- [x] 3.6 Medir e registrar o consumo real de tokens (B4)
  - Arquivo(s): `docs/sprints/sprint-02-autogovernanca.md`, `MEMORY.md`
  - Validacao: `python3 scripts/nf_gate.py budget`
  - Evidencia: 2.2M faturaveis medidos com `nf_tokens.py`; estouro de 439% declarado com
    causa raiz e mitigacao, em vez de reescrever o budget

## Riscos / Blockers / ETA

- Risco: adotante edita uma porta de entrada em vez de `AGENTS.md`, criando regra que so
  uma ferramenta conhece. Impacto: divergencia silenciosa entre agentes. Mitigacao: o
  guard P2 trava, e o proprio texto da porta diz para nao edita-la.
- Risco: o extrator do indice e conservador e pode deixar regra de fora. Impacto: agente
  nao ve uma regra que existe. Mitigacao: o indice traz a fonte de cada regra e nao
  substitui `AGENTS.md` — e ponto de entrada, nao resumo autoritativo.

## Evidencias de Implementacao

- `python3 -m unittest discover -s tests` — 77 testes, verde
- `python3 scripts/nf_gate.py` — 7 guards conforme neste repositorio
- `python3 scripts/nf_install.py --target . --smoke-gate no` — autoinstalacao valida no gate
- `python3 scripts/nf_tokens.py --dias 3` — consumo real medido: 2.2M faturaveis, 227
  requisicoes, 98,8% de aproveitamento de cache (ver FinOps)
- Bug encontrado ao dogfoodar: `MEMORY.md` instalado carregava o cabecalho
  `> TEMPLATE Neural-Flow`, que desliga todos os guards sobre o arquivo — corrigido e
  coberto por teste de regressao

## Pendencias para a Proxima Sprint

- [feito] Budget da Sprint 3 dimensionado em 2.5M a partir desta medicao - ver
  `docs/sprints/sprint-03-divida-de-auth-e-telemetria.md`
- Recorte de telemetria por sprint (hoje e por dia) para o consumo parar de ser limite
  superior - sprint alvo: 3, item 1.1
- Decidir se o grafo do `graphify` sobe sobre o repositorio - sprint alvo: 3, item 3.1

## Regras

- Validar antes de commitar: `python3 scripts/nf_gate.py`
- Item so recebe `[x]` quando a acao foi realmente executada.
