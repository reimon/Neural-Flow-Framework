# Playbook de Rollback: <Feature / Sprint N-M>

> TEMPLATE Neural-Flow. Copie para `docs/playbooks/ROLLBACK-<escopo>.md` ao entregar
> qualquer feature com risco de producao. Escrever o rollback ANTES do deploy e gate
> de sprint (Evidencia Sintetica).

## Quando usar este playbook

- `<sintoma 1 que justifica rollback>`
- `<sintoma 2>`

## Escalacao rapida (< 5 min)

```bash
# 1. Determinar se o problema e desta feature ou geral
<comando de health geral>
<comando de health da feature>
# 2. Se health geral falhando → rollback geral (nao este playbook)
# 3. Avisar o canal: "Rollback iniciado para <escopo>. ETA <X> min."
```

## Fase 1 — Avaliacao (5 min)

- [ ] Confirmar sintoma com evidencia (log/metricas, nao suposicao)
- [ ] Classificar: codigo | banco | config | integracao externa

## Fase 2 — Rollback de codigo

### Opcao A: Feature flag (mais rapido)

```bash
<desligar flag>
<validar que endpoints respondem com feature desativada>
```

### Opcao B: Revert via git + CI (mais seguro)

```bash
# 1. Identificar ultimo commit ANTES da feature (buscar "Sprint N - ...")
# 2. git revert (nunca reset em branch compartilhada)
# 3. Push → deploy automatico via CI (NUNCA deploy manual)
# 4. Monitorar pipeline ate success + aguardar startup
```

## Fase 3 — Rollback de banco (se houver migration)

- [ ] Backup do estado ATUAL antes de qualquer undo
- [ ] Preferir rollback logico (reset de triggers/defaults) a DROP
- [ ] Validar que dados pre-existentes NAO foram perdidos (`<query de sanidade>`)
- Opcao destrutiva (DROP das tabelas novas) exige aprovacao explicita e backup completo

## Fase 4 — Validacao pos-rollback (5 min)

```bash
<script/comandos de validacao com resultado esperado explicito>
```

## Fase 5 — Post-mortem

- Timeline, causa raiz, acao corretiva, follow-ups
- Registrar em `docs/incidents/AAAA-MM-DD-<slug>-postmortem.md`
- Licao → `MEMORY.md` (Solutions Log); regra permanente → `AGENTS.md` + guard

## Fase 6 — Re-deploy (apos fix)

- Fix em branch → PR → review → merge → deploy via CI → monitorar

## Checklists rapidos

Before: backup feito | rollback testado em nao-prod | canal avisado
During: seguir fases na ordem | evidencia de cada passo | sem comando manual ad-hoc
After: validacao PASS | post-mortem aberto | memoria atualizada

## Tempo estimado por cenario

| Cenario | Tempo |
|---|---|
| Feature flag | `<min>` |
| Revert de codigo | `<min>` |
| Revert codigo + banco | `<min>` |
