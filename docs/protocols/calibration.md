# Protocolo de Calibracao e Incerteza

## Missao

Impedir que o agente afirme com a mesma firmeza o que verificou e o que supos — tornando
o **grau de certeza** um dado explicito, derivado de evidencia e auditavel, em vez de um
tom de voz.

## Regra inegociavel

Toda conclusao tecnica declara seu **nivel de confianca** e a **classe de evidencia** que
o sustenta. Conclusao sem nivel declarado e tratada como `BAIXA`.

## Por que este protocolo existe

Os demais protocolos do framework sao binarios: PASS/FAIL, verde/vermelho,
CLEAR/WARNING/BLOCK. Isso e correto para gates, mas cria um ponto cego: entre "provado" e
"bloqueado" existe a maior parte do trabalho real — a inferencia razoavel. Sem calibracao,
uma resposta ancorada em teste executado e uma resposta ancorada em plausibilidade saem com
a mesma cara, e o revisor humano perde o unico sinal que lhe permitiria priorizar a
revisao.

Governanca por evidencia sem calibracao ainda deixa o agente parecer certo quando esta
apenas confortavel.

## Confianca nao e sensacao — e derivada da evidencia

O nivel **nao** e escolhido pelo agente por introspeccao. Ele e **lido** da classe de
evidencia disponivel. Isso e o que o torna auditavel.

| Nivel | Classe de evidencia que o autoriza | O que o agente pode fazer |
| --- | --- | --- |
| **ALTA** | Execucao verificada: teste verde, comando rodado com saida conferida, artefato inspecionado | Fechar item, afirmar sem ressalva |
| **MEDIA** | Fonte documental explicita e vigente: spec, ADR aceito, chunk `[SEED]`, contrato versionado | Prosseguir declarando a fonte; nao fecha item que exija prova de execucao |
| **BAIXA** | Inferencia, analogia com outro projeto, padrao "que costuma ser assim", leitura parcial | **Nao conclui.** Vira divergencia ou degrau extra de verificacao |

Regra de degradacao: quando fontes de niveis diferentes sustentam a mesma conclusao, vale
**a menor**. Uma cadeia com um elo inferido e uma conclusao inferida.

Regra de nao-promocao: **repetir uma inferencia nao a promove.** Consistencia interna do
modelo nao e evidencia; tres respostas iguais de baixa confianca continuam baixa confianca.

## Escada de verificacao proporcional

Confianca baixa nao autoriza responder e esperar revisao. Ela obriga **um degrau a mais de
prova antes de responder**:

1. **BAIXA → MEDIA:** localizar fonte documental que decida a questao (indice, spec, ADR).
   Se existir, citar e subir de nivel.
2. **MEDIA → ALTA:** executar o que prova (teste, comando, consulta ao schema). Se for
   executavel, executar e nao argumentar.
3. **Continua BAIXA apos os dois degraus:** a lacuna e real. Registrar como divergencia (em
   loop) ou pendencia de contexto (em sprint) com a decisao **mais conservadora** tomada
   para seguir — nunca preencher com o valor plausivel.

Corolario operacional: **se e barato executar, nao opine.** Discutir por dois paragrafos o
que um comando resolve em cinco segundos e desperdicio de token e de credibilidade.

## Gatilho de reconsulta

O framework e deliberadamente anti-pergunta em execucao autonoma (o loop nao pede
confirmacao para seguir). O gatilho de reconsulta e o contrapeso: cobre o eixo
**incerteza**, enquanto o gatilho de irreversibilidade cobre o eixo **risco**.

| Situacao | Acao obrigatoria |
| --- | --- |
| Consulta ao indice volta vazia, generica ou irrelevante | **Reformular** a consulta (outro vocabulario, outra entidade, outro nivel de abstracao) antes de escalar para leitura bruta |
| Segunda reformulacao tambem sem resultado util | Registrar **lacuna de contexto** e assumir `BAIXA`; nao presumir que "nao ha nada sobre isso" |
| Fontes recuperadas se contradizem | Nao escolher a mais conveniente: acionar `check_contradiction`, e persistindo o conflito, registrar divergencia |
| Confianca `BAIXA` **e** acao irreversivel (perda de dado, exposicao de dado pessoal, gasto financeiro, mudanca em producao) | **Parar e perguntar ao humano.** Unico caso em que o loop interrompe por incerteza |
| Confianca `BAIXA` e acao reversivel | Seguir com a decisao conservadora + divergencia registrada. Nao perguntar |

O que **nao** e gatilho de pergunta: preferencia de estilo, escolha entre alternativas
equivalentes, e qualquer coisa que a spec ja responde. Perguntar o que esta escrito e
falha de leitura, nao prudencia.

