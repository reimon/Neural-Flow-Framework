# Project Memory: Neural-Flow-Framework

**Ultima validacao deste arquivo:** 11-08-2026

> Decisoes, padroes e estado consolidado deste repositorio. Consulte **antes** de sugerir
> solucao; atualize sempre que um padrao novo for definido ou um problema complexo for
> resolvido. Decisao arquitetural maior vira ADR em `docs/adr/` e e apenas referenciada
> aqui. Nunca registrar segredo neste arquivo.

## 0. Delivery Workflow (Sprints + Checklists)

- **Modelo obrigatorio de execucao:** todo desenvolvimento organizado por sprints numeradas.
- **Formato da sprint:** checklist de acoes executaveis (ver `templates/sprint-template.md`).
- **Regra de marcacao:** item so recebe `[x]` quando a acao foi **realmente executada**.
- **Padrao de commit:** toda mensagem comeca com `Sprint N - <descricao>`.
- **Historico continuo:** o checklist por sprint e a fonte de verdade do progresso.

## 1. Architecture and Tech Stack

- **O produto sao os artefatos.** Nao ha aplicacao, frontend nem banco: o entregavel e o
  conjunto protocolos + guards + templates + instalador que outro projeto adota.
- **Guards:** Python 3.10+ **stdlib pura** (ADR-002), orquestrados por `scripts/nf_gate.py`.
  Helpers compartilhados em `scripts/nf_guards.py`; validadores nao duplicam parsing.
- **Instalador:** `install.sh` (wrapper bash) → `scripts/nf_install.py`. Detecta
  greenfield/brownfield, e idempotente e nunca sobrescreve sem `--force`.
- **Governanca de agente:** `AGENTS.md` e a fonte de verdade; as portas por ferramenta sao
  **geradas** de `scripts/nf_agentes.py`; `scripts/nf_indice_regras.py` produz o indice que
  o agente le antes de tudo.
- **Implementacao de referencia (opcional):** Azure AI Search + Azure OpenAI —
  `scripts/ingest.py`, `scripts/search.py`, `mcp/neural-memory-server/`,
  `infra/terraform/`. E referencia, **nao** requisito (ADR-001).
- **CI:** `.github/workflows/neural-flow-gates.yml` — testes em 3.10 e 3.12, prova de
  reprovacao (fixture violadora sai 1), prova de aprovacao (fixture conforme sai 0) e
  dogfood (o gate sobre este repositorio). `reindex.yml` cuida da ingestao Neural-Memory.
- **Hook local:** `core.hooksPath=.githooks`; o pre-commit roda o gate sobre o **stage**.

## 2. Critical Decisions and Code Patterns

### Guards

- **Ausencia de artefato = PASS (exit 0)** — o guard trava quem usa o protocolo errado,
  nao quem ainda nao o usa. Instalar o framework nao pode bloquear o primeiro commit.
  ADR-002; referencia: qualquer `validate_*.py`.
- **Toda diretriz forte tem guard** (principio n. 0). Guard novo entra pelo dicionario
  `GUARDS` de `nf_gate.py` e chega com protocolo em `docs/protocols/`, testes nas duas
  direcoes e entrada no diagrama — no mesmo commit.
- **`NF_GUARD_ASSINATURA` em todo script instalavel.** Sem a assinatura o `nf_gate` se
  recusa a executar o arquivo: projeto brownfield pode ter homonimo com outra interface.
  Referencia: `nf_gate.eh_nosso()`.
- **Codigos de verificacao sao contrato** (S1, B4, V3, A6, P1...). Remover um ou mudar o
  seu significado e MAJOR — quebra projeto que ja adotou.

### Governanca de agente

- **Uma fonte, muitas portas.** Diretriz mora so em `AGENTS.md`; as portas por ferramenta
  sao geradas do corpo canonico e **nao se editam**. Nove copias divergem na terceira
  edicao, e a partir dai cada agente segue uma versao diferente do projeto.
  Referencia: `scripts/nf_agentes.py`, protocolo `docs/protocols/agent-entrypoints.md`.
