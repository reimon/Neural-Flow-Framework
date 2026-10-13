# ADR-008 — Adaptadores de sandbox validados por plataforma

## Status

Aceito (Sprint 5)

Supera ADR-007

## Contexto

O ADR-007 aprovou `sandbox-exec` como adaptador macOS. A ferramenta e depreciada, e o
perfil testado permitia iniciar processos de forma ampla. Isso nao prova isolamento
adequado nem impede shell direto fora do gateway. O desafio TTY tambem nao autentica uma
pessoa separada do agente.

## Decisao

1. O modo `required` so executa com adaptador suportado, validado por testes de filesystem,
   rede e processos filhos.
2. Nenhum adaptador de sandbox e considerado validado neste momento. A politica ativa usa
   `required`, portanto o gateway falha fechado ate haver implementacao aprovada.
3. `sandbox-exec` e removido do caminho de execucao por ser depreciado.
4. `when-available` e explicitamente best-effort e nao pode sustentar afirmacao de
   isolamento ou seguranca completa.
5. A aprovacao de acoes sensiveis precisa vir de canal independente do agente; TTY e apenas
   protecao contra execucao desassistida.
6. Linux, Windows e macOS terao adaptadores proprios, escolhidos e verificados conforme as
   capacidades e limites de cada sistema.

## Consequencias

- Nao se afirma que existe sandbox multiplataforma antes de testes reais em cada sistema.
- A politica atual interrompe execucao de comandos via gateway enquanto o adaptador
  requerido nao estiver disponivel.
- Os adaptadores futuros terao contratos e testes comuns, sem simular recursos ausentes.

## Evidencia (Neural-Flow)

- Sprint de origem: `Sprint 5`
- Supera: `ADR-007`
- Guard associado: `python3 scripts/nf_gate.py action`; `tests/test_action_gateway.py`
  verifica bloqueio fail-closed quando nao ha adaptador validado.
- Artefatos: `scripts/nf_sandbox.py`, `scripts/nf_action_gateway.py`,
  `docs/protocols/action-gateway.md`
