# AGENTS.md — Diretrizes para qualquer agente/LLM neste repositorio

> **Fonte de verdade tool-agnostica deste repositorio.** As portas de entrada
> (`CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`, `.cursor/rules/`,
> `.clinerules`, `.windsurfrules`, `AGENT.md`, `CONVENTIONS.md`, `HERMES.md`) apontam
> para ca e **nao devem ser editadas** — sao geradas de `scripts/nf_agentes.py`.
> Mudou uma diretriz? Edite **este** arquivo e regere.
>
> **Principio n. 0:** documentacao orienta, **guard obriga**. Diretriz sem guard nao
> esta pronta. Este repositorio e o framework: aqui, isso e literal.

---

## 1. Nao reconstruir infraestrutura — mapa de capacidades

**Antes de criar qualquer abstracao, use o que ja existe.** Reimplementar isto e o
erro mais caro (e mais comum) de agentes.

| Precisa de... | Use | NAO faca |
|---|---|---|
| Parsing de markdown num guard | `scripts/nf_guards.py` (`secao`, `campos`, `ler`, `numero`, `eh_placeholder`) | regex propria dentro do validador |
| Reportar resultado de guard | `Resultado` + `relatar()` de `nf_guards` | `print` e `sys.exit` a mao |
| Registrar um guard novo | dicionario `GUARDS` em `scripts/nf_gate.py` | chamar o validador direto no hook ou no CI |
| Texto de porta de entrada de agente | `scripts/nf_agentes.py` (`PORTAS`, `corpo()`) | escrever `GEMINI.md` e afins a mao |
| Indice de regras | `scripts/nf_indice_regras.py` | resumir as regras num arquivo novo |
| Escrever arquivo no projeto alvo | `Instalacao.escrever` / `copiar_template` | `write_text` direto no instalador |
| Telemetria de tokens por provedor | `scripts/nf_tokens.py` | novo leitor de transcript |
| Pagina de estado da governanca | `scripts/nf_dashboard.py` | segundo gerador de HTML |
| Diagrama de arquitetura | `scripts/nf_diagrama.py` (le o registro de guards) | SVG editado a mao |

Em duvida sobre se algo ja existe: comece por `.neural-flow/indice-regras.md`, depois
`README.md` (tabela do kit de adocao) e `docs/protocols/README.md`.

## 2. Boundaries de camada

```text
nf_gate.py  →  validate_*.py  →  nf_guards.py
nf_install.py  →  templates/ + nf_agentes.py + nf_indice_regras.py
```

- **Guard nao importa guard.** Logica compartilhada desce para `nf_guards.py` — duplicar
  parsing foi o vetor que ja propagou uma forma errada para dezenas de arquivos.
- **Nada fora da stdlib**, em nenhum script instalado no projeto alvo (ADR-002) → guard:
  `tests/test_guards.py` roda os validadores num ambiente limpo.
- **Todo script instalavel carrega `NF_GUARD_ASSINATURA`** — sem ela o `nf_gate` se recusa
  a executar o arquivo, para nao chamar um homonimo do projeto com os nossos argumentos.
- O instalador **nunca sobrescreve** artefato existente sem `--force`; colisao vira
  instalacao lado a lado (`nf_<nome>`) ou anexo, sempre com aviso.

## 3. Governanca do proprio framework

- **Guard novo entra pelo `GUARDS` do `nf_gate`** e ganha, no mesmo commit: protocolo em
  `docs/protocols/`, testes nas duas direcoes (conforme e violador) e entrada no diagrama.
- **Ausencia de artefato = exit 0.** Nenhum guard reprova projeto que ainda nao tem o
  artefato que ele valida — instalar o framework nao pode bloquear o primeiro commit.
- **Artefato instalado nao pode nascer invisivel para o gate**: o cabecalho
  `> TEMPLATE Neural-Flow` desliga a validacao, entao template vai para o projeto via
  `copiar_template` → guard: `test_nenhum_artefato_nasce_invisivel_para_o_gate`.
- **O instalador escreve na arvore de terceiros.** Mudanca ali opera em A1 e so fecha com
  instalacao ponta a ponta executada, nunca com leitura do diff.

## 4. Validacao antes de afirmar "pronto"

- Typecheck **e build** (typecheck sozinho nao pega import orfao de arquivo movido).
- Lint + testes do dominio alterado.
- Mover arquivo: grep dos importadores relativos E absolutos antes; 0 orfaos depois.
- **Se e barato executar, nao opine.** Comando que resolve em segundos nao vira paragrafo
  de argumentacao.

### 4.1 Confianca declarada (protocolo Calibracao)

