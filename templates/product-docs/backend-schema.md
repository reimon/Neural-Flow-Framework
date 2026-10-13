> TEMPLATE Neural-Flow
> Modelo oficial do esquema backend. Tipos e relacoes devem refletir decisoes confirmadas.

# Esquema Backend — <nome do produto>

## Identificacao
- **Versao do PRD/TRD coberta:** a preencher
- **Banco ou persistencia:** a preencher ou nao se aplica com justificativa
- **Status:** rascunho | revisao | aprovado
- **Ultima revisao:** AAAA-MM-DD

## Visao geral e fronteiras
Descreva a persistencia, os servicos que a acessam e os limites de responsabilidade.

## Entidades
IDs `ENT-001`, `ENT-002`... Explique propriedade, ciclo de vida e requisito atendido.

## Tabelas, colecoes e campos
| Entidade | Campo | Tipo | Obrigatorio | Restricao/indice | Origem |
|---|---|---|---|---|---|
| a preencher | a preencher | pendente | pendente | pendente | pendente |

Para cada tabela/colecao, liste todos os campos, tipos, valores nulos, defaults, chaves,
unicidade, indices e regras de retencao. Nao invente nomes de tabelas reais.

## Relacionamentos e integridade
| Origem | Destino | Cardinalidade | Chave | Regra de exclusao |
|---|---|---|---|---|
| a preencher | a preencher | pendente | pendente | pendente |

## Acesso aos dados e contratos
Identifique produtores e consumidores, operacoes, transacoes, eventos e validacao de
entrada. Inclua APIs ou consultas relevantes, sem registrar segredos.

## Autenticacao, sessoes e autorizacao
Descreva provedor, cadastro/login, tokens ou cookies, duracao e revogacao de sessao,
recuperacao de conta, papeis e permissao por recurso. Se nao se aplica, explique o limite
de acesso usado no lugar.

## Privacidade e seguranca
Classificacao de campos sensiveis, isolamento entre usuarios/tenants, criptografia,
auditoria, retencao, exclusao e modos de falha seguros.

## Migracoes, backup e recuperacao
Estrategia de evolucao do schema, compatibilidade, backup e restauracao.

## Decisoes pendentes e referencias
- **PEND-001:** tabela, campo ou regra ainda nao decidida, impacto e responsavel.
- Link para PRD, TRD, Fluxo do App, UI/UX Design e Plano de Implementacao.
