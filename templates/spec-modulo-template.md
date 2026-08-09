# Spec do Modulo <NN> — <Nome>

> TEMPLATE Neural-Flow (`docs/protocols/spec-first.md`). A estrutura abaixo e **minima e
> obrigatoria** — um validador executavel a verifica no pre-commit, para todos os modulos,
> descobrindo-os pelo diretorio. Adapte o conjunto de secoes ao seu dominio uma vez, em
> `PADRAO-ESPECIFICACAO-<escopo>.md`, e nao abra excecao por conveniencia.

## 1. Proposito e fronteira

O que este modulo resolve, e **o que explicitamente nao resolve**.

## 2. Dominio de dados

Entidades, campos, tipos e unidades. Regras:

- Valor monetario e inteiro na menor unidade (centavos) — nunca float.
- **Dado vivo nao vira constante permanente** em DDL ou regra: valor mutavel mora na base
  de referencia, com `source` e `last_verified`.

## 3. Invariantes

`<PREFIXO>-INV-NNN` — uma linha cada, testavel. Sao o contrato que nenhum caminho pode
violar, inclusive os degradados.

**Toda invariante precisa ser citada em outro lugar** — num criterio de aceite, num
contrato, num teste. Invariante definida e nunca referenciada e spec morta, e o guard
reprova (P5). O inverso tambem: citar um ID que nao existe e referencia pendurada.

## 4. Fonte de verdade

Para cada valor, prazo ou regra regulada: de onde vem, com data de verificacao. **Sem
fonte, o sistema responde "dados insuficientes"** — nunca um numero plausivel.

## 5. Contratos e eventos (bilaterais)

Evento declarado por um lado so **nao e contrato** — vira "pendencia registrada" ate a
contrapartida existir. Liste produtor, consumidor, payload e garantia de entrega.

## 6. Modos de falha (falha fechada)

Para cada dependencia: o que acontece quando ela cai. Cache, fila ou fallback **nunca**
relaxam autorizacao, consentimento ou mascaramento.

## 7. Linguagem segura

Frases proibidas na UI e nas mensagens (prometer resultado, elegibilidade final, prazo
garantido, aconselhamento profissional regulado) e as formulacoes aceitas no lugar.

## 8. Dependencias

Modulos e servicos externos. Todo servico externo entra como **interface + falso
deterministico**; a implementacao real fica atras de variavel de ambiente.

## 9. Governanca de LLM (se o modulo chama modelo)

Cota por feature, fallback, teto de custo e registro de auditoria. **Modulo que chama LLM
sem isto esta incompleto** — foi a lacuna mais comum encontrada em inventario de reuso.

## 10. Criterios de aceite

Verificaveis, numerados, sem adjetivo. Sao o que o item do `PLANO.md` vai referenciar —
e onde as invariantes da secao 3 sao citadas:

1. `<criterio>`, conforme `<PREFIXO>-INV-001`.
2. `<criterio>`, conforme `<PREFIXO>-INV-002`.

## 11. Fora de escopo

Nominalmente, o que este modulo nao fara — para o agente nao ampliar sozinho.
