# Sprint 10: Retirar o Action Gateway

## Snapshot Operacional

- App/Escopo: `Neural-Flow Framework — validacao local e retirada do executor de acoes`
- Status: `concluida`
- Tipo de trabalho: `implementacao`
- Data de inicio: `2026-11-27`
- Data planejada de conclusao: `2026-11-27`
- Data real de conclusao: `2026-11-27`
- Ultima atualizacao: `2026-11-27`
- Nivel de autonomia: `A1`
- Blocker principal: `nenhum`
- Proxima acao: `consultar o indice de decisoes na Sprint 11`

## FinOps de Tokens

- Token budget: `100k`
- Consumo observado: `425741`
- Leitura do consumo: teto faturavel observado no projeto pelo recorte da sprint em 2026-11-27. Inclui a Sprint 9 e outras atividades do dia.
- Mitigacao aplicada: contabilizado o teto compartilhado sem atribuir o estouro a uma unica sprint. Fonte: `python3 scripts/nf_tokens.py --sprint 10 --json` (152 requisicoes).

## Escopo incluido

- Retirar o executor de acoes, a politica, o guard dedicado e suas integracoes.
- Preservar testes, hook, validacao local e historico dos ADRs.
- Publicar a main validada e retirar branches ja integradas.

## Fora do escopo

- Alterar infraestrutura de aplicacao ou apagar dados operacionais.

## Checklist de Acoes

- [x] 1.1 Retirar o Action Gateway e alinhar a documentacao.
- [x] 1.2 Executar a suite e o pre-commit local.

## Evidencias de Implementacao

- `2026-11-27`: `python3 -m unittest discover -s tests` PASS com 104 testes,
  incluindo instalacao em projetos descartaveis.
- `2026-11-27`: `python3 scripts/nf_gate.py --quiet` PASS com sete guards;
  `.githooks/pre-commit` PASS sobre os arquivos em stage.
- Confianca: ALTA - suite, guards e compilacao de 21 arquivos Python verificados localmente.
