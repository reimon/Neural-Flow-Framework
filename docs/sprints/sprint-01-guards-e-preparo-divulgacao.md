# Sprint 1: Guards executaveis e preparo para divulgacao

## Snapshot Operacional

- App/Escopo: `neural-flow-framework — protocolos, guards e kit de adocao`
- Status: `em andamento`
- Data de inicio: `2026-08-08`
- Data planejada de conclusao: `2026-08-15`
- Data real de conclusao: `a definir`
- Ultima atualizacao: `2026-08-08`
- Nivel de autonomia: `A1`
- Blocker principal: `nenhum`
- Proxima acao: `revisao humana antes da divulgacao publica`

> Autonomia A1 e obrigatoria aqui: o escopo toca `infra/terraform`, segredos e
> configuracao de autenticacao (ADR-003). O guard S4 reprova A2/A3 neste escopo.

## FinOps de Tokens

- Token budget: `1M`
- Limite de alerta: `70%`
- Consumo observado: `em andamento`
- Mitigacao aplicada: `nao se aplica`

> Consumo real ainda nao medido. O protocolo Spec-First proibe preencher dado ausente com
> valor plausivel — por isso `em andamento`, e nao um numero inventado. B4 exige o registro
> antes de marcar a sprint como `concluida`.

## Objetivo

Transformar o Neural-Flow de conjunto de documentos em framework adotavel: protocolos com
guards executaveis, kit de templates, e o proprio repositorio operando sob as regras que
prega. A sprint prepara a divulgacao publica, mas nao a executa.

## Escopo incluido

- Colheita dos metodos maduros de dois projetos internos como protocolos e templates
- Protocolos 8 (Spec-First), 9 (Loop Autonomo) e 10 (Calibracao)
- Guards executaveis para 6 protocolos, com suite de testes nas duas direcoes
- Dogfood: ADRs e esta sprint dentro do proprio repositorio
- Registro da divida de seguranca admin key vs. RBAC (ADR-003)
- Getting started, versionamento e changelog

## Fora do escopo

- Migracao de `ingest.py`/`search.py`/MCP para `DefaultAzureCredential` (ADR-003)
- Reescrita da implementacao de referencia em Node/pgvector (ADR-001)
- Traducao do framework para ingles
- Publicacao efetiva (anuncio, site, divulgacao em redes)
- Guards para State/Circuit Breaker/Vetor de Contexto alem do que ja foi entregue

## Entregaveis

- [x] E1. Dez protocolos versionados em `docs/protocols/`
- [x] E2. Seis guards executaveis com orquestrador unico
- [x] E3. Suite de testes que prova aprovacao e reprovacao
- [x] E4. Kit de adocao (templates + hook + workflow)

## Checklist de Acoes

### Bloco 1: Colheita e protocolos

- [x] 1.1 Colher praticas de governanca do projeto interno de plataforma
  - Arquivo(s): `templates/AGENTS-template.md`, `templates/AI_SAFETY-template.md`, `templates/MEMORY-template.md`
  - Validacao: revisao manual contra os originais
  - Evidencia: templates generalizados, sem dado especifico do projeto de origem

- [x] 1.2 Colher metodo docs-first do projeto interno docs-first
  - Arquivo(s): `docs/protocols/spec-first.md`, `docs/protocols/autonomous-loop.md`, `templates/loop/`
  - Validacao: revisao manual contra `METODO.md` e `build/PROTOCOLO.md` de origem
  - Evidencia: protocolos 8 e 9 versionados

- [x] 1.3 Criar protocolo de Calibracao e Incerteza
  - Arquivo(s): `docs/protocols/calibration.md`
  - Validacao: `python scripts/nf_gate.py calibration`
  - Evidencia: ADR-004

### Bloco 2: Guards executaveis

- [x] 2.1 Guard de Calibracao (C1-C6)
  - Arquivo(s): `scripts/validate_calibration.py`
  - Validacao: `python -m unittest discover -s tests`
  - Evidencia: 17 testes verdes

- [x] 2.2 Guards de State Protocol, Circuit Breaker, Vetor de Contexto, ADR e Spec-First
  - Arquivo(s): `scripts/validate_sprint_state.py`, `scripts/validate_token_budget.py`, `scripts/validate_context_sources.py`, `scripts/validate_adr.py`, `scripts/validate_module_spec.py`
  - Validacao: `python scripts/nf_gate.py`
  - Evidencia: 6 guards conforme neste repositorio

