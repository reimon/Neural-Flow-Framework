# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).
Versionamento semantico: a versao descreve o **contrato de adocao** (protocolos, codigos
de guard, formato dos templates), nao o volume de documentacao.

Regra de compatibilidade:

- **MAJOR** — codigo de guard removido ou com significado alterado; campo obrigatorio novo
  em template ja publicado; protocolo removido. Quebra projeto que ja adotou.
- **MINOR** — protocolo, guard, codigo de verificacao ou template novo. Projeto existente
  continua passando.
- **PATCH** — correcao de falso positivo/negativo, mensagem, documentacao.

Ao copiar templates para um projeto, anote a versao de origem: e o que permite saber, mais
tarde, de qual geracao veio o `AGENTS.md` que esta la.

---

## [Nao publicado]

### Adicionado

- `install.sh` + `scripts/nf_install.py` — instalador com deteccao de modo
  (greenfield/brownfield), idempotente, que nao sobrescreve nada e se auto-valida
  rodando `nf_gate` no projeto gerado.
- `templates/CLAUDE-template.md` — principios de execucao (Karpathy) amarrados aos
  protocolos que os tornam verificaveis. Instalado nos dois modos.
- smoke-gate resolvido na **versao mais recente** a cada instalacao (tags via API),
  com `--smoke-gate-ref` para congelar ou acompanhar `main`.
- `scripts/nf_dashboard.py` — dashboard HTML auto-contido (sem CDN, sem JS de terceiros)
  com sprint ativa, guards, FinOps de tokens, smoke-gate, indice de conhecimento, loop e
  protocolos. Paleta validada por script nos modos claro e escuro; status sempre com
  icone + rotulo. Instalado por padrao.
- Leitor do **Codex** na telemetria (`~/.codex/sessions`), com filtro por projeto via `cwd`
  e normalizacao do vocabulario da OpenAI. Dashboard e CLI mostram a divisao por provedor.
- Mapa de calor de ritmo (hora x dia), ferramentas mais usadas e sessoes por consumo.
- Graficos em SVG desenhados a mao, sem biblioteca: area com endpoint destacado para serie
  temporal, anel para proporcao unica, rampa sequencial com passos proprios por tema.
- `scripts/nf_tokens.py` — telemetria real de tokens lida dos transcripts locais do Claude
  Code (entrada, saida, cache, por modelo e por dia, aproveitamento de cache). O dashboard
  passa a mostrar medido x declarado. Le apenas numeros; nunca o conteudo das mensagens.
- Ajuda contextual no dashboard: botao `?` em cada quadro, protocolo e indicador, abrindo
  janela com `popover` nativo — sem JavaScript, preservando a auto-contencao.
- Dashboard linka os artefatos do graphify (`graph.html`, wiki, `GRAPH_REPORT.md`) com
  caminho relativo a saida e o tamanho de cada um; estado vazio explica como gerar.
- `docs/dashboard-demo.html` — demonstracao versionada, gerada de `tests/fixtures/demo/`
  com `--gerado-em` para saida reproduzivel. Um teste regenera e compara: a demo nao pode
  divergir do gerador.

### Corrigido

- `scripts/setup-hooks.sh`: interpretador `python` fixo, mascaramento de falha e
  instalacao em `.git/hooks` com `core.hooksPath` ativo (hook morto).
- Guard `calibration` nao ignorava blocos de codigo — o arquivo que documenta o formato
  era lido como se cada exemplo fosse divergencia pendente.
- Workflow de reindex falhava sem os segredos do indice, deixando badge vermelho cronico
  em fork e em projeto sem a implementacao de referencia Azure. Agora pula com aviso.

---

## [0.1.0] — 2026-08-08

Primeira versao publica.

### Protocolos (10)

- **State Protocol** — nenhuma execucao sem sprint validada
- **Circuit Breaker de Tokens** — orcamento declarado e disjuntor de custo
- **Vetor de Contexto** — decisao ancorada em fonte; indice antes de leitura; selecao de
  ferramenta por classe de pergunta