- **Indice antes de leitura.** `.neural-flow/indice-regras.md` e deterministico e nao
  depende de LLM nem de rede; o grafo do `graphify` e a camada de cima, nao o
  pre-requisito. Referencia: `scripts/nf_indice_regras.py`.

### Instalador

- **Nunca sobrescrever trabalho do adotante.** Colisao de script vira instalacao lado a
  lado (`nf_<nome>`); porta de entrada que ja existia recebe as diretrizes **anexadas**.
  Sempre com aviso no relatorio.
- **Template vai para o projeto via `copiar_template`**, nunca `read_text` direto: o
  cabecalho `> TEMPLATE Neural-Flow` desliga `eh_template()` e faz o artefato nascer
  invisivel para o gate.
- **Versao do smoke-gate e resolvida na instalacao e gravada no projeto** — referencia
  flutuante faria o mesmo commit auditar diferente em dias diferentes.
- **A instalacao se auto-valida:** o instalador roda o gate ao final e sai 1 se o que ele
  proprio escreveu nao passa.

### Autenticacao Azure (implementacao de referencia)

- **Keyless por padrao, chave so por opt-in explicito.** `scripts/nf_azure_auth.py`
  centraliza a decisao para `ingest.py`, `search.py` e o servidor MCP. `NF_AZURE_AUTH=key`
  volta a admin key e avisa em toda execucao. **Sem fallback automatico**: cair na chave
  sozinho quando o RBAC falha converteria um erro de permissao, que se conserta, em
  dependencia permanente de segredo, que ninguem mais ve. ADR-003.

### Terraform

- **`prevent_destroy` nos cinco recursos que nao se recriam sem perda:**
  `random_string.suffix` (todo nome deriva dele), resource group, Search (recriar apaga o
  indice), OpenAI (muda endpoint) e Key Vault (`purge_protection` desligado). Transforma
  a proibicao escrita no `AI_SAFETY` em erro de plan.
- **State local, sem copia e sem lock** e o risco aberto mais serio da infra. O caminho
  para o backend remoto esta em `infra/terraform/backend.tf.exemplo`, com extensao inerte
  de proposito: ativar backend nao e editar arquivo, e migrar state.

### Escrita

- **Portugues sem acento** em codigo, comentarios e artefatos de governanca — os guards
  comparam texto normalizado.
- **Artefato gerado nao se edita a mao:** `docs/img/arquitetura.svg`,
  `docs/dashboard-demo.html`, `.neural-flow/indice-regras.*` e as portas de entrada.

## 3. Modulos principais

| Modulo | Onde vive | Estado |
| --- | --- | --- |
| Protocolos | `docs/protocols/` (10 nucleares + `agent-entrypoints`) | versionados |
| Guards | `scripts/nf_gate.py` + 7 validadores | 7 guards, 80 testes verdes |
| Kit de adocao | `templates/` | AGENTS, CLAUDE, AI_SAFETY, MEMORY, ADR, sprint, spec, loop, hook |
| Instalador | `install.sh`, `scripts/nf_install.py` | greenfield + brownfield, auto-validado |
| Portas de agente | `scripts/nf_agentes.py` | 8 portas geradas + `AGENTS.md` + `CLAUDE.md` |
| Indice de regras | `scripts/nf_indice_regras.py` | deterministico, stdlib pura |
| Observabilidade | `nf_dashboard.py`, `nf_tokens.py`, `nf_diagrama.py` | HTML auto-contido; telemetria Claude + Codex |
| Neural-Memory (referencia) | `scripts/ingest.py`, `search.py`, `mcp/`, `infra/terraform/` | Azure; divida de auth em ADR-003 |

## 4. Solutions Log and Lessons Learned

> _AI Instruction: adicionar abaixo padroes descobertos e bugs complexos resolvidos, para
> nao repetir os mesmos erros._

