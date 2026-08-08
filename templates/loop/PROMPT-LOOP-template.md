# Como rodar o loop — <Projeto>

> TEMPLATE Neural-Flow. Copie para `build/PROMPT-LOOP.md`. E a folha de operacao do humano
> (nao do agente): como iniciar, o que esperar, o que revisar, o que fazer se travar.

## Antes de comecar (uma vez so)

1. **Deixe a arvore limpa.** Commite ou `git stash` o que estiver em andamento. O loop foi
   instruido a nao tocar no que nao e dele, mas arvore limpa evita confusao.
2. **Confirme que o indice esta pronto e versionado.** `graphify-out/graph.json`,
   `GRAPH_REPORT.md` e `wiki/` entram no repositorio — e o que cada iteracao consulta em
   vez de reler a documentacao. Cache, intermediarios e `graph.html` ficam no `.gitignore`.
   > Verifique o **artefato final**, nao a presenca do diretorio: extracao interrompida
   > deixa intermediarios que parecem um indice pronto.
3. **Ative os gates:**
   ```bash
   git config core.hooksPath .githooks
   ```

## O prompt

Abra o agente em `<caminho do projeto>` e cole exatamente isto:

```
/loop Leia build/PROTOCOLO.md e execute UMA iteracao do protocolo, do inicio ao fim. O protocolo manda ler build/PLANO.md antes de decidir qualquer coisa — o disco e a fonte de verdade, nao a sua memoria da conversa. Um item por iteracao. Nao marque nada como pronto sem `<comando de verificacao>` verde. Quando a Definicao de Pronto de build/PLANO.md estiver satisfeita, escreva build/RELATORIO-FINAL.md e encerre o loop.
```

**Sem intervalo depois do `/loop`:** o loop se auto-ritma e cada iteracao leva o tempo que
precisar. Um intervalo fixo cortaria itens no meio.

## O que esperar

- **Iteracoes `<n1>` a `<n2>`** montam o esqueleto. Ao fim da `<nX>` o sistema ja sobe na
  sua maquina.
- **Iteracoes `<n3>` e `<n4>`** carregam os dados de referencia com versao e fonte.
- **Da `<n5>` em diante**, um pedaco de modulo por iteracao, na ordem de dependencia.
- O loop para sozinho ao bater a Definicao de Pronto.

## Durante o loop

Interrompa quando quiser (Esc) e retome colando o mesmo prompt: o estado esta em
`build/PLANO.md` e `build/DIARIO.md`, nao no contexto.

Vale olhar de vez em quando:

- `build/DIARIO.md` — o que cada iteracao fez.
- `build/DIVERGENCIAS.md` — **o mais importante para voce revisar**: cada linha e uma
  decisao de produto que o loop tomou sozinho.
- Itens `[BLOQUEADO]` em `build/PLANO.md`.

## Se travar

Se o mesmo item falhar tres vezes, o protocolo manda marcar `[BLOQUEADO]` e seguir. Se
varios itens seguidos bloquearem, pare o loop e leia o `DIARIO.md` — provavelmente a ordem
do plano esta errada, ou uma spec tem um buraco que precisa de decisao humana.
