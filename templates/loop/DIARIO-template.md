# Diario do loop — <Projeto>

> TEMPLATE Neural-Flow. Copie para `build/DIARIO.md`. Escrito pelo agente, uma entrada por
> iteracao, cronologico. Serve para: (a) a proxima iteracao saber onde parou, (b) contar
> falhas repetidas do mesmo item (3 ⇒ `[BLOQUEADO]`).

Formato de cada linha:

```
<ID do item> — <o que foi feito> — <verificar: verde|vermelho> — <confianca: ALTA|MEDIA|BAIXA> — <o que a proxima iteracao precisa saber>
```

Regras:

- 1 a 3 linhas por iteracao. Nao e relatorio, e rastro.
- Registrar tambem iteracao que **falhou** — e como as 3 tentativas sao contadas.
- Decisao de produto tomada pelo agente nao vai aqui: vai em `DIVERGENCIAS.md`.
- **Confianca e derivada da evidencia**, nao da sensacao: `ALTA` = execucao verificada,
  `MEDIA` = spec/ADR vigente, `BAIXA` = inferencia. Item marcado `[x]` nunca e `BAIXA`.

---

- E1 — `<exemplo>` — verificar: verde — confianca: ALTA — `<proximo item precisa de X>`