Toda conclusao tecnica declara nivel e fonte. O nivel nao e escolhido — e **lido** da
classe de evidencia:

| Nivel | Autorizado por | Pode fechar item? |
| --- | --- | --- |
| ALTA | Execucao verificada (teste verde, comando rodado, artefato inspecionado) | Sim |
| MEDIA | Fonte documental vigente (spec, ADR aceito, contrato versionado) | Nao, se o criterio exige execucao |
| BAIXA | Inferencia, analogia, padrao "que costuma ser assim" | **Nunca** |

Formato: `Confianca: <NIVEL> — <classe de evidencia + referencia>`

Regras: cadeia com um elo inferido e conclusao inferida (vale o menor nivel); repetir uma
inferencia **nao** a promove. `BAIXA` obriga um degrau a mais de prova antes de responder —
buscar fonte e, se for executavel, executar.

### 4.2 Quando reconsultar / quando perguntar

- Indice devolveu resultado fraco ⇒ **reformule** a consulta antes de escalar para
  varredura. Segunda reformulacao sem resultado ⇒ registre lacuna de contexto.
- Fontes se contradizem ⇒ nao escolha a conveniente: acione `check_contradiction`.
- `BAIXA` **e** acao irreversivel (perder dado, expor dado pessoal, gastar dinheiro, mexer
  em producao) ⇒ **pare e pergunte**.
- `BAIXA` e acao reversivel ⇒ siga conservador e registre a divergencia. Nao pergunte.
- Nao pergunte o que a spec ja responde — isso e falha de leitura, nao prudencia.

### 4.3 Ferramenta certa por classe de pergunta

Estrutura/relacao ⇒ grafo. Historico/decisao ⇒ RAG + ADR. Texto exato ⇒ leitura do arquivo
que o indice apontou. Comportamento ⇒ **executar**. Estado do trabalho ⇒ disco. Localizar
literal conhecido ⇒ `grep`. **`grep` para "entender" e anti-padrao** — custa ~48x mais
tokens que a consulta ao indice.

## 5. Regras fixas do projeto

- **Portugues sem acentos** em codigo, comentarios e artefatos de governanca — os guards
  comparam texto normalizado, e acento inconsistente vira falso negativo.
- **Nada de dependencia externa** nos scripts que o instalador copia (ADR-002).
- **Numeracao de ADR e sequencial e nunca reutilizada**; ADR aceito e imutavel — mudanca
  de rumo gera ADR que o supera → guard: `nf_gate.py adr`.
- **Sprint numerada nao se duplica**: uma sprint por numero, em `docs/sprints/`.
- **`docs/img/arquitetura.svg` e `docs/dashboard-demo.html` sao gerados** — regenere com
  `nf_diagrama.py` / `nf_dashboard.py` → guard: testes de "esta atualizado".
- **Imagem de tema nao entra no repositorio** (licenciamento) — ver `.gitignore`.

## 6. Git (regra fixa do usuario)

- **Nunca commitar ou dar push sem autorizacao explicita.**
- Mensagem de commit segue o padrao `Sprint N - <descricao>` (Neural-Flow).
- Stage apenas os proprios arquivos — nunca o WIP de outra sessao/terminal.

## 7. Processo — "diretriz nao esta pronta sem guard"

Ao estabelecer uma regra arquitetural nova, entregue **junto** o guard que a faz
cumprir:

- Boundary de import / API banida → lint `no-restricted-imports`/`no-restricted-syntax`.
- Invariante estrutural → teste de *architecture fitness* no CI.
- Drift SQL/schema, IDOR, error leak, endpoint sem cobertura → `smoke-gate`
  (`github:reimon/smoke-gate#v0.5.0`): `npx smoke-gate audit --since origin/main`
  no PR + Action com `fail-on: critical`. Agente valida SQL antes de gerar via MCP
  `audit_check_sql`.
- O que nao da para lintar → code review ancorado no mapa de capacidades (secao 1).

**Estender guards existentes, nao duplicar.**

## 8. Documentos de referencia

- `.neural-flow/indice-regras.md` — **comece aqui**: uma linha por regra, com fonte e guard.
- `.github/AI_SAFETY.md` — proibicoes absolutas + acoes que exigem confirmacao.
- `MEMORY.md` — decisoes/padroes consolidados.
- `docs/adr/` — registros de decisao arquitetural (ADRs).
- `docs/protocols/` — os protocolos e o gate primario de cada um.
- `docs/sprints/` — sprints; nenhuma execucao comeca sem uma validada.
- `docs/Manifest-Dev-AI.md` — manifesto (gates, sprints, niveis de autonomia).