- **[2026-08-11] - MEMORY.md nascia invisivel para o gate:** o instalador copiava
  `templates/MEMORY-template.md` com `read_text` direto, levando o cabecalho
  `> TEMPLATE Neural-Flow` para o projeto do adotante; `eh_template()` entao desligava
  todos os guards sobre o arquivo e o gate passava sem validar nada. Causa raiz: um
  caminho de copia que escapava do helper `copiar_template`, que existe exatamente para
  isso. Padrao adotado: todo template passa pelo helper, e o teste
  `test_nenhum_artefato_nasce_invisivel_para_o_gate` varre **todos** os `.md` instalados —
  a regressao nao volta por outro arquivo.
- **[2026-08-11] - A governanca cobria um agente so:** o instalador escrevia `CLAUDE.md` e
  mais nada, entao Gemini, Copilot, Cursor, Cline, Windsurf, Amp, Aider e Hermes entravam
  no projeto sem diretriz nenhuma. Causa raiz: confundir "fonte de verdade unica" com
  "arquivo unico" — a fonte e uma, mas cada ferramenta le uma porta diferente. Padrao
  adotado: corpo canonico em `nf_agentes.py`, portas geradas dele, e o guard `agentes`
  travando divergencia.
- **[2026-08-10] - Colisao com o validador do proprio adotante:** projeto brownfield tinha
  `scripts/validate_module_spec.py` com interface propria; o gate o chamava com os nossos
  argumentos e o erro parecia defeito do framework. Causa raiz: duas decisoes certas
  (nao sobrescrever + rodar o guard) que juntas quebram. Padrao adotado:
  `NF_GUARD_ASSINATURA` + instalacao lado a lado + `.neural-flow.json` para apontar o
  comando do projeto.
- **[2026-08-08] - Os guards acharam bugs na propria documentacao:** ao rodar o gate sobre
  este repositorio, "Dev-IA" em vez de "Dev-AI" (8 ocorrencias) e uma referencia a arquivo
  inexistente. Licao: dogfood nao e cerimonia — foi o que encontrou os defeitos.

Regras deste log:

- Sempre datar (data absoluta, nunca relativa).
- Registrar a causa raiz e o padrao correto, nao so o sintoma.
- Se a licao implica regra permanente, promover para a secao 2, `AGENTS.md` (com guard) ou
  ADR — e deixar aqui apenas o registro historico.

## 5. Pendencias ativas

- [ ] **Rodar `python3 scripts/nf_azure_smoke.py` num ambiente autenticado** - trava o
      bloco 2 inteiro da Sprint 4; exige `az login`, nao ha como agente sem tenant fechar
      - sprint alvo: 4, item 1.2
- [ ] Superar o ADR-003 depois da verificacao - sprint alvo: 4, item 2.2
- [ ] Desabilitar `local_authentication` no Search e remover a admin key do Key Vault,
      depois da via keyless verificada - sprint alvo: 4, item 2.3
- [ ] Migrar o state do Terraform para backend remoto - runbook em
      `infra/terraform/backend.tf.exemplo`; operacao com o humano presente - sprint alvo: 4
- [ ] Aceitar ou rejeitar o ADR-005 (grafo do graphify) - decisao humana - sprint alvo: 3
- [ ] Avaliar traducao do framework para ingles - sprint alvo: a definir

## 6. Documentos de referencia

- `.neural-flow/indice-regras.md` — indice das regras, com fonte e guard de cada uma
- `AGENTS.md` — diretrizes arquiteturais (fonte de verdade)
- `.github/AI_SAFETY.md` — proibicoes absolutas e o que exige confirmacao
- `docs/adr/` — ADR-001 memoria backend-agnostica · ADR-002 guards em stdlib pura ·
  ADR-003 divida admin key vs. RBAC · ADR-004 protocolo de Calibracao
- `docs/protocols/README.md` — matriz de protocolos e o gate primario de cada um
- `docs/Manifest-Dev-AI.md` — manifesto (gates, sprints, niveis de autonomia)
