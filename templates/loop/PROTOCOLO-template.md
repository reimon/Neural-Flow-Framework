# Protocolo de construcao — uma iteracao

> TEMPLATE Neural-Flow (`docs/protocols/autonomous-loop.md`). Copie para
> `build/PROTOCOLO.md` e preencha `<...>`. Este arquivo e lido no inicio de **cada**
> iteracao — corrigi-lo vale ja na proxima.

Voce esta dentro de um loop. Este arquivo descreve exatamente o que fazer numa iteracao.
Nao improvise fora daqui.

Diretorio de trabalho: `<caminho absoluto>`. O codigo vive em `<dir>`.

## 0. Antes de qualquer coisa

Leia, nesta ordem:

1. `build/PLANO.md` — backlog e estado. **Fonte de verdade do que ja foi feito.**
2. `build/DIARIO.md` — ultimas 20 linhas, para saber o que a iteracao anterior fez.
3. `build/DIVERGENCIAS.md`, se existir.

Nao confie na sua memoria da conversa: o contexto pode ter sido reiniciado entre
iteracoes. **O disco manda.**

### A especificacao se consulta pelo indice, nao por varredura

```
graphify query "<sua pergunta>"
```

Outros pontos de entrada: `graphify-out/wiki/index.md`, `graphify-out/GRAPH_REPORT.md`.

Só abra o `.md` bruto quando precisar do texto exato de um trecho que o grafo apontou.
Varrer a documentacao com `grep` para "entender o modulo" custa ~48x mais tokens que a
consulta ao indice, e voce tem teto de contexto a respeitar (secao 3, regra 7).

**Se a consulta voltar fraca, reformule antes de escalar.** Resultado vazio, generico ou
irrelevante nao autoriza cair na varredura: mude o vocabulario, a entidade ou o nivel de
abstracao e consulte de novo. Se a segunda reformulacao tambem nao ajudar, registre a
lacuna de contexto em `build/DIVERGENCIAS.md` — nao presuma que "nao ha nada sobre isso".

Escolha a ferramenta pela classe da pergunta: estrutura/relacao ⇒ grafo; historico/decisao
⇒ RAG + ADR; texto exato ⇒ leitura do arquivo apontado; **comportamento ⇒ executar**;
estado do trabalho ⇒ disco.

## 1. Condicao de parada — verifique primeiro

Se **todos** os itens de `build/PLANO.md` estiverem `[x]` ou `[BLOQUEADO]` **e**
`<comando de verificacao>` estiver verde:

- escreva `build/RELATORIO-FINAL.md` — o que ficou pronto, o que ficou bloqueado e por
  que, e como rodar o sistema;
- **encerre o loop** (nao agende nova iteracao);
- imprima as instrucoes de execucao em tres linhas.

Caso contrario, siga.

## 2. Escolha exatamente UM item

Pegue o **primeiro** item nao marcado de `build/PLANO.md`, na ordem escrita. A ordem
codifica dependencia — nao pule por conveniencia.

**Um item por iteracao. Nunca dois.**

Se o item ja falhou em 3 iteracoes seguidas (conte no `DIARIO.md`), marque `[BLOQUEADO]`
com o motivo em uma linha e passe ao proximo.

## 3. Implemente

Regras que nao se negociam:

1. **A especificacao e entrada, nao saida.** Nao edite `<dir de specs>`. Se a spec estiver
   ambigua, incompleta ou contraditoria, escreva em `build/DIVERGENCIAS.md` (arquivo,
   secao, o que falta, que decisao voce tomou) e siga com a decisao mais conservadora.
2. **Nenhum dado de dominio inventado.** `<valores regulados>` vem de `<base de
   referencia>`, sempre com fonte e data. Dado ausente ⇒ item `[BLOQUEADO]` — nunca um
   valor plausivel.
3. **Nenhuma credencial externa.** Todo servico externo entra como interface +
   implementacao falsa deterministica, ativa por padrao. O sistema sobe numa maquina sem
   nenhuma chave.
4. **Falha fechada.** Caminho degradado nunca relaxa autorizacao, consentimento ou
   mascaramento. Sem dado: "dados insuficientes" com a data da ultima informacao.
5. **Linguagem segura** em UI e mensagens: nao prometer `<resultado regulado>`.
6. **Nao refatore o que ja esta verde** porque voce faria diferente.
7. **Teto de 50% de contexto.** Passou da metade da janela ⇒ o item era grande demais.
   Pare, quebre em subitens no `PLANO.md`, faca o primeiro. Ao despachar subagente,
   dimensione a fatia por **volume de conteudo** (palavras/bytes), nao por numero de
   arquivos.
8. **Confianca declarada.** Antes de concluir qualquer coisa, classifique a evidencia:
   `ALTA` (execucao verificada) · `MEDIA` (spec/ADR vigente) · `BAIXA` (inferencia).
   Cadeia com um elo inferido e conclusao inferida. Repetir a inferencia nao a promove.
   - `BAIXA` obriga um degrau a mais **antes** de responder: buscar a fonte; se for
     executavel, executar. Se e barato executar, nao opine.
   - `BAIXA` persistente + acao **reversivel** ⇒ decisao conservadora + divergencia.
   - `BAIXA` persistente + acao **irreversivel** (perder dado, expor dado pessoal, gastar
     dinheiro, mexer em producao) ⇒ **pare e pergunte ao humano.** E a unica interrupcao
     por incerteza permitida no loop.

## 4. Verifique — antes de marcar qualquer coisa

```
<comando de verificacao — formatacao, lint, migrations descartaveis, suite de testes>
```

**Verde e a unica condicao para marcar pronto.** Vermelho: conserte nesta iteracao; se nao
conseguir, o item **nao** e marcado — registre no diario o que falhou.

Item **nunca** e marcado `[x]` com confianca `BAIXA`, mesmo que a verificacao esteja verde
por outro motivo: verde sem cobertura do que o item pedia e falso positivo, nao evidencia.

Nunca marque pronto com teste desabilitado, `skip`/`xfail` novo ou assercao afrouxada.
Isso e regressao silenciosa, e o loop nao tem quem a pegue alem de voce.

## 5. Registre e commite

1. Marque `[x]` em `build/PLANO.md`.
2. Acrescente 1 a 3 linhas em `build/DIARIO.md`:
   `<ID> — <o que foi feito> — <verificar: verde|vermelho> — <confianca: ALTA|MEDIA|BAIXA> — <o que a proxima precisa saber>`
3. **Deixe o indice pronto para a proxima iteracao** (incremental):
   ```
   /graphify <caminho do projeto> --update
   ```
   > NUNCA rode `graphify update` direto no shell em repositorio que contem documentacao —
   > o subcomando do CLI faz rebuild so de AST sobre todos os arquivos e destroi a camada
   > semantica curada. Use a skill.
4. Aprendeu algo nao derivavel do codigo nem da spec ⇒ `build/DIVERGENCIAS.md`.
5. Commite **apenas o que voce escreveu**, com caminhos explicitos:
   ```
   git add <caminhos seus> && git commit -m "<ID>: <resumo> (spec: <arquivo>)"
   ```
   Nunca `git add -A` nem `git add .`. Se o pre-commit reclamar, **nao use `--no-verify`**
   — o gate esta certo e voce provavelmente incluiu o que nao devia.

## 6. Encerre a iteracao

Escreva no chat, em no maximo 4 linhas: item feito, resultado da verificacao, proximo item.
Depois agende a proxima iteracao.

Nao peca confirmacao para seguir. Só pare para perguntar diante de decisao **irreversivel**
que a spec nao responde (perder dado, expor dado pessoal, gastar dinheiro).
