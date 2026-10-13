# Sprint 6: Base documental do produto

## Snapshot Operacional

- App/Escopo: `framework — diagnostico dos seis documentos e exemplos no dashboard`
- Status: `em andamento`
- Data de inicio: `2026-09-27`
- Data planejada de conclusao: `2026-10-11`
- Data real de conclusao: `a definir`
- Ultima atualizacao: `2026-10-12`
- Nivel de autonomia: `A1`
- Blocker principal: `consumo especifico da sprint ainda nao registrado`
- Proxima acao: `registrar o consumo observado da sprint e concluir a revisao visual na Sprint 7`

## FinOps de Tokens

- Token budget: `500k`
- Limite de alerta: `70%`
- Consumo observado: `em andamento`
- Mitigacao aplicada: `nao se aplica`

## Objetivo

Instalar uma base documental com seis papeis, comparar projetos brownfield sem sobrescrever
seus arquivos, expor os mesmos modelos oficiais no dashboard offline e impedir que uma
sprint de implementacao comece sem revisao e aprovacao atuais.

## Escopo incluido

- Instalar modelos de PRD, TRD, Fluxo do App, UI/UX Design, Esquema Backend e Plano de Implementacao.
- Diagnosticar lacunas, ambiguidades, referencias, IDs, dependencias e aprovacao por hash.
- Mostrar os seis documentos e seus exemplos dentro do dashboard.
- Vincular base aprovada, Plano mestre e sprints de implementacao.
- Documentar decisao, protocolo e testes de conformidade.

## Fora do escopo

- Criar ou instalar um sandbox como parte da base documental.
- Auditar conformidade do codigo com a documentacao.
- Gerar a revisao semantica sem o agente escolhido pelo usuario.
- Abrir, renomear, substituir ou preencher automaticamente documentos do adotante.
- Commit, push, release ou publicacao.

## Entregaveis

- [x] E1. Modelos completos e diagnostico compartilhado instalador/CLI/dashboard.
- [x] E2. Exibicao offline dos exemplos e estados documentais no dashboard.
- [x] E3. Guards de Spec-First e sprint de implementacao com trilha de aprovacao.
- [x] E4. Testes nas duas direcoes, protocolo, ADR-009 e artefatos derivados atualizados.

## Checklist de Acoes

### Bloco 1: Modelos e diagnostico

- [x] 1.1 Criar os seis modelos com orientacoes, campos minimos e exemplos
  - Arquivo(s): `templates/product-docs/`, `scripts/nf_product_docs.py`
  - Validacao: `python3 -m unittest tests.test_guards.TestProductDocs`
  - Evidencia: TestProductDocs e TestDashboard PASS; seis exemplos presentes e HTML escapado verificado.
- [x] 1.2 Integrar diagnostico, mapeamento, instalacao e atualizacao do dashboard
  - Arquivo(s): `scripts/nf_install.py`, `scripts/nf_dashboard.py`
  - Validacao: instalacao greenfield/brownfield em diretorio temporario
  - Evidencia: TestInstalador PASS com instalacoes greenfield, brownfield, dry-run e reinstalacao descartaveis.

### Bloco 2: Aprovacao e sprints

- [x] 2.1 Estender Spec-First com validacao de IDs, referencias e dependencias do plano
  - Arquivo(s): `scripts/validate_module_spec.py`, `docs/protocols/product-documentation.md`
  - Validacao: guard reprova inconsistencias e tolera preparacao documental
  - Evidencia: teste focado P11 PASS nas direcoes conforme e violadora.
- [x] 2.2 Bloquear inicio de implementacao com documento ausente, stale ou sem aprovacao
  - Arquivo(s): `scripts/validate_sprint_state.py`, `docs/adr/ADR-009-base-documental-do-produto.md`
  - Validacao: sprint implementacao pendente falha S7 e sprint de preparacao passa
  - Evidencia: teste focado S7 PASS; aprovacao vigente permite, ausencia/stale bloqueiam e preparacao documental passa.

### Bloco 3: Fechamento

- [x] 3.1 Rodar suite e gates; regenerar indice, dashboard-demo e diagrama se afetado
  - Arquivo(s): `tests/test_guards.py`, `.neural-flow/indice-regras.md`, `docs/dashboard-demo.html`
  - Validacao: suite completa, `python3 scripts/nf_gate.py`, `git diff --check`
  - Evidencia: suite completa PASS (102 testes), mais 2 testes focados S7/P11 PASS; 8 guards PASS; derivados verificados pelos testes de drift.

## Evidencias de Implementacao

- `2026-10-12`: consolidacao e publicacao autorizadas pelo usuario na Sprint 7.
- `2026-10-12`: testes focados PASS para S7 (base aprovada permite implementacao;
  aprovacao ausente ou stale bloqueia; preparacao documental permanece permitida).
- `2026-10-12`: testes focados PASS para P11 (referencia REQ inexistente e
  dependencia circular/self-reference reprovam; plano conforme e aceito).
- `2026-10-12`: configuracao existente e preservada byte a byte sem --force;
  instalacao inicial, dry-run, reinstalacao e --force verificados em fixtures.
- `2026-10-12`: suite completa PASS, 102 testes em 357,761 s, incluindo instalacao
  ponta a ponta. Dois testes adicionais S7/P11 tambem PASS; 8 guards PASS.
- Confianca: ALTA - execucao dos testes, instalacoes descartaveis e guards. Status
  permanece em andamento ate registrar o consumo; revisao visual segue na Sprint 7.

## Pendencias para a Proxima Sprint

- Consumo observado desta sprint ainda nao medido com atribuicao especifica.
- Revisao visual do dashboard documentada como pendente na Sprint 7.

## Regras

- Validar antes de commitar: `python3 scripts/nf_gate.py`
- Item so recebe `[x]` quando a acao foi realmente executada.
- Preservar o trabalho que ja existia no checkout.
