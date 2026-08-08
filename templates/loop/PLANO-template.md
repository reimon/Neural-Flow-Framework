# Plano de construcao — <Projeto>

> TEMPLATE Neural-Flow (`docs/protocols/autonomous-loop.md`). Copie para `build/PLANO.md`.

Estado vivo do loop. **Este arquivo e a fonte de verdade do que ja foi feito.**
Atualize ao fim de cada iteracao, conforme `build/PROTOCOLO.md`.

Marcacao: `[ ]` a fazer · `[x]` pronto e verificado · `[BLOQUEADO: motivo]`.

## Definicao de Pronto (a meta do loop)

O loop encerra quando **todos** os itens estiverem `[x]` ou `[BLOQUEADO]` **e** isto for
verdade **numa maquina limpa**:

1. `<subir dependencias — ex: docker compose up -d>`
2. `<aplicar migrations>`
3. `<subir a aplicacao + health check com resultado esperado explicito>`
4. `<abrir a interface e executar o fluxo minimo>`
5. `<comando de verificacao>` verde: formatacao, lint, migrations em banco descartavel,
   suite de testes
6. O roteiro de aceite (item `<A1>`) percorre ponta a ponta sem erro
7. Nada disso exige uma unica credencial externa

## Decisoes ja tomadas — nao reabrir

> Cada decisao aponta para a spec/ADR que a fundamenta. Reabrir decisao registrada e
> desperdicio de iteracao.

- **`<Backend>`:** `<escolha>`. Fonte: `<arquivo>`.
- **`<Interface>`:** `<escolha>`. Fonte: `<arquivo>`.
- **`<Banco>`:** `<escolha>`.
- **`<Runtime/versao fixada e por que>`**
- **`<Gerenciador de pacotes — e o que NAO usar>`**
- **Sem servico externo real.** Todo integrador externo e interface + falso deterministico.

## Fora do escopo deste loop

> Escopo sem fronteira explicita e escopo que o agente amplia sozinho — sempre com boa
> intencao, sempre na direcao errada. Liste **nominalmente**.

- `<modulo/feature que NAO deve ser comecado>`
- `<integracao adiada>`
- `<qualquer implantacao em nuvem>`

## Fase E — Esqueleto que roda

- [ ] **E1 — `<titulo>`.**
  - Criterio de aceite: `<verificavel, nao subjetivo>`
  - Spec a seguir: `<arquivo>`

- [ ] **E2 — `<titulo>`.**
  - Criterio de aceite: `<...>`
  - Spec a seguir: `<...>`

## Fase D — Dados de referencia

- [ ] **D1 — `<carga da base com versao e fonte>`.**

## Fase M — Modulos

> Ordem = dependencia. Um pedaco de modulo por iteracao.

- [ ] **M1 — `<titulo>`.**

## Fase A — Aceite

- [ ] **A1 — Roteiro de aceite ponta a ponta.**
