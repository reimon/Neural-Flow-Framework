# Sprint 7: Clareza, prioridades e navegacao do dashboard

## Snapshot Operacional

- App/Escopo: `dashboard offline do Neural-Flow, visual e leitura do estado existente`
- Status: `em andamento`
- Tipo de trabalho: `implementacao`
- Data de inicio: `2026-10-12`
- Data planejada de conclusao: `2026-10-12`
- Data real de conclusao: `a definir`
- Ultima atualizacao: `2026-10-12`
- Nivel de autonomia: `A1`
- Blocker principal: `revisao visual manual; ferramenta de navegador bloqueia URLs file`
- Proxima acao: `revisar visualmente o painel, o teclado e uma tela pequena no navegador`

## FinOps de Tokens

- Token budget: `100k`
- Limite de alerta: `70%`
- Consumo observado: `em andamento`
- Mitigacao aplicada: `nao se aplica`

## Objetivo

Melhorar os tres pontos pedidos pelo usuario: visual e organizacao, indicadores e
pendencias, navegacao e uso no celular. Manter o HTML offline, a stdlib e todas as
secoes e ajudas existentes.

## Escopo incluido

- Hierarquia visual, grupos de indicadores e atalhos para as secoes.
- Prioridades derivadas de guards, sprints, budget, documentos e divergencias.
- Sprint em destaque coerente com as sprints em andamento e informacao de prazo.
- Layout responsivo e acesso por teclado.
- Testes de comportamento, demonstracao regenerada e dashboard local atualizado.
- Consolidacao e publicacao dos trabalhos anteriores do gateway e da base documental,
  conforme autorizacao explicita do usuario em 2026-10-12.
- Alinhamento do instalador com a preservacao de configuracao existente sem --force.

## Fora do escopo

- Alterar politicas de seguranca, instalar dependencias ou executar servicos.
- Modificar dados das outras sprints ou aprovar documentos automaticamente.
- Merge sem a revisao humana exigida pela protecao da branch main.

## Criterios de aceite

- CA-001: nenhuma sprint planejada ou concluida aparece como ativa.
- CA-002: a ausencia de controles ativos nao aparece como conformidade verificada.
- CA-003: prazos e pendencias sao derivados do carimbo de geracao e dos artefatos.
- CA-004: atalhos possuem destinos existentes e o HTML continua offline.
- CA-005: secoes, exemplos e ajuda existentes continuam acessiveis.

## Checklist de Acoes

- [x] 1.1 Melhorar indicadores, escolha da sprint e resumo de pendencias
  - Arquivo(s): `scripts/nf_dashboard.py`, `tests/test_guards.py`
  - Validacao: testes do dashboard e casos de fronteira
  - Evidencia: suite completa com 99 testes PASS e teste adicional de blocker do snapshot PASS.
- [ ] 1.2 Melhorar organizacao, atalhos e layout para celular
  - Arquivo(s): `scripts/nf_dashboard.py`
  - Validacao: HTML gerado, destinos dos atalhos, regras responsivas e acesso por teclado
  - Evidencia: HTML, atalhos e scripts verificados; layout implementado. Revisao visual e uso real por teclado/celular pendentes.
- [x] 1.3 Regenerar demonstracao e painel local; executar suite e gates
  - Arquivo(s): `docs/dashboard-demo.html`, `.neural-flow/dashboard.html`
  - Validacao: `python3 -m unittest discover -s tests`, `python3 scripts/nf_gate.py`
  - Evidencia: geracoes com exit 0; suite completa PASS; 8 guards PASS; diff sem erros.

### Bloco 2: Consolidacao e publicacao autorizadas

- [x] 2.1 Validar a instalacao e preservar configuracao existente sem --force
  - Arquivo(s): `scripts/nf_install.py`, `tests/test_guards.py`
  - Validacao: suite completa com instalacoes greenfield e brownfield descartaveis
  - Evidencia: suite completa com 102 testes PASS; preservacao sem --force, dry-run e reinstalacao verificados.
- [x] 2.2 Commitar e publicar o conjunto completo em branch com PR
  - Validacao: hook sobre o stage, commit, push e checks do PR
  - Evidencia: commit 20f61ba publicado em codex/dashboard-sprint7; PR #1 aberto; 3 checks PASS no run 38329075984.

## Contexto e autorizacao

- Fontes: `README.md`, `scripts/nf_dashboard.py`, `tests/test_guards.py`.
- Lacuna de contexto: `graphify-out/graph.json` ausente; leitura dirigida do gerador e seus testes.
- O usuario autorizou nesta conversa a excecao para executar diretamente a suite,
  os gates e o gerador do dashboard, incluindo a demonstracao, sem alterar a politica.
- Em 2026-10-12, apos a pergunta sobre escopo e excecao do Git, o usuario pediu
  "publica tudo a alinha tudo": autorizou a consolidacao de todo o trabalho pendente
  e a execucao direta necessaria ao commit/push, sem relaxar a politica versionada.

## Evidencias de Implementacao

- `2026-10-12`: sprint validada antes da implementacao; `nf_gate.py sprint` PASS.
- `2026-10-12`: `nf_gate.py` PASS com 8 guards. `git diff --check` sem erros.
- `2026-10-12`: painel local e demonstracao regenerados pelo gerador oficial.
- `2026-10-12`: teste de IDs unicos e destinos dos atalhos PASS; IDs do SVG e
  janela de ajuda do historico corrigidos para evitar duplicacao no mesmo HTML.
- `2026-10-12`: sintaxe dos scripts inline de navegacao e idioma verificada no V8.
- `2026-10-12`: `python3 -m unittest discover -s tests -q` PASS, 99 testes em 369,297 s.
- `2026-10-12`: teste adicional do blocker declarado no snapshot PASS. Bloqueio
  declarado aparece mesmo quando o status da sprint ainda e em andamento.
- `2026-10-12`: validacao do conjunto consolidado PASS: 102 testes em 357,761 s,
  mais 2 testes focados positivos/negativos de S7 e P11; 8 guards PASS.
- `2026-10-12`: refs atualizadas do origin confirmaram base alinhada com main (0/0).
- `2026-10-12`: commit `20f61ba` criado com 45 arquivos; hook sobre o stage PASS
  com 8 guards. Push da branch `codex/dashboard-sprint7` confirmado.
- `2026-10-12`: PR https://github.com/reimon/Neural-Flow-Framework/pull/1 publicado.
  CI https://github.com/reimon/Neural-Flow-Framework/actions/runs/38329075984 PASS:
  testes em Python 3.10 e 3.12 e dogfood dos protocolos.
- Integracao na main depende do review humano obrigatorio. Revisao visual do painel,
  adaptadores de sandbox e consumo especifico da Sprint 6 continuam pendentes.
- Confianca: ALTA - execucoes acima e HTML gerado inspecionado.
- Confianca: MEDIA - responsividade e interacoes avaliadas pelo codigo; revisao
  visual e uso real por teclado/celular ainda pendentes. A ferramenta de navegador
  bloqueia a abertura de URLs file; nao foi contornado esse bloqueio.
