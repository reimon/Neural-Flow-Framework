# Protocolo de Loop Autonomo (Estado em Disco)

## Missao

Permitir execucao autonoma prolongada (nivel A2/A3) sem que o reinicio de contexto cause
retrabalho, salto de etapa ou conclusao falsa — colocando **todo** o estado operacional em
disco, nunca na conversa.

## Regra inegociavel

O disco e a fonte de verdade, nao a memoria da conversa. Toda iteracao le o estado do
disco antes de decidir qualquer coisa, e escreve o resultado no disco antes de encerrar.

## Por que este protocolo existe

O problema que derruba a maioria das tentativas de loop e simples: **o contexto
reinicia.** Se o estado vive na conversa, a iteracao seguinte refaz trabalho ou pula
etapa. Se vive em disco, o loop pode ser interrompido a qualquer momento e retomado com o
mesmo prompt.

Efeito colateral valioso: editar as regras no meio do caminho fica trivial — o protocolo e
lido a cada iteracao, entao uma correcao vale ja na proxima.

## Os quatro arquivos de estado

| Arquivo | Papel | Quem escreve |
| --- | --- | --- |
| `build/PROTOCOLO.md` | As regras de UMA iteracao. Lido no inicio de cada uma. | Humano |
| `build/PLANO.md` | Backlog ordenado por dependencia + Definicao de Pronto + escopo negativo. **Fonte de verdade do que ja foi feito.** | Humano cria; agente marca |
| `build/DIARIO.md` | Uma a tres linhas por iteracao, cronologico. | Agente |
| `build/DIVERGENCIAS.md` | Onde a spec nao respondeu e que decisao foi tomada. **O arquivo que o humano revisa.** | Agente |

O diario e cronologico; as divergencias sao o que se le **antes de decidir**. Cada linha
de divergencia e uma decisao de produto que o loop tomou sozinho — por isso e o artefato
de revisao humana prioritario.

## Prompt de entrada

Curto de proposito. Tudo que importa esta em disco:

```
/loop Leia build/PROTOCOLO.md e execute UMA iteracao do protocolo, do inicio ao fim.
```

Sem intervalo fixo: o loop se auto-ritma, e cada iteracao leva o tempo que precisar. Um
intervalo fixo cortaria itens no meio.

## As regras que evitam mentira silenciosa

1. **Um item por iteracao. Nunca dois.** Um item pequeno que termina verde vale mais que
   tres pela metade.
2. **Verde no comando de verificacao e a unica condicao para marcar pronto.**
   Explicitamente proibido: teste desabilitado, `skip`/`xfail` novo ou assercao afrouxada
   para passar. Num loop nao ha revisor — ou a regra esta escrita, ou nao existe.
3. **A spec e entrada, nao saida.** O agente nao edita a documentacao de origem.
   Divergencia vai para arquivo proprio, com a decisao conservadora tomada.
4. **Nenhum dado de dominio inventado.** Valor regulado vem da base de referencia com
   fonte e data. Dado ausente **bloqueia o item** — nao vira valor plausivel.
5. **Nenhuma credencial externa.** Todo servico externo entra como interface +
   implementacao falsa deterministica, ativa por padrao. O sistema tem que subir numa
   maquina sem nenhuma chave.
6. **Falha fechada.** Caminho degradado nunca relaxa autorizacao, consentimento ou
   mascaramento.
7. **Nao refatorar o que ja esta verde** so porque voce faria diferente.
8. **Tres falhas seguidas no mesmo item → marcar `[BLOQUEADO]` e seguir.** Loop que
   insiste no mesmo obstaculo queima orcamento sem produzir nada.

## Teto de contexto e dimensionamento de fatia

Nenhum agente passa de **50% da janela**. Se a tarefa nao cabe, quebra-se em subitens
dentro do plano.

Ao fatiar trabalho para subagentes, dimensionar por **volume de conteudo** (palavras e
bytes), nao por contagem de arquivos. Vinte e dois arquivos pequenos e vinte e dois
grandes sao cargas completamente diferentes — essa confusao e a causa mais comum de um
agente estourar. (Caso real: 174 arquivos viraram 14 fatias de no maximo 18 mil palavras;
os dois PDFs grandes e uma imagem ganharam agente proprio.)

## Commit escopado — nunca `git add -A`

O agente commita **apenas o que escreveu**, com caminhos explicitos. `git add -A` ou
`git add .` num loop varre alteracoes em andamento que nao sao dele e dispara gates
alheios. Se o pre-commit reclamar, **nao usar `--no-verify`** — o gate esta certo e o
`git add` provavelmente incluiu o que nao devia.

Um commit por item, referenciando a spec seguida.

## Fim de agente arruma a casa para o proximo

Ao encerrar, o agente atualiza o indice de conhecimento (incremental) e registra na
memoria o que aprendeu e **nao e derivavel do codigo**. Sem isso, o custo inteiro da
releitura e empurrado para o proximo agente e o desperdicio se repete a cada sessao.

## Condicao de parada

Definida no plano como **Definicao de Pronto** verificavel numa maquina limpa. Ao
satisfaze-la: escrever relatorio final, encerrar o loop (nao agendar nova iteracao) e
imprimir as instrucoes de execucao.

## Integracao com os demais protocolos

- **State Protocol:** o `PLANO.md` cumpre o papel de sprint validada — sem plano, sem loop.
- **Circuit Breaker:** o teto de 50% de contexto e a regra das 3 falhas sao disjuntores de
  token em nivel de iteracao.
- **Evidencia Sintetica:** verde no comando de verificacao e a evidencia; diario e
  divergencias sao a trilha.
- **Vetor de Contexto:** cada iteracao consulta o indice antes de ler arquivo.

## Criterio PASS

- Estado completo em disco (4 arquivos), reconstituivel apos reinicio de contexto
- Um item por iteracao, cada um com verificacao verde registrada no diario
- Divergencias registradas em vez de spec editada
- Commits escopados, sem `--no-verify`

## Criterio FAIL

- Estado operacional vivendo apenas na conversa
- Item marcado pronto sem verificacao verde, ou com teste afrouxado
- Agente editando a spec de origem
- `git add -A` / `git add .` dentro do loop
- Mesmo item repetido por mais de 3 iteracoes sem bloqueio

## Templates

`templates/loop/` — `PROTOCOLO-template.md`, `PLANO-template.md`, `DIARIO-template.md`,
`DIVERGENCIAS-template.md`, `PROMPT-LOOP-template.md`
