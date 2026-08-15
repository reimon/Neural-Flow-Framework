# Sprint 3: Divida de autenticacao e telemetria por sprint

## Snapshot Operacional

- App/Escopo: `neural-flow-framework — migracao para Entra ID/RBAC e recorte de telemetria por sprint`
- Status: `em andamento`
- Data de inicio: `2026-08-15`
- Data planejada de conclusao: `2026-08-29`
- Data real de conclusao: `a definir`
- Ultima atualizacao: `2026-08-15`
- Nivel de autonomia: `A1`
- Blocker principal: `2.1 nao verificavel sem credencial Azure — codigo pronto, execucao pendente`
- Proxima acao: `rodar a ingestao keyless num ambiente com Entra ID para fechar 2.1`

> A1 e obrigatoria: o escopo toca autenticacao e segredo (ADR-003) e o Terraform que
> gerencia 10 recursos reais com state local. O guard S4 reprova A2/A3 aqui.

## FinOps de Tokens

- Token budget: `2.5M`
- Limite de alerta: `70%`
- Consumo observado: `em andamento`
- Mitigacao aplicada: `nao se aplica`

> **De onde vem o 2.5M.** Nao e estimativa: e a medicao da Sprint 2 mais uma margem
> declarada. A Sprint 2 consumiu **2.195.040 tokens faturaveis** em 227 requisicoes
> (`python3 scripts/nf_tokens.py --dias 3`, registrado em
> `docs/sprints/sprint-02-autogovernanca.md`). Arredondando para cima e somando ~14% de
> folga: **2.5M**.
>
> **Por que a Sprint 2 e a base defensavel.** Escopo comparavel — codigo de guard, script
> novo, testes, revisao e documentacao — e o mesmo par de provedores. A Sprint 1 nao serve
> de base: era colheita de protocolos, majoritariamente escrita de documento, com perfil de
> consumo diferente.
>
> **Por que essa margem, e nao o dobro.** Budget folgado demais nao trava nada e vira
> numero decorativo; o ponto do Circuit Breaker e o estouro **doer** enquanto ainda da para
> reagir. 14% cobre variacao normal de iteracao, nao mudanca de escopo — se o escopo
> crescer, o certo e estourar e registrar, como a Sprint 2 fez.
>
> **O que este numero nao e.** A medicao da Sprint 2 e um **limite superior** (a telemetria
> agrega por dia, e os dias 10 e 11 contem a cauda da Sprint 1), entao 2.5M pode estar
> generoso. Isso e conservador na direcao certa — errar para cima num budget nao esconde
> consumo, so atrasa o alarme. O item 1.1 desta sprint existe para a proxima base ser exata.
> `Confianca: MEDIA` — deriva de medicao verificada, mas a atribuicao por sprint e inferida.
>
> **Alerta em 70% = 1.75M.** Verificar com `python3 scripts/nf_tokens.py --dias 1` ao fim
> de cada dia de trabalho, conforme a mitigacao acordada na Sprint 2.

## Objetivo

Pagar a divida de seguranca declarada no ADR-003 e fechar a lacuna de medicao que obrigou
a Sprint 2 a registrar consumo como limite superior.

## Escopo incluido

- Migrar `ingest.py`, `search.py` e o servidor MCP para `DefaultAzureCredential`
- Adicionar as role assignments correspondentes no Terraform
- Recorte de telemetria por sprint em `nf_tokens.py` (hoje agrega por dia)
- Decisao registrada sobre subir o grafo do `graphify` sobre este repositorio

## Fora do escopo

- Backend remoto de Terraform com lock — melhoria real, mas e outra sprint
- `prevent_destroy` nos recursos stateful — depende da decisao de backend acima
- Traducao do framework para ingles
- Qualquer `terraform apply`: o escopo desta sprint e codigo e ADR, nao execucao

## Checklist de Acoes

### Bloco 1: Telemetria

- [x] 1.1 Recorte por sprint em `nf_tokens.py`
  - Arquivo(s): `scripts/nf_tokens.py`, `tests/test_guards.py`
  - Validacao: `python3 -m unittest tests.test_guards.TestTelemetriaDeTokens`
  - Evidencia: 8 testes verdes. `--sprint N` le o intervalo do proprio arquivo de sprint;
    `--desde/--ate` recortam a mao. Onde o recorte **nao** resolve — dia partilhado por
    duas sprints — a saida denuncia (`exato: false`) em vez de deixar o teto com cara de
    medida

- [x] 1.2 Reprocessar a Sprint 2 com o recorte novo e comparar com o teto registrado
  - Arquivo(s): `docs/sprints/sprint-02-autogovernanca.md`
  - Validacao: `python3 scripts/nf_tokens.py --desde 2026-08-10 --ate 2026-08-11`
  - Evidencia: 2.233.068 faturaveis contra os 2.195.040 registrados — diferenca de 1,7%,
    explicada por requisicoes do dia 11 posteriores a medicao original. O teto registrado
    se confirma. `--sprint 2` continua marcando `exato: false`, porque a Sprint 1 seguiu
    aberta no mesmo intervalo: o recorte melhora a atribuicao, nao elimina a sobreposicao

