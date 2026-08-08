# RUNBOOK: <Sintoma> (<limiar, ex: P95 > 5s | erro > 5%>)

> TEMPLATE Neural-Flow. Um runbook por modo de falha conhecido, agrupados em
> `docs/playbooks/SRE-RUNBOOKS-<sistema>.md`. Cada runbook deve ser executavel por
> alguem (ou algum agente) que nao construiu o sistema.

## Sintomas

- `<como o problema aparece para usuario/monitoramento>`

## Diagnostico (<X> min)

```bash
# 1. <verificacao mais barata primeiro, com resultado ESPERADO comentado>
# Esperado: <valor>. Se <outro valor> → pular para RUNBOOK <n>
# 2. <proxima verificacao>
# 3. <...>
```

Regras:

- Cada comando declara o resultado esperado — sem isso o operador nao sabe se passou.
- Encadear runbooks ("se X → runbook Y") em vez de duplicar diagnostico.
- Nomes de recursos derivados em runtime, nunca hardcoded.

## Causas comuns

| Causa | Sinal distintivo |
|---|---|
| `<causa 1>` | `<como reconhecer>` |

## Remediation (<X> min)

```bash
# Opcao 1 (menos invasiva): <comando> — aguardar <t>, testar
# Opcao 2: <comando>
# Opcao N (mais invasiva/custosa por ultimo)
```

- NUNCA deploy/apply manual como remediacao — usar CI.
- Acao temporaria (firewall, scale-up) → registrar e reverter apos.

## Validacao de sucesso

```bash
<comando + valor esperado que fecha o incidente>
```

## Escalacao

- Se nao resolver em `<t>` min: `<quem/canal>`
- Incidente com perda de dados ou seguranca: acionar `<processo>` imediatamente

## Pos-incidente

- Post-mortem se houve impacto a usuario
- Licao → `MEMORY.md`; se o runbook mudou, atualizar a data no cabecalho
