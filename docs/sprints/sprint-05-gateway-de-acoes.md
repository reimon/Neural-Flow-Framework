# Sprint 5: Gateway de acoes e aprovacao humana

## Snapshot Operacional

- App/Escopo: `neural-flow-framework — gateway de acoes para execucao de agentes`
- Status: `em andamento`
- Data de inicio: `2026-09-22`
- Data planejada de conclusao: `2026-10-06`
- Data real de conclusao: `a definir`
- Ultima atualizacao: `2026-10-12`
- Nivel de autonomia: `A1`
- Blocker principal: `adaptador de sandbox e canal independente de aprovacao ainda pendentes`
- Proxima acao: `implementar e validar os adaptadores antes de habilitar execucao isolada`

> O gateway e uma fronteira de execucao. Acoes desconhecidas sao negadas; acoes
> sensiveis ou irreversiveis exigem aprovacao humana interativa para o comando exato.

## FinOps de Tokens

- Token budget: `500k`
- Limite de alerta: `70%`
- Consumo observado: `em andamento`
- Mitigacao aplicada: `nao se aplica`

## Objetivo

Fazer a politica de autonomia sair do Markdown e chegar a uma fronteira executavel,
auditavel e fail-closed para comandos que um agente tenta rodar.

## Escopo incluido

- Contrato JSON de acoes permitidas, risco, sprint, item e aprovacao.
- Gateway stdlib que valida sprint, allowlist, risco, aprovacao humana e auditoria.
- Interface de sandbox fail-closed; adaptadores macOS/Linux/Windows ainda pendentes.
- Guard de politica integrado ao `nf_gate`, pre-commit, CI e instalador.
- Portas de entrada e documentacao ensinando o gateway como caminho unico de execucao.
- Protecao da branch `main` com checks obrigatorios no GitHub.

## Fora do escopo

- Policy engine externo ou isolamento universal para ferramentas que ignorem o gateway.
- Concessao automatica de permissoes em cloud ou provedores externos.
- Inferir risco de uma acao apenas pelo texto natural da intencao.
- Commit ou push desta mudanca sem autorizacao explicita.

## Checklist de Acoes

### Bloco 1: Contrato e politica

- [x] 1.1 ADR e protocolo do gateway escritos
  - Arquivo(s): `docs/adr/ADR-006-gateway-de-acoes.md`, `docs/adr/ADR-007-sandbox-do-gateway.md`, `docs/protocols/action-gateway.md`
  - Validacao: `python3 scripts/nf_gate.py adr`
  - Evidencia: `python3 scripts/nf_gate.py adr` passou com ADR-006, ADR-007 e protocolo versionado.

- [x] 1.2 Contrato `.neural-flow/action-policy.json` definido
  - Arquivo(s): `scripts/nf_action_policy.py`, `.neural-flow/action-policy.json`
  - Validacao: `python3 scripts/nf_gate.py action`
  - Evidencia: `python3 scripts/validate_action_policy.py` retornou `PASS` para a politica habilitada.

### Bloco 2: Fronteira de execucao

- [x] 2.1 Gateway bloqueia acao desconhecida e exige aprovacao interativa para risco alto
  - Arquivo(s): `scripts/nf_action_gateway.py`
  - Validacao: `python3 -m unittest tests.test_action_gateway`
  - Evidencia: 6 testes focados passaram; com politica `required` sem adaptador validado, o gateway bloqueia.

- [x] 2.2 Gateway registra somente hash do comando, decisao e resultado
  - Arquivo(s): `scripts/nf_action_gateway.py`
  - Validacao: teste de auditoria sem segredo em claro
  - Evidencia: teste focado confirmou auditoria sem segredo ou comando cru em `action-audit.jsonl`.

### Bloco 3: Integracao e operacao

- [x] 3.1 Guard, instalador, portas, diagrama e CI integrados
  - Arquivo(s): `scripts/nf_gate.py`, `scripts/nf_install.py`, `scripts/nf_diagrama.py`
  - Validacao: `python3 -m unittest discover -s tests`
  - Evidencia: `python3 -m unittest discover -s tests -q` passou com 90 testes; `nf_gate` passou com 8 guards.

- [x] 3.2 Branch `main` exige PR, review humano e checks verdes
  - Arquivo(s): configuracao protegida do GitHub
  - Validacao: consulta read-only da protecao e workflow verde
  - Evidencia: API do GitHub confirmou PR obrigatório, 1 review, 3 checks, admins sujeitos a regra,
    sem force push/delecao e com resolucao de conversas; ultimo workflow `success` em `3025ba5`.

## Evidencias de Implementacao

- `2026-10-12`: consolidacao para publicacao autorizada pelo usuario na Sprint 7.
- `2026-10-12`: API do GitHub reconfirmou main protegida, 1 review obrigatorio,
  os 3 checks obrigatorios e administradores sujeitos a regra.
- `2026-10-12`: politica segue em required; nao foi habilitado nem declarado um
  adaptador ausente. A excecao de execucao desta sessao foi registrada na Sprint 7.
- `2026-09-22`: gateway, guard, instalador, artefatos gerados e testes implementados.
- `2026-09-22`: protecao da branch `main` aplicada e verificada pela API do GitHub.
- `2026-09-22`: politica `required` bloqueia ate existir adaptador de isolamento validado.

## Pendencias para a Proxima Sprint

- Integrar o gateway a um executor de ferramentas especifico de cada projeto adotante.
- Substituir a aprovacao interativa por aprovacao assinada quando houver um servico de
  identidade e um canal de aprovacao separado do agente.

## Regras

- Validar antes de commitar: `python3 scripts/nf_gate.py`
- Item so recebe `[x]` quando a acao foi realmente executada.
