# Sprint N: Titulo da Sprint

## Snapshot Operacional

- App/Escopo: `a preencher`
- Status: `planejada`
- Data de inicio: `YYYY-MM-DD`
- Data planejada de conclusao: `YYYY-MM-DD`
- Data real de conclusao: `a preencher`
- Ultima atualizacao: `YYYY-MM-DD`
- Nivel de autonomia: `A1`
- Blocker principal: `nenhum`
- Proxima acao: `a preencher`

> Status permitidos: `planejada` · `em andamento` · `bloqueada` · `concluida` · `cancelada`.
> Status fora dessa lista e FAIL do State Protocol (S2) — ambiguidade nao e estado.
>
> Escopo sensivel (auth, segredos, infra, billing, dados pessoais, producao) opera em
> **A0 ou A1**. A2/A3 nesse escopo so com `Excecao formal` registrada nesta sprint (S4).

## FinOps de Tokens

- Token budget: `a preencher`
- Limite de alerta: `70%`
- Consumo observado: `em andamento`
- Mitigacao aplicada: `nao se aplica`

> Guard: `python scripts/nf_gate.py budget`. Sprint sem budget declarado nao passa (B1);
> sprint concluida sem consumo registrado nao passa (B4); consumo >= 100% do budget sem
> mitigacao nem excecao formal nao passa (B3).

## Objetivo

Descrever em 1 ou 2 paragrafos o resultado esperado da sprint.

## Escopo incluido

- Item 1
- Item 2

## Fora do escopo

- Item 1
- Item 2

## Entregaveis

- [ ] E1. Entregavel principal
- [ ] E2. Entregavel principal

## Checklist de Acoes

### Bloco 1: Tema

- [ ] 1.1 Acao detalhada
  - Arquivo(s): `path/to/file.ts`
  - Validacao: `npm run check`
  - Evidencia: a preencher

- [ ] 1.2 Acao detalhada
  - Arquivo(s): `path/to/file.ts`
  - Dependencia: a preencher
  - Evidencia: a preencher

### Bloco 2: Tema

- [ ] 2.1 Acao detalhada
  - Arquivo(s): `path/to/file.ts`
  - Validacao: teste manual
  - Evidencia: a preencher

## Dependencias Tecnologicas

- Biblioteca/SDK: nome e versao
- Servico externo: nome
- Permissoes: a preencher
- Incompatibilidades conhecidas: nenhuma

## Notas de Seguranca

- Item 1
- Item 2
- Se nao se aplicar, escrever `Nao se aplica`.

## Delta desde a ultima atualizacao

- `YYYY-MM-DD`: resumo curto do que mudou desde a ultima revisao.

## Riscos / Blockers / ETA

- Risco ou blocker atual
- Impacto
- ETA ou proxima revisao

## Evidencias de Implementacao

- `npm run check` executado com sucesso
- Teste manual validado
- Screenshot/log/link de PR/deploy

## Commits Executados

- `abc1234` - `mensagem do commit` - finalidade resumida
- `def5678` - `mensagem do commit` - finalidade resumida

## Resumo das Atividades

| Acao | O que foi feito     | Arquivos alterados       |
| ---- | ------------------- | ------------------------ |
| 1.1  | Descrever resultado | `path/a.ts`, `path/b.ts` |
| 1.2  | Descrever resultado | `path/c.ts`              |

## Pendencias para a Proxima Sprint

- Pendencia 1 - motivo - proxima acao
- Pendencia 2 - motivo - sprint alvo

## Regras

- Seguir o manifesto do projeto (`Manifest-Dev-AI.md`) e os protocolos em `docs/protocols/`.
- Validar antes de commitar: `python scripts/nf_gate.py sprint budget context`.
