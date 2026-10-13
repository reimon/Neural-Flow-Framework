# Protocolo de Base Documental do Produto

## Missao

Registrar o contrato do produto em seis documentos que orientam a especificacao dos
modulos e a sequencia das sprints. O instalador encontra e compara documentos, mostra os
modelos no dashboard e preserva os arquivos ja existentes.

## Os seis papeis

| ID | Documento | Responsabilidade |
|---|---|---|
| PD1 | PRD | Visao do produto, usuarios, requisitos, metas e limites da versao |
| PD2 | TRD | Arquitetura, decisoes tecnicas, operacao e custo de manutencao |
| PD3 | Fluxo do App | Perfis, jornadas, navegacao e estados alternativos |
| PD4 | UI/UX Design | Sistema visual, componentes, telas, estados e acessibilidade |
| PD5 | Esquema Backend | Entidades, campos, relacoes, autenticacao e autorizacao |
| PD6 | Plano de Implementacao | Itens ordenados, dependencias, requisitos e aceite verificavel |

Os seis modelos oficiais ficam em `templates/product-docs/`. O instalador copia os mesmos
conteudos para `.neural-flow/product-examples/`; o dashboard mostra esses arquivos. O
modelo e referencia, nao documento do projeto.

## Descoberta e mapeamento

- Procurar Markdown no projeto e na documentacao, excluindo dependencias, arquivos
  gerados, historico `old/` e modelos do framework.
- Descobrir equivalencia por nome conhecido ou cobertura de secoes. Empate vira ambiguidade
  e pede mapeamento, nunca escolha silenciosa.
- `.neural-flow.json` aceita `product_docs.documents.<id>.path` e, opcionalmente,
  `product_docs.documents.<id>.sections` para mapear titulos locais aos titulos padrao.
- Um mesmo arquivo pode cumprir papeis diferentes por mapeamentos explicitos de secoes.
- Caminho mapeado precisa ficar dentro da raiz do projeto.

## Diagnostico e estados

O diagnostico e uma leitura estrutural deterministica, sem servico externo e sem escrever
nos documentos do projeto. Cada papel mostra arquivo, secoes faltantes, conteudo ainda em
placeholder, candidatos ambiguos, estado da revisao e proxima acao. IDs, dependencias,
ordem e referencias verificaveis do plano sao comparados entre os documentos.

Estados de estrutura: `ausente`, `ambiguo`, `incompleto`, `completo` e `nao_se_aplica`.
Estados exibidos: `ausente`, `incompleto`, `aguardando_revisao`, `aprovado` e
`alterado_apos_aprovacao`. "Completo" comprova apenas os campos e secoes exigidos por
maquina; coerencia, cobertura de produto e adequacao dependem da revisao da IA e do
usuario.

O diagnostico pode ser lido pela instalacao, pelo dashboard e pela CLI:

```text
python3 scripts/nf_product_docs.py --root . --format text
python3 scripts/nf_product_docs.py --root . --format json
```

## Revisao, aprovacao e vigencia

- A IA revisa cobertura da versao atual, coerencia entre documentos, lacunas e decisoes
  pendentes. A IA nao se aprova.
- A aprovacao explicita do usuario e registrada por papel em `.neural-flow.json`, com hash
  do conteudo, nome declarado, data e referencia da evidencia de aprovacao.
- A alteracao do conteudo ou do mapeamento invalida somente a aprovacao afetada.
- `--approve <id> --by <nome> --evidence <referencia>` registra aprovacao somente para
  documento estruturalmente completo.
- `--not-applicable <id> --by <nome> --evidence <justificativa>` registra ausencia
  justificada. O registro e vinculado ao hash da justificativa.
- O hash do Plano de Implementacao ignora apenas marcadores `[ ]`/`[x]` e a secao
  operacional `Acompanhamento das sprints`. Requisitos, aceite, itens e dependencias
  continuam protegidos pela aprovacao.
- Nome de revisor e referencia de evidencia sao um registro audivel, nao autenticacao
  criptografica de uma pessoa.

## Relacao com sprints

- A adocao documental comeca ativa em projetos sem Neural-Flow previo. Instalacoes ja
  governadas mantem a configuracao atual ate a adocao explicita.
- Preparacao documental pode rodar com base incompleta. Uma sprint classificada como
  `implementacao` so pode estar `em andamento` com todos os seis papeis aprovados ou com
  justificativa de nao aplicabilidade aprovada.
- Cada linha de implementacao do plano mestre usa ID `IMP-NNN`, ordem unica, dependencia
  explicita, requisitos `REQ-NNN` e criterios `CA-NNN`. Dependencia deve anteceder o item;
  referencias precisam existir.
- A sprint de implementacao referencia os IDs do plano mestre e requisitos atendidos. O
  estado da execucao fica na sprint e em `build/PLANO.md`, sem reescrever o contrato mestre.
- Sprints anteriores a adocao nao sao reclassificadas automaticamente.

## Limites

- O diagnostico compara documentos com modelos; nao afirma que o codigo implementado
  esteja em conformidade com eles.
- Um estado estruturalmente `completo` nao substitui avaliacao semantica humana.
- O instalador nao sobrescreve documentos do adotante. Modelos do Neural-Flow ficam
  separados em `.neural-flow/product-examples/` e incorporados ao dashboard offline.