## Formato de declaracao

Em conclusao tecnica, resposta a humano e registro de item:

```
Confianca: ALTA | MEDIA | BAIXA — <classe de evidencia + referencia>
```

Exemplos:

- `Confianca: ALTA — make verificar verde em 2026-08-08, 143 testes`
- `Confianca: MEDIA — ADR-007 secao "Decisao"; nao executado neste ambiente`
- `Confianca: BAIXA — inferido do padrao dos modulos 02 e 03; sem fonte direta`

## Integracao com os demais protocolos

- **Evidencia Sintetica:** define *se* ha prova; este protocolo define *quanto* ela prova.
  Item so fecha com `ALTA` quando o criterio de aceite exige execucao.
- **Neural-Memory:** `check_contradiction` alimenta o gatilho de reconsulta; resultado
  fraco de `query_neural_memory` dispara reformulacao.
- **Loop Autonomo:** `BAIXA` + reversivel ⇒ `DIVERGENCIAS.md`; `BAIXA` + irreversivel ⇒
  parar e perguntar. Item nunca e marcado `[x]` com `BAIXA`.
- **Spec-First:** dado de dominio ausente e `BAIXA` por definicao ⇒ `[BLOQUEADO]`.
- **Circuit Breaker:** cadeia longa de conclusoes `BAIXA` encadeadas e sinal de alucinacao
  operacional — dispara o disjuntor antes do estouro de budget.

## Guard executavel (obrigatorio)

Este protocolo nao vive de disciplina. O framework diz que **diretriz sem guard nao esta
pronta** — entao a calibracao tem o seu:

```bash
python scripts/validate_calibration.py            # valida ./build
python scripts/validate_calibration.py --root <dir> --build-dir <dir>
```

Sem dependencia externa, de proposito: roda em qualquer projeto, qualquer stack.

| Codigo | O que bloqueia |
| --- | --- |
| `C1` | Entrada de `DIARIO.md` sem confianca declarada (ausencia = `BAIXA`) |
| `C2` | Item marcado `[x]` no `PLANO.md` com confianca `BAIXA` no diario |
| `C3` | Item marcado `[x]` sem entrada correspondente no diario |
| `C4` | Divergencia sem campo obrigatorio, ou com placeholder de template nao preenchido |
| `C5` | Divergencia **irreversivel** ainda pendente — devia ter sido pergunta ao humano, nao registro autonomo |
| `C6` | Divergencia sem as consultas ao indice tentadas (escada de verificacao nao percorrida) |

Arquivos ainda no estado de template e projetos sem loop sao ignorados (exit 0) — o guard
nao atrapalha quem nao usa o protocolo, e trava quem usa errado.

### Onde ele roda

1. **Pre-commit** — `templates/githooks/pre-commit`. Valida **o que esta em stage**,
   materializando o indice numa arvore temporaria: o que e checado e exatamente o que
   entraria no commit, nao o que esta aberto no editor.
2. **CI** — `.github/workflows/neural-flow-gates.yml`. Autoritativo, porque
   `core.hooksPath` e opt-in por clone: **guard que depende de configuracao de maquina nao
   e guard**.

Ativacao no projeto:

```bash
cp <neural-flow>/templates/githooks/pre-commit .githooks/pre-commit
cp <neural-flow>/scripts/validate_calibration.py scripts/
chmod +x .githooks/pre-commit
git config core.hooksPath .githooks
```

## Criterio PASS

- Toda conclusao tecnica do periodo carrega nivel de confianca e classe de evidencia
- Nenhum item fechado com confianca `BAIXA`
- Escada de verificacao percorrida antes de registrar lacuna (fonte buscada, execucao tentada)
- Reconsulta registrada quando o indice devolveu resultado fraco
- Toda combinacao `BAIXA` + irreversivel resultou em pergunta ao humano

## Criterio FAIL

- Afirmacao tecnica sem nivel declarado (tratada como `BAIXA` retroativamente)
- Inferencia apresentada com a mesma firmeza de execucao verificada
- Conclusao `BAIXA` promovida por repeticao ou por concordancia entre agentes
- Escalada para leitura bruta sem reformular a consulta ao indice
- Acao irreversivel executada sob `BAIXA` sem aprovacao humana

## Acao automatica em FAIL

- Rebaixar a conclusao a `BAIXA` e reabrir o item
- Exigir o degrau de verificacao que foi pulado
- Registrar a ocorrencia no delta da sprint (ou no `DIARIO.md`, em loop)
- Reincidencia no mesmo ciclo: acionar Circuit Breaker por alucinacao operacional
