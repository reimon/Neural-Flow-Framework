# Action Gateway

## Missao

Colocar uma fronteira executavel entre um agente e o sistema operacional. O agente pode
avancar em acoes previamente permitidas e para antes de risco sensivel ou irreversivel.

## Regra inegociavel

Acao que nao existe na politica e acao negada. Nenhum comando e inferido como seguro por
ser comum, curto ou sugerido pelo agente.

## Contrato

O arquivo `.neural-flow/action-policy.json` contem:

- `version`: atualmente `1`;
- `enabled`: precisa ser `true` para executar;
- `actions`: allowlist de acoes;
- `audit_path`: caminho relativo para o diario de tentativas.
- `execution.sandbox`: `required`, `when-available` ou `off`; em `required`, a ausencia
  de sandbox do host bloqueia a execucao;
- `execution.network`: pedido de permissao de rede; so e aplicado por um adaptador
  validado, nunca pelo gateway Python sozinho.

Cada acao declara `id`, `description`, `sprint`, `item`, `risk`, `argv_prefix`,
`requires_human_approval` e `max_runtime_seconds`. `network` e opcional e so sera uma
restricao efetiva quando o adaptador do host a aplicar.

`argv_prefix` e uma lista de argumentos, nunca uma string de shell. `sh`, `bash`, `zsh`,
`sudo`, `-c` e equivalentes sao rejeitados pelo guard. O gateway executa com
`shell=False`.

## Riscos

| Risco | Comportamento |
| --- | --- |
| `safe` | executa se a acao estiver na allowlist, na sprint ativa e no item correto |
| `sensitive` | exige sprint A0/A1, TTY e confirmacao para o hash exato |
| `irreversible` | exige sprint A0/A1, TTY e confirmacao para o hash exato |

Acao desconhecida, politica desabilitada, sprint invalida, item ausente, allowlist
divergente ou auditoria indisponivel resulta em bloqueio.

## Fluxo

```text
agente → nf_action_gateway.py
          ├─ politica valida?
          ├─ sprint validada?
          ├─ item e argv permitidos?
          ├─ safe → executa
          └─ sensitive/irreversible → TTY + confirmacao do desafio → executa
                                      └─ sem confirmacao → bloqueia
```

Uso:

```bash
python3 scripts/nf_action_gateway.py \
  --action run-tests \
  --sprint docs/sprints/sprint-05-gateway-de-acoes.md \
  -- python3 -m unittest discover -s tests

python3 scripts/nf_action_gateway.py \
  --action git-push \
  --sprint docs/sprints/sprint-05-gateway-de-acoes.md \
  -- git push origin main
```

O segundo comando so continua em terminal interativo depois que o humano digitar o
desafio mostrado para aquele comando exato. Em CI, pipe, cron ou terminal sem TTY ele
falha fechado.

## Guard executavel

```bash
python3 scripts/nf_gate.py action
python3 scripts/nf_action_gateway.py --plan --action run-tests \
  --sprint docs/sprints/sprint-05-gateway-de-acoes.md \
  -- python3 -m unittest discover -s tests
```

O guard `action` valida o contrato sem executar comandos. O gateway valida novamente a
politica e a sprint no momento da acao. A duplicacao e intencional na fronteira: o guard
protege o commit; o gateway protege a execucao.

Quando `execution.sandbox` esta em `required`, o gateway so executa se houver adaptador
validado para o sistema operacional. Neste momento nao ha adaptadores habilitados para
macOS, Linux ou Windows; por isso, a politica deste repositorio bloqueia execucao via
gateway ate essa implementacao. `when-available` e best-effort, nao oferece garantia e
grava `sandbox: unavailable` na auditoria.

## Limite declarado

O gateway controla apenas o caminho que passa por ele. A confirmacao TTY impede execucao
desassistida, mas nao autentica uma pessoa separada do agente. O sistema operacional deve
isolar o processo do agente para impedir shell direto e garantir escrita, rede e processos
filhos. Ate um broker de aprovacao separado e adaptadores de sandbox serem integrados e
testados em cada plataforma, nao se declara garantia completa.
