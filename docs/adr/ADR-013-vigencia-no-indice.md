# ADR-013 - Vigencia das regras no indice

## Status

Aceito (Sprint 11)

## Contexto

O indice apontava uma politica de execucao retirada pelo ADR-012. O hash das
fontes correspondia ao repositorio e os arquivos historicos continuavam corretos.

## Decisao

Publicar separadamente as regras vigentes, as regras historicas e as relacoes de
superacao no indice. Resolver o escopo declarado em Status pelas secoes do
documento anterior. Um mapeamento versionado associa titulos antigos ao escopo.

## Alternativas consideradas

Editar o ADR antigo perderia a decisao original. Ocultar o documento inteiro
tambem removeria as regras que continuam vigentes em outros escopos.

## Consequencias

Adotantes regeneram o indice para ler o formato v2. A origem e os identificadores
de regras permanecem consultaveis no historico.

## Evidencia

- Data: 2026-11-27
- Autores: Codex
- Sprint de origem: Sprint 11
- Guard associado: `python3 scripts/nf_gate.py adr agentes`.
