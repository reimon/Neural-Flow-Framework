# Protocolo Spec-First

## Missao

Garantir que a especificacao exista, esteja completa e passe em gate automatico **antes**
de existir codigo — porque com geracao assistida por IA o gargalo migrou: escrever codigo
e a parte barata; decidir o que construir e provar que a decisao esta registrada e o caro.

## Regra inegociavel

Codigo de produto nao comeca sem spec aprovada no padrao obrigatorio. Onde a spec nao
responde, o agente **nao preenche** — registra divergencia e para no item.

Corolario: **a especificacao e entrada, nao saida.** O agente que constroi nao edita
`docs/`. Spec editada pelo executor deixa de ser contrato e vira racionalizacao do que
ele ja fez.

## Por que este protocolo existe

Quando a spec esta pronta, o codigo sai dela. Quando nao esta, o agente preenche o vazio
com o que soa razoavel. Em dominio regulado (imigracao, saude, financeiro, juridico),
"soar razoavel" e o modo de falha mais caro que existe — produz numero plausivel e errado,
com a mesma confianca de um numero correto.

## Estrutura minima de spec

Cada modulo/dominio declara um conjunto **fixo** de artefatos (dominio de dados,
invariantes, contratos, eventos, criterios de aceite...). O conjunto e definido uma vez em
`PADRAO-ESPECIFICACAO-<escopo>.md` e vale para todos — sem excecao por conveniencia.

Principios que o padrao deve exigir (validados em campo):

| Principio | O que ele proibe na pratica |
| --- | --- |
| Fonte de verdade | Valor, prazo ou regra sem apontar para a base de dados de referencia e sua data de verificacao |
| Dados vivos separados | Valor mutavel codificado como constante permanente em DDL ou regra de negocio |
| Contratos bilaterais | Evento declarado por um lado so — dependencia sem contrapartida vira "pendencia registrada", nunca contrato fechado |
| Falha fechada | Cache, fila ou fallback relaxando autorizacao, consentimento ou mascaramento |
| Linguagem segura | Prometer resultado, elegibilidade final, prazo garantido ou aconselhamento profissional regulado |

## Gate automatico (obrigatorio)

Um validador executavel verifica **todos** os modulos, acionado por hook de pre-commit.
Dois detalhes de implementacao que fazem o gate funcionar de verdade:

1. **Validar o que esta em stage, nao a arvore de trabalho.** Materializar o indice numa
   arvore temporaria e rodar la. O que e checado e exatamente o que entraria no commit —
   nao o que esta aberto no editor.
2. **Descobrir os modulos pelo diretorio, nao por lista fixa.** Modulo novo nao pode
   nascer sem gate por esquecimento de alguem.

Ativacao do hook: `git config core.hooksPath .githooks`

## Inventario de reuso antes de construir

Antes de escrever modulo novo, produzir um **mapa de cobertura**: o que cada ativo
reutilizavel ja resolve, contra o que as specs pedem, com o impedimento declarado no topo
(stack, licenca, acoplamento) e os caminhos possiveis, cada um com seu custo.

O inventario nao e burocracia de reuso — **e como se descobre o que falta**. Num caso real
ele revelou que varios modulos chamavam LLM e nenhum especificava cota, fallback ou custo
por feature: governanca de LLM era lacuna, nao refinamento.

## Escopo negativo declarado

Todo plano declara nominalmente uma secao **"Fora do escopo"**. Escopo sem fronteira
explicita e escopo que o agente amplia sozinho — sempre com boa intencao, sempre na
direcao errada.

## Criterio PASS

- Todo modulo com codigo possui spec completa no padrao, aprovada antes do codigo
- Validador de spec verde para todos os modulos no pre-commit
- Mapa de cobertura de reuso registrado antes da construcao
- Plano com secao "Fora do escopo" preenchida nominalmente

## Criterio FAIL

- Codigo de produto sem spec correspondente
- Spec editada pelo agente executor
- Validador desativado, contornado com `--no-verify` ou rodando so na arvore de trabalho
- Valor de dominio inventado onde a base de referencia nao tinha o dado

## Acao automatica em FAIL

- Item volta a pendente e o commit e bloqueado pelo hook
- Dado de dominio ausente: item marcado `[BLOQUEADO]`, nunca preenchido com valor plausivel
- Divergencia registrada em arquivo proprio com a decisao conservadora tomada

## Templates

- `templates/spec-modulo-template.md` — estrutura minima de spec
- `templates/loop/PLANO-template.md` — plano com Definicao de Pronto e escopo negativo
