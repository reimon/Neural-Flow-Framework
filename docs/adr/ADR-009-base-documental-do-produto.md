# ADR-009 — Base documental do produto antes da implementacao

## Status

Aceito (Sprint 6)

## Contexto

As sprints precisam de um contrato comum sobre produto, arquitetura, jornadas, interface,
backend e sequencia de construcao. Hoje o Spec-First cobre modulos, mas o instalador nao
mostra de forma unificada quais documentos do produto existem nem permite consultar os
modelos oficiais dentro do dashboard.

## Decisao

Adotar seis papeis documentais padronizados: PRD, TRD, Fluxo do App, UI/UX Design,
Esquema Backend e Plano de Implementacao. Cada projeto pode mapear arquivos e secoes
existentes em `.neural-flow.json`; o framework nao renomeia nem sobrescreve esses arquivos.

O instalador instala os modelos oficiais separados, gera o diagnostico e o dashboard. A
revisao semantica cabe ao agente em uso; a liberacao exige aprovacao explicita do usuario
vinculada a hash do documento. A justificativa para papel nao aplicavel tambem e revisada
e registrada.

O guard Spec-First valida IDs e sequencia do plano quando a base estiver preenchida. O
State Protocol bloqueia sprint de implementacao em andamento sem os seis papeis vigentes.
Sprints de preparacao documental continuam permitidas. O acompanhamento de execucao fica
separado do Plano de Implementacao aprovado.

## Consequencias

Positivas:

- a instalacao revela lacunas e mostra os modelos sem abrir outros arquivos;
- os seis contratos se relacionam a itens de implementacao e sprints;
- documento alterado apos revisao precisa de nova aprovacao;
- novos projetos adotam a regra, e projetos existentes entram quando habilitam a opcao.

Trade-offs:

- verificacao automatica cobre estrutura, IDs, referencias, sequencia e hash, nao verdade
  do dominio nem conformidade do codigo;
- nome de revisor e evidencia registrada dependem do processo de identidade do projeto e
  nao sao assinatura criptografica;
- custos do TRD dependem de premissas, volume e fontes declaradas.

## Evidencia (Neural-Flow)

- Sprint de origem: `Sprint 6`
- Guard associado: `python3 scripts/nf_gate.py spec sprint`
- Protocolo: `docs/protocols/product-documentation.md`
- Codigo e testes: `scripts/nf_product_docs.py`, `scripts/nf_dashboard.py`,
  `scripts/validate_module_spec.py`, `scripts/validate_sprint_state.py` e
  `tests/test_guards.py`
