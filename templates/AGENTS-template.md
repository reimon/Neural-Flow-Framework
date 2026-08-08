# AGENTS.md — Diretrizes para qualquer agente/LLM neste repositorio

> TEMPLATE Neural-Flow. Copie para a raiz do projeto como `AGENTS.md` e preencha os
> blocos `<...>`. Originado de um padrao validado em producao.

> **Fonte de verdade tool-agnostica.** Vale para **qualquer** LLM/ferramenta
> (Claude Code, Copilot, Cursor, etc.). Os arquivos por-ferramenta (`CLAUDE.md`,
> `.github/copilot-instructions.md`, `.cursorrules`) e as regras de seguranca
> (`.github/AI_SAFETY.md`) **apontam para ca**. Quando uma diretriz arquitetural
> mudar, edite **este** arquivo.
>
> **Principio n. 0:** documentacao orienta, **guard obriga**. Toda diretriz forte
> deve ter um guard automatizado (lint/test/CI) — so assim independe de qual modelo
> leu o que. Diretriz sem guard ainda nao esta "pronta" (ver secao Processo).

---

## 1. Nao reconstruir infraestrutura — mapa de capacidades

**Antes de criar qualquer abstracao, use o que ja existe.** Reimplementar isto e o
erro mais caro (e mais comum) de agentes.

| Precisa de... | Use | NAO faca |
|---|---|---|
| Chamar LLM | `<modulo central de LLM>` | client proprio / SDK direto |
| Auditar/custear LLM | `<mecanismo de audit log>` | tabela/log de metrica nova |
| Acesso a dados | `<camada de repositorio/DAO>` | query crua na camada HTTP |
| Storage | `<helper de storage>` | SDK de storage direto numa rota |
| Auth/RBAC | `<middleware de auth>` | checagem inline |
| `<outra capacidade>` | `<modulo>` | `<anti-padrao>` |

Em duvida sobre se algo ja existe: `grep` em `<diretorios de libs/services>` — ou
consulte `<docs de arquitetura>`.

## 2. Boundaries de camada (guard: lint `error`)

```text
<camada HTTP>  →  <camada de orquestracao>  →  <camada de dados>
               →  <helpers/integracoes>
```

- `<regra de import proibido 1>` → guard: `<regra de lint>`.
- `<regra de import proibido 2>` → guard: `<teste de arquitetura>`.

## 3. Governanca de LLM

- **Toda** chamada LLM passa pelo modulo central com contexto de feature e
  proposito → registro em audit log. Regra de ouro: tudo configuravel/auditavel.
- **Proibido** importar SDK de LLM fora de `<diretorio permitido>` → guard:
  teste de bypass no CI.

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

- `<migrations sequenciais; nunca editar aplicada>`
- `<deploy so via CI; nunca manual>`
- `<outras invariantes: i18n, tenancy, DI...>`

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

- `.github/AI_SAFETY.md` — proibicoes absolutas + acoes que exigem confirmacao.
- `MEMORY.md` — decisoes/padroes consolidados.
- `docs/adr/` — registros de decisao arquitetural (ADRs).
- `docs/Manifest-Dev-AI.md` — manifesto Neural-Flow (gates, sprints, autonomia).
