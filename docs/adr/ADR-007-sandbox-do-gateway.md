# ADR-007 — Sandbox obrigatoria no caminho de execucao

## Status

Aceito (Sprint 5)

## Contexto

O ADR-006 criou o Action Gateway, mas deixou explicito que uma ferramenta externa
poderia ignorar o gateway e chamar o shell diretamente. Isso impede afirmar isolamento
de ambiente no caminho que executa a acao.

## Decisao

1. A politica pode declarar `execution.sandbox` como `required`, `when-available` ou
   `off`.
2. Em `required`, o gateway usa o sandbox nativo disponivel no host e falha fechado
   quando ele nao existe.
3. No macOS, `sandbox-exec` permite leitura do sistema, execucao de processos e escrita
   apenas no workspace. A rede permanece negada por padrao.
4. Uma acao so libera rede quando declara `network: true` na allowlist. Isso nao remove
   a aprovacao humana de acoes sensiveis ou irreversiveis.
5. A sandbox protege o caminho que passa pelo gateway. O bloqueio de qualquer shell
   fora dele continua sendo responsabilidade do host, container ou executor do agente.

## Consequencias

- O projeto pode exigir isolamento real sem fallback silencioso.
- Ambientes sem sandbox precisam instalar ou fornecer um executor compativel antes de
  habilitar a politica.
- O gateway continua portavel: `when-available` permite adocao gradual, mas nao e uma
  garantia de isolamento.
- O teste de fronteira prova que escrita fora do workspace e bloqueada quando o recurso
  esta disponivel.

## Evidencia (Neural-Flow)

- Sprint de origem: `Sprint 5`
- Guard associado: `python3 scripts/nf_gate.py action` (G1-G5), com
  `scripts/nf_sandbox.py` e `tests/test_action_gateway.py` cobrindo sandbox e fail-closed
- Artefatos: `docs/protocols/action-gateway.md`, `scripts/nf_action_gateway.py`,
  `scripts/nf_sandbox.py`, `scripts/validate_action_policy.py`,
  `.neural-flow/action-policy.json`