### Bloco 2: Divida de autenticacao (ADR-003)

- [ ] 2.1 Migrar a implementacao de referencia para `DefaultAzureCredential`
  - Arquivo(s): `scripts/nf_azure_auth.py`, `scripts/ingest.py`, `scripts/search.py`,
    `mcp/neural-memory-server/server.py`
  - Validacao: ingestao roda sem admin key no ambiente
  - Evidencia: **codigo pronto, criterio de aceite NAO atendido.** `nf_azure_auth.py`
    centraliza a decisao: keyless por padrao, `NF_AZURE_AUTH=key` como opt-in explicito
    que avisa em toda execucao, e **sem fallback automatico** — cair na chave sozinho
    converteria erro de permissao, que se conserta, em dependencia permanente de segredo.
    Os tres consumidores passaram a usa-lo e `AZURE_*_KEY` deixou de ser obrigatoria no
    import. Verificado: modo `entra` e `key` resolvem certo, `python3 -m ast` limpo nos
    quatro arquivos. **Nao verificado:** ingestao real — exige credencial Entra ID que
    esta maquina nao tem. `Confianca: MEDIA` (codigo e SDK documentado, sem execucao);
    o item **nao fecha** com MEDIA, por isso segue aberto

- [x] 2.2 Role assignments no Terraform, sem apply
  - Arquivo(s): `infra/terraform/main.tf`, `infra/terraform/variables.tf`
  - Validacao: `terraform validate`
  - Evidencia: `Success! The configuration is valid` e `terraform fmt -check` limpo nos
    dois arquivos. Search Index Data Contributor, Search Service Contributor e Cognitive
    Services OpenAI User, para o principal que aplica mais `var.rbac_principal_ids`.
    `plan` nao rodou: exige credencial Azure e leitura do state, que nao tem copia.
    A admin key **nao** foi removida do Key Vault nem `local_authentication` desabilitado
    — isso e mudanca de comportamento em recurso existente e so depois de 2.1 verificado

- [ ] 2.3 ADR que supera o ADR-003 quando a migracao concluir
  - Arquivo(s): `docs/adr/`
  - Validacao: `python3 scripts/nf_gate.py adr`
  - Evidencia: **deliberadamente nao feito.** O ADR-003 registra uma divida; declara-la
    paga com o codigo escrito mas nunca executado seria exatamente a falha que o protocolo
    de Calibracao proibe. Superar o ADR-003 depende de 2.1 fechar com execucao verificada

### Bloco 3: Indice

- [x] 3.1 Decidir e registrar se o grafo do `graphify` sobe sobre este repositorio
  - Arquivo(s): `docs/adr/ADR-005-grafo-do-graphify-neste-repositorio.md`
  - Validacao: `python3 scripts/nf_gate.py adr`
  - Evidencia: ADR-005, status `Proposto` — a decisao e de direcao de produto, entao quem
    aceita e o humano. Recomendacao: nao subir agora. Corpus de ~30 documentos de
    governanca esta muito abaixo do porte onde o ganho de 48x foi medido, e a telemetria
    mostra 98,8% de cache — o gargalo aqui e geracao, nao leitura. Tres gatilhos objetivos
    reabrem a decisao

## Riscos / Blockers / ETA

- Risco: a migracao para RBAC exige permissao no tenant que pode nao estar disponivel.
  Impacto: bloco 2 trava. Mitigacao: o bloco 1 e independente e segue sozinho.
- Risco: `terraform plan` com credencial nova pode acusar diferenca no state local.
  Impacto: risco de mexer no state, que nao tem copia. Mitigacao: `plan` e leitura;
  qualquer escrita para e pergunta ao humano (AI_SAFETY, proibicao 1).

## Evidencias de Implementacao

- `python3 -m unittest discover -s tests` — 80 testes, verde
- `python3 scripts/nf_gate.py` — 7 guards conforme
- `terraform validate` — configuration is valid; `terraform fmt -check` limpo
- `python3 scripts/nf_tokens.py --sprint 2` — recorte funcionando, com aviso de
  sobreposicao com a Sprint 1
- `python3 scripts/nf_tokens.py --desde 2026-08-10 --ate 2026-08-11` — 2.233.068
  faturaveis, confirmando o teto de 2.2M registrado na Sprint 2 dentro de 1,7%

## Pendencias para a Proxima Sprint

- Rodar a ingestao keyless num ambiente com Entra ID e fechar 2.1 - sprint alvo: 4
- Superar o ADR-003 depois que 2.1 fechar - sprint alvo: 4
- Desabilitar `local_authentication` no Search e remover a admin key do Key Vault, depois
  de a via keyless estar verificada - sprint alvo: 4
- Backend remoto de Terraform com lock e `prevent_destroy` nos stateful - sprint alvo: 4
- Aceitar ou rejeitar o ADR-005 (decisao humana) - sprint alvo: 3

## Regras

- Validar antes de commitar: `python3 scripts/nf_gate.py`
- Item so recebe `[x]` quando a acao foi realmente executada.
