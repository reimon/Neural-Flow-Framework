# Sprint 11: Vigencia das decisoes

## Snapshot Operacional

- App/Escopo: `Neural-Flow Framework - indice de regras e validacao de superacao de ADRs`
- Status: `concluida`
- Tipo de trabalho: `implementacao`
- Data de inicio: `2026-11-27`
- Data planejada de conclusao: `2026-11-27`
- Data real de conclusao: `2026-11-27`
- Ultima atualizacao: `2026-11-27`
- Nivel de autonomia: `A1`
- Blocker principal: `nenhum`
- Proxima acao: `usar as decisoes vigentes na revisao das entregas`

## FinOps de Tokens

- Token budget: `150k`
- Consumo observado: `756843`
- Leitura do consumo: teto faturavel observado na raiz do projeto ate a coleta. Recorte diario compartilhado com outras sprints; os tetos nao sao aditivos.
- Mitigacao aplicada: encerramento com o teto identificado separadamente do consumo exclusivo; medidas do piloto em pastas temporarias ficam registradas a parte.
- Fonte: `python3 scripts/nf_tokens.py --sprint 11 --json` (245 requisicoes do projeto).

## Escopo incluido

- Indice de regras e validacao de superacao de adrs.

## Fora do escopo

- Alterar as decisoes aceitas, a infraestrutura de producao ou as permissoes de publicacao.

## Checklist de Acoes

- [x] 11.1 Resolver decisoes e escopos no indice Markdown e JSON.
- [x] 11.2 Validar referencias e ciclos nas duas formas de declarar superacao.

## Evidencias de Implementacao

- 2026-11-27: O indice v2 associa as quatro regras historicas do gateway ao ADR-012 no escopo de execucao. Fixtures de superacao parcial, titulo com prefixo semelhante, referencia pendurada e ciclo misto passaram nos testes.
- `python3 -m unittest discover -s tests`: PASS, 111 testes.
- Confianca: ALTA - execucao dos testes, dos guards e inspecao dos artefatos gerados.
