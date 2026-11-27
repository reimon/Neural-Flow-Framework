# Sprint 9: Remover sandbox do Action Gateway

## Snapshot Operacional

- App/Escopo: `Neural-Flow Framework — politica v2 e execucao de comandos exatos`
- Status: `em andamento`
- Tipo de trabalho: `implementacao`
- Data de inicio: `2026-11-27`
- Data planejada de conclusao: `2026-11-27`
- Ultima atualizacao: `2026-11-27`
- Nivel de autonomia: `A1`
- Blocker principal: `nenhum`
- Proxima acao: `revisar o diff e registrar o consumo antes de encerrar`

## FinOps de Tokens

- Token budget: `100k`
- Limite de alerta: `70%`
- Consumo observado: `em andamento`
- Mitigacao aplicada: `nao se aplica`

## Escopo incluido

- Remover a integracao interna de sandbox e exigir o comando completo na politica.
- Preservar aprovacao interativa, auditoria e validacao de sprint.
- Validar o instalador e documentar a migracao explicita.

## Fora do escopo

- Prover isolamento externo ou alterar o CI e a infraestrutura.
- Publicar alteracoes ou executar commit, push ou deploy.

## Checklist de Acoes

- [x] 1.1 Implementar a politica v2 e remover o sandbox interno.
- [x] 1.2 Atualizar diretrizes, instalador e documentacao de migracao.
- [x] 1.3 Executar os testes e os guards pelo gateway.

## Evidencias de Implementacao

- `2026-11-27`: State Protocol PASS antes da implementacao.
- `2026-11-27`: em clone descartavel, `run-gates` aprovou os oito guards e
  `run-tests` aprovou 111 testes em 213,061 s. A auditoria registrou resultado
  zero para as duas acoes, executadas sem TTY.
- `2026-11-27`: a suite confirmou a instalacao greenfield sem o modulo removido,
  a preservacao brownfield e a execucao pelo gateway apos migracao explicita.
- Confianca: ALTA - resultados observados nos comandos e na auditoria do gateway.
