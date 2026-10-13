# ADR-006 — Gateway de acoes para execucao de agentes

## Status

Aceito (Sprint 5)

## Contexto

Os protocolos existentes validam sprints, evidencias e divergencias, mas a execucao de
uma ferramenta ainda depende de o agente obedecer ao texto. O pre-commit bloqueia uma
consolidacao invalida, porem chega depois de comandos, chamadas externas ou mudancas
locais que podem ser sensiveis ou irreversiveis.

Tambem nao basta um campo Markdown dizendo que existe aprovacao. A fronteira precisa
conferir uma acao previamente permitida, o escopo da sprint e o nivel de risco antes de
entregar o comando ao sistema operacional.

## Decisao

Criar o Action Gateway com quatro regras executaveis:

1. Toda acao precisa existir em `.neural-flow/action-policy.json`, com `id`, comando
   permitido, sprint, item, risco e prazo.
2. O gateway valida a sprint escolhida com o State Protocol e rejeita acoes fora da
   allowlist ou fora do item declarado.
3. Acoes `sensitive` e `irreversible` exigem A0/A1 e confirmacao interativa em TTY para
   o hash exato do comando. Acoes desconhecidas sao rejeitadas, nunca inferidas como
   seguras.
4. Toda tentativa executada gera auditoria sem registrar o comando bruto, segredos ou
   argumentos sensiveis. A falta de capacidade de auditar tambem bloqueia a execucao.

O gateway e uma fronteira obrigatoria para os executores de ferramenta integrados ao
projeto. Ele nao e um sandbox de sistema operacional: um projeto que entrega shell cru
ao agente pode ser contornado, e deve revogar essa via para obter a garantia completa.

## Consequencias

Positivas:

- acoes safe pre-aprovadas avancam sem pergunta repetitiva;
- acoes sensiveis e irreversiveis param antes do subprocesso;
- a aprovacao fica vinculada ao comando, sprint, item e politica atuais;
- a auditoria prova a decisao e o resultado sem copiar o comando para o log.

Trade-offs:

- cada projeto precisa manter uma allowlist explicita;
- comandos genericos ou wrappers de shell sao deliberadamente dificeis de usar;
- a confirmacao TTY e um bloqueio operacional, nao uma identidade criptografica;
- a garantia nao cobre uma ferramenta externa que o agente consiga chamar fora do gateway.

Fora de escopo nesta etapa:

- sandbox OS, container ou policy engine externo;
- aprovacao assinada por identidade independente;
- inferencia confiavel de risco a partir de linguagem natural.

## Evidencia (Neural-Flow)

- Sprint de origem: `Sprint 5`
- Guard associado: `python3 scripts/nf_gate.py action` (G1-G5), coberto por
  `tests/test_action_gateway.py` e `tests/test_guards.py`
- Artefatos: `docs/protocols/action-gateway.md`, `scripts/nf_action_gateway.py`,
  `scripts/validate_action_policy.py`, `.neural-flow/action-policy.json`