- **Evidencia Sintetica** — verde e a unica condicao para marcar pronto
- **Aegis** — classificacao de dado e zero segredo
- **Neural-Memory** — recuperacao semantica em vez de leitura linear; backend-agnostico
  (ver ADR-001)
- **ADR Governance** — decisao arquitetural numerada, imutavel, auditavel
- **Spec-First** — especificar e passar em gate antes de codificar
- **Loop Autonomo** — execucao prolongada com estado em disco
- **Calibracao e Incerteza** — confianca derivada da classe de evidencia (ver ADR-004)

### Guards executaveis (6)

Python 3.10+ stdlib puro, orquestrados por `scripts/nf_gate.py` (ver ADR-002).

| Guard | Codigos |
| --- | --- |
| `sprint` | S1-S6 |
| `budget` | B1-B4 |
| `context` | V1-V3 |
| `adr` | A1-A6 |
| `spec` | P1-P4 |
| `calibration` | C1-C6 |

### Kit de adocao

- Templates: `AGENTS`, `AI_SAFETY`, `MEMORY`, `adr`, `sprint`, `spec-modulo`,
  `playbook-rollback`, `runbook-incidente`, `loop/` (5 arquivos)
- Hook de pre-commit que valida **o stage**, nao a arvore de trabalho
- Workflow de CI que prova aprovacao **e** reprovacao
- `docs/GETTING-STARTED.md` — adocao em 5 minutos

### Qualidade

- 23 testes (`python -m unittest discover -s tests`) cobrindo as duas direcoes: fixture
  conforme aprovada, fixture violadora reprovada com os codigos esperados
- CI em Python 3.10 e 3.12

### Divida conhecida

- A implementacao de referencia Azure usa admin key em vez de Entra ID/RBAC — declarada em
  `docs/adr/ADR-003-divida-admin-key-vs-rbac.md`. Nenhum protocolo, template ou guard
  depende dela.
- Sem guard executavel: Loop Autonomo (parcial, via C1-C3), Neural-Memory (parcial, via
  reindex no CI) e Aegis (depende de scanner do projeto). Declarados como tal em
  `docs/protocols/README.md`.

### Bugs corrigidos durante a construcao (encontrados pelos proprios guards e testes)

- `secao()` nao reconhecia titulo numerado (`## 1. Titulo`) — quebrava o guard `spec` em
  toda spec que usasse o formato do proprio template
- V2 exigia a fonte dentro da secao "Decisao"; num ADR as fontes vivem em
  Contexto/Evidencia — falso positivo de escopo
- B2 rejeitava `` `em andamento` `` por causa das crases do template — falso positivo em
  toda sprint aberta
- **S4 e B3 eram desligados pelo texto explicativo do proprio template**: procuravam
  "excecao formal"/"mitigacao" em qualquer lugar do documento. Agora exigem campo com
  conteudo real
- V1 acusava caminhos prospectivos do projeto adotante — passou a so cobrar referencia
  cujo diretorio-pai existe
- `sprint-template.md` referenciava `../../docs/Manifest-Dev-AI.md`, caminho valido apenas
  no repositorio de origem — bloqueava o primeiro commit de quem seguisse o guia
- Typo `Manifest-Dev-IA.md` (8 ocorrencias) e referencia a prompt inexistente em
  `docs/SPRINTS-MVP.md`
- `scripts/setup-hooks.sh` gerava um post-commit com tres defeitos: chamava `python`
  (ausente no macOS moderno e em distros sem python-is-python3); mascarava qualquer
  falha com `|| echo "(non-blocking)"`, de modo que o indice nunca era atualizado e
  ninguem percebia; e instalava em `.git/hooks` mesmo com `core.hooksPath` configurado —
  diretorio que o git ignora nesse caso, entao o hook nunca rodava para quem seguia o
  getting-started
