# ADR-005 — Grafo do graphify neste repositorio: nao agora

## Status

Proposto

## Contexto

O protocolo Vetor de Contexto manda consultar o indice antes de ler qualquer arquivo, e
cita o grafo de conhecimento do `graphify` como ponto de entrada mais barato que a leitura
bruta — com ganho medido em campo de ~48x em corpus documental de porte medio.

A Sprint 2 entregou `.neural-flow/indice-regras.md`: deterministico, em stdlib pura, com
uma linha por regra e a fonte (`arquivo:linha`). A pergunta que ficou em aberto foi se este
repositorio deve **tambem** manter um grafo do `graphify`.

Os numeros deste repositorio, medidos e nao estimados:

- 64 regras indexadas, ~150 arquivos versionados, dos quais ~30 sao documentacao de
  governanca — corpus pequeno, muito abaixo do porte em que o ganho de 48x foi observado;
- a telemetria da Sprint 2 mostra **98,8% do contexto vindo de cache** e entrada "fria" de
  431 tokens em 227 requisicoes. O custo desta base de codigo **nao esta em le-la**.

O grafo tambem tem custo que o indice deterministico nao tem: depende de LLM e de rede
(viola o espirito do ADR-002 para qualquer coisa que entre no caminho do gate), precisa de
reindexacao a cada mudanca relevante, e envelhece em silencio — grafo desatualizado
responde com confianca sobre uma estrutura que nao existe mais.

## Decisao

**Nao subir o grafo do `graphify` sobre este repositorio nesta etapa.** O indice
deterministico cobre a regra de entrada, e a medicao mostra que o gargalo aqui e geracao,
nao leitura: um grafo reduziria um custo que nao estamos pagando.

A recomendacao para **projetos adotantes** permanece inalterada e continua nos protocolos:
corpus documental grande e a situacao em que o grafo se paga, e a etapa "Indexar" da ordem
de construcao continua apontando para ele.

Gatilhos que reabrem esta decisao — qualquer um basta:

1. o repositorio passar de ~300 arquivos ou ~100 documentos de governanca;
2. a telemetria mostrar aproveitamento de cache abaixo de ~80% de forma sustentada, sinal
   de que o contexto esta sendo relido;
3. surgir pergunta recorrente de relacao entre modulos que o indice de regras nao responde.

## Consequencias

Positivas:

- nenhuma dependencia de LLM ou rede no caminho de entrada do agente neste repositorio
- nada de artefato gerado que envelhece sem ninguem perceber
- a decisao fica com gatilho objetivo, em vez de virar pendencia perpetua

Trade-offs:

- perde-se a deteccao de comunidades, que ja revelou em outro projeto conexoes que ninguem
  pensaria em consultar. Aceito conscientemente: com ~30 documentos, a chance de conexao
  nao percebida e baixa
- o framework recomenda aos outros uma ferramenta que ele proprio nao usa — mitigado por
  este ADR, que explica **por que** o caso dele e diferente, em vez de silenciar

Fora de escopo nesta etapa:

- remover a mencao ao `graphify` dos protocolos ou da ordem de construcao
- decidir a mesma coisa para projetos adotantes

## Evidencia (Neural-Flow)

- Sprint de origem: `Sprint 3`
- Guard associado: `nao aplicavel` — e decisao de nao adotar ferramenta; nao ha invariante
  estrutural a travar. Os gatilhos de reabertura sao revisao humana, nao lint.
- Artefatos: `.neural-flow/indice-regras.md`, `docs/protocols/context-vector.md`,
  `docs/sprints/sprint-02-autogovernanca.md` (secao FinOps, medicao de cache)
- `Confianca: ALTA` para os numeros (medidos com `nf_tokens.py` e contagem de arquivos);
  `Confianca: MEDIA` para o juizo de que o ganho nao compensa — deriva dos numeros, mas o
  limiar de corte e julgamento, nao medicao.
