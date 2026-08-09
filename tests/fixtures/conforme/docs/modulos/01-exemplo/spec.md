# Spec do Modulo 01 — Catalogo

## 1. Proposito e fronteira

Expor catalogo de produtos para leitura publica.

## 2. Dominio de dados

Produto: id, nome, preco_centavos (inteiro), categoria_id.

## 3. Invariantes

- CAT-INV-001 — preco_centavos e sempre inteiro nao negativo.
- CAT-INV-002 — produto sem categoria nao aparece na listagem publica.

## 4. Fonte de verdade

Precos vem da tabela de precos vigentes, com data de verificacao.

## 5. Contratos e eventos

Produz `produto.publicado`; consumido pelo modulo de busca.

## 6. Modos de falha

Cache indisponivel devolve dados do banco; nunca relaxa visibilidade.

## 7. Linguagem segura

Nao prometer disponibilidade de estoque em tempo real.

## 8. Dependencias

Modulo de precos (interface + falso deterministico em desenvolvimento).

## 9. Governanca de LLM

Nao se aplica: modulo nao chama modelo.

## 10. Criterios de aceite

1. Listagem devolve 200 com no maximo 50 itens por pagina.
2. Produto sem categoria nao aparece na resposta, conforme CAT-INV-002.
3. Preco negativo e recusado na escrita, conforme CAT-INV-001.

## 11. Fora de escopo

Busca full-text e recomendacao.
