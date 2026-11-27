# Action Gateway

## Missao

Colocar uma fronteira executavel entre um agente e o sistema operacional. O agente pode
avancar em acoes previamente permitidas e para antes de risco sensivel ou irreversivel.

## Regra inegociavel

Acao que nao existe na politica e acao negada. Nenhum comando e inferido como seguro por
ser comum, curto ou sugerido pelo agente.

## Contrato

O arquivo `.neural-flow/action-policy.json` contem:

- `version`: deve ser `2`;
- `enabled`: precisa ser `true` para executar;
- `actions`: allowlist de acoes;
- `audit_path`: caminho relativo para o diario de tentativas.

Cada acao declara `id`, `description`, `sprint`, `item`, `risk`, `argv`,
`requires_human_approval` e `max_runtime_seconds`.

`argv` e a lista completa, incluindo o executavel. A lista recebida deve ser
identica a cadastrada, inclusive no modo `--plan`. O guard rejeita executaveis de
shell, `sudo` e flags de execucao arbitraria. O gateway executa com `shell=False`.

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
  --sprint docs/sprints/sprint-09-remover-sandbox-do-gateway.md \
  -- python3 -m unittest discover -s tests
```

Para uma acao sensivel ou irreversivel, o gateway exige terminal interativo e o
desafio mostrado para o comando exato.

## Guard executavel

```bash
python3 scripts/nf_gate.py action
python3 scripts/nf_action_gateway.py --plan --action run-tests \
  --sprint docs/sprints/sprint-09-remover-sandbox-do-gateway.md \
  -- python3 -m unittest discover -s tests
```

O guard `action` valida o contrato sem executar comandos. O gateway valida novamente a
politica e a sprint no momento da acao. A duplicacao e intencional na fronteira: o guard
protege o commit; o gateway protege a execucao.

## Instalacao e migracao da politica

Em uma instalacao nova, cadastre os comandos do projeto antes de mudar `enabled`
para `true`. O instalador preserva a politica existente na reinstalacao padrao.

Para atualizar uma instalacao v1, preserve uma copia da politica e atualize os
scripts gerenciados pelo Neural-Flow junto da politica. A reinstalacao padrao
tambem preserva scripts existentes. Revise o diff da atualizacao antes de aplicar
os arquivos novos sobre a instalacao anterior.

1. Se a equipe exige isolamento, configure-o no executor antes de habilitar a v2.
   Considere as regras de arquivos, processos e rede da politica anterior.
2. Para cada acao, substitua `argv_prefix` pelo `argv` completo. Separe comandos
   diferentes em acoes distintas. Preserve o risco, o prazo, a sprint e o item.
3. Remova `execution` e os campos `network` e mude `version` para `2`. Rode o
   guard `action` e confira os comandos permitidos com `--plan`.

A v1 falha na validacao e no gateway, inclusive em `--plan`, ate a migracao.

## Limite declarado

O gateway controla apenas as chamadas que passam por ele. A confirmacao TTY exige
interacao no terminal. A autenticacao independente do aprovador e o isolamento de
arquivos, rede e processos filhos dependem do ambiente de execucao.
