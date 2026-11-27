# Sprint 12: Evidencia dos guards

## Snapshot Operacional

- App/Escopo: `Neural-Flow Framework - relatorio dos guards no terminal, painel e CI`
- Status: `concluida`
- Tipo de trabalho: `implementacao`
- Data de inicio: `2026-11-27`
- Data planejada de conclusao: `2026-11-27`
- Data real de conclusao: `2026-11-27`
- Ultima atualizacao: `2026-11-27`
- Nivel de autonomia: `A1`
- Blocker principal: `nenhum`
- Proxima acao: `acompanhar a adocao do relatorio de guards`

## FinOps de Tokens

- Token budget: `150k`
- Consumo observado: `756843`
- Leitura do consumo: teto faturavel observado na raiz do projeto ate a coleta. Recorte diario compartilhado com outras sprints; os tetos nao sao aditivos.
- Mitigacao aplicada: encerramento com o teto identificado separadamente do consumo exclusivo; medidas do piloto em pastas temporarias ficam registradas a parte.
- Fonte: `python3 scripts/nf_tokens.py --sprint 12 --json` (245 requisicoes do projeto).

## Escopo incluido

- Relatorio dos guards no terminal, painel e ci.

## Fora do escopo

- Alterar as decisoes aceitas, a infraestrutura de producao ou as permissoes de publicacao.

## Checklist de Acoes

- [x] 12.1 Distinguir conformidade, falha, ausencia de artefato e falta de execucao.
- [x] 12.2 Compartilhar evidencia no painel e no resumo da execucao do CI.
- [x] 12.3 Validar em projetos conformes, violadores, vazios e com validador proprio.

## Piloto de skills

Em 2026-11-27, duas sessoes efemeras do Codex CLI 0.169.0 usaram o mesmo
modelo (`gpt-6.2-astra`), modo de leitura e um projeto Git descartavel.
O arquivo de dominio dizia: "Uma turma possui matriculas ativas ou encerradas.
Arquivar oculta a turma da listagem principal." A solicitacao nas duas sessoes
foi: "Precisamos desenhar o arquivamento de turmas. Consulte DOMINIO.md e me
diga o que precisamos definir antes de implementar esse recurso."

O criterio de acerto foi perguntar o que fazer com matriculas ativas, sem
inventar essa politica como requisito. Uma copia recebeu o diretorio completo
da skill `grilling` em `.agents/skills/`. Os contadores de entrada ja incluem
o cache lido. A soma por tarefa usa entrada e saida.

| Catalogo local | Acerto | Entrada | Cache lido | Saida | Tokens por tarefa |
| --- | --- | ---: | ---: | ---: | ---: |
| Sem a skill | Sim | 52041 | 44544 | 424 | 52465 |
| Com a skill disponivel | Sim | 52256 | 48384 | 393 | 52649 |

Confianca: ALTA - eventos de conclusao e respostas das duas execucoes do Codex
inspecionados. A trilha mostrou leitura do arquivo de dominio em ambas. A
ativacao da skill ficou sem evidencia. Esta amostra tem um par e cache diferente
entre as execucoes. A comparacao com Claude Code fica pendente por ausencia
do cliente na estacao.

## Evidencias de Implementacao

- 2026-11-27: O repositorio registrou cinco guards conformes e dois sem artefato. Instalacao em projeto descartavel com validador proprio reproduziu P10 com arquivo e linha no JSON, HTML e resumo. O comando do workflow sobre as fixtures conforme e violadora gerou o resumo e retornou respectivamente 0 e 1.
- `python3 -m unittest discover -s tests`: PASS, 111 testes.
- Confianca: ALTA - execucao dos testes, dos guards e inspecao dos artefatos gerados.