- [x] 2.3 Orquestrador e helpers compartilhados
  - Arquivo(s): `scripts/nf_gate.py`, `scripts/nf_guards.py`
  - Validacao: `python scripts/nf_gate.py --list`
  - Evidencia: duplicacao de parsing eliminada entre validadores

### Bloco 3: Prova e dogfood

- [x] 3.1 Suite de testes com fixtures conforme e violadora
  - Arquivo(s): `tests/test_guards.py`, `tests/fixtures/`
  - Validacao: `python -m unittest discover -s tests`
  - Evidencia: 17 testes; a suite encontrou 2 bugs reais nos guards (titulo de secao numerado; escopo do check V2)

- [x] 3.2 CI que prova reprovacao, nao so aprovacao
  - Arquivo(s): `.github/workflows/neural-flow-gates.yml`
  - Validacao: simulacao local dos dois jobs
  - Evidencia: job `testes` falha se a fixture violadora for aprovada

- [x] 3.3 Dogfood: ADRs e sprint no proprio repositorio
  - Arquivo(s): `docs/adr/ADR-001..004`, este arquivo
  - Validacao: `python scripts/nf_gate.py`
  - Evidencia: guards `adr` e `sprint` validando artefatos reais em vez de "nada a validar"

### Bloco 4: Preparo de divulgacao

- [x] 4.1 Registrar divida de seguranca admin key vs. RBAC
  - Arquivo(s): `docs/adr/ADR-003-divida-admin-key-vs-rbac.md`
  - Validacao: `python scripts/nf_gate.py adr`
  - Evidencia: ADR-003 aceito, com guard declarado aspiracional

- [x] 4.2 Getting started de 5 minutos
  - Arquivo(s): `docs/GETTING-STARTED.md`
  - Validacao: caminho executado do zero em diretorio temporario
  - Evidencia: hook bloqueando e liberando commit conforme o estado do artefato

- [x] 4.3 Versionamento e changelog
  - Arquivo(s): `VERSION`, `CHANGELOG.md`
  - Validacao: leitura manual
  - Evidencia: v0.1.0 descrita com os 10 protocolos e 6 guards

## Dependencias Tecnologicas

- Python 3.10+ (stdlib apenas — ver ADR-002)
- git 2.x (o hook usa `git checkout-index`)
- Opcional: `github:reimon/smoke-gate#v0.5.0` para o gate de Evidencia Sintetica
- Opcional: Azure AI Search + Azure OpenAI para a implementacao de referencia de RAG

## Notas de Seguranca

- Nenhum segredo versionado: `scripts/.env` e `infra/terraform/*.tfstate` no `.gitignore`;
  `scripts/.env.example` contem apenas placeholders.
- Divida conhecida e declarada: admin key em vez de Entra ID/RBAC (ADR-003).
- `infra/terraform/tfplan` foi removido e adicionado ao `.gitignore` — plan pode conter
  valores sensiveis.

## Delta desde a ultima atualizacao

- `2026-08-08`: guards dos quatro protocolos aspiracionais entregues; suite de testes
  criada e ja pegou 2 bugs; dogfood do repositorio concluido.

## Riscos / Blockers / ETA

- Risco: adotante copia `ingest.py` sem ler ADR-003 e herda o uso de admin key.
  Impacto: pratica de seguranca ruim propagada. Mitigacao: aviso no README e no ADR.
- Risco: guards baseados em regex toleram pouca variacao de formato markdown.
  Impacto: falso positivo em projeto com formatacao divergente. Mitigacao: `.neural-flow.json`
  e fixtures de regressao.

## Evidencias de Implementacao

- `python -m unittest discover -s tests` — 17 testes, verde
- `python scripts/nf_gate.py` — 6 guards conforme neste repositorio
- `python scripts/nf_gate.py --root tests/fixtures/violador` — sai 1, como esperado
- Teste ponta a ponta com repositorio git real: hook bloqueou commit de sprint em A3 com
  escopo sensivel e liberou apos correcao para A1
- Bugs encontrados pelos proprios guards em `docs/SPRINTS-MVP.md`: nome de manifesto grafado
  com "Dev-IA" em vez de "Dev-AI" (8 ocorrencias) e referencia a um prompt de governanca
  inexistente — ambos corrigidos

## Pendencias para a Proxima Sprint

- Medir e registrar o consumo real de tokens desta sprint - exigido por B4 antes de marcar `concluida`
- Migrar autenticacao Azure para Entra ID/RBAC - ADR-003 - sprint alvo: 2
- Avaliar traducao do framework para ingles - decisao de alcance - sprint alvo: a definir

## Regras

- Seguir `docs/Manifest-Dev-AI.md`
