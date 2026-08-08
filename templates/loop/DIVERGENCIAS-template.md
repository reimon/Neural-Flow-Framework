# Divergencias — <Projeto>

> TEMPLATE Neural-Flow. Copie para `build/DIVERGENCIAS.md`.
>
> **Este e o arquivo mais importante para o humano revisar.** Cada entrada e uma decisao
> de produto que o loop tomou sozinho porque a spec nao respondeu. O diario e cronologico;
> as divergencias sao o que se le **antes de decidir**.

Regra de ouro: o agente **nao edita a spec**. Quando a spec e ambigua, incompleta ou
contraditoria, registra aqui e segue com a decisao **mais conservadora**.

Formato:

```markdown
## <ID do item> — <titulo curto>

- **Data:** AAAA-MM-DD
- **Spec consultada:** `<arquivo, secao>`
- **Consultas ao indice tentadas:** `<formulacao 1>`, `<formulacao 2 — reformulada>`
- **O que falta / o que conflita:** <descricao objetiva>
- **Confianca:** BAIXA — <por que nao subiu: fonte inexistente | nao executavel neste ambiente>
- **Decisao tomada para seguir:** <a opcao mais conservadora, explicita>
- **Reversivel?** sim | nao — <se "nao", esta entrada deveria ter virado pergunta ao humano>
- **Impacto se a decisao estiver errada:** <o que precisaria ser refeito>
- **Status:** pendente de revisao humana | confirmada em AAAA-MM-DD | revertida
```

Antes de abrir uma divergencia, percorra a escada de verificacao (`docs/protocols/calibration.md`):
buscar fonte documental, e se for executavel, executar. Divergencia aberta sem os dois
degraus e preguica registrada como incerteza.

---

## <ID> — <exemplo>

- **Data:** AAAA-MM-DD
- **Spec consultada:** `<arquivo>`
- **O que falta / o que conflita:** `<...>`
- **Decisao tomada para seguir:** `<...>`
- **Impacto se a decisao estiver errada:** `<...>`
- **Status:** pendente de revisao humana
