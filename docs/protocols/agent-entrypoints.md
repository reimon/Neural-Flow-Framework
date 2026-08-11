# Portas de Entrada de Agente

## Missao

Garantir que **qualquer** ferramenta de IA que abra o projeto — Claude Code, Codex,
Gemini, Copilot, Cursor, Cline, Windsurf, Aider, Amp, Hermes — chegue as mesmas
diretrizes, na mesma ordem, sem que ninguem precise lembrar de contar isso a ela.

## O problema que resolve

Cada ferramenta le um arquivo diferente na raiz do projeto. Um repositorio que so tem
`CLAUDE.md` esta governado para exatamente um agente; todo o resto opera por conta
propria e reimplementa o que ja existe — o erro mais caro que agentes cometem.

A tentacao e escrever as diretrizes em cada um dos arquivos. Nove copias da mesma regra
divergem na terceira edicao, e a partir dai cada agente segue uma versao diferente do
projeto. Isto e o mesmo vetor que o framework ja registra em `MEMORY.md`: duplicar
comando operacional propagou uma forma errada para dezenas de arquivos.

## Regra inegociavel

**Uma fonte, muitas portas.** `AGENTS.md` e a unica fonte de verdade das diretrizes.
Toda porta de entrada e um arquivo **gerado**, curto, que manda o agente para la e
carrega apenas as cinco regras que valem antes de qualquer leitura.

Corolario: **nao se edita uma porta de entrada.** Editar `GEMINI.md` para mudar uma
diretriz e criar uma regra que so o Gemini conhece. Edite `AGENTS.md` e regere:

```bash
python3 scripts/nf_agentes.py --escrever
```

Este comando toca **so** as portas. Nao use `nf_install.py --force` para consertar uma
porta: `--force` sobrescreve todo artefato, inclusive o `AGENTS.md` e o `MEMORY.md` que o
time preencheu a mao.

## Portas cobertas

| Arquivo | Quem le |
| --- | --- |
| `AGENTS.md` | Fonte de verdade. Codex, Jules, Devin e Factory leem direto daqui |
| `CLAUDE.md` | Claude Code — **ancora**, nao stub: carrega os principios de execucao |
| `GEMINI.md` | Gemini CLI, Gemini Code Assist |
| `.github/copilot-instructions.md` | GitHub Copilot |
| `.cursor/rules/neural-flow.mdc` | Cursor (`alwaysApply: true`) |
| `.clinerules` | Cline |
| `.windsurfrules` | Windsurf |
| `AGENT.md` | Amp, Zed |
| `CONVENTIONS.md` | Aider |
| `HERMES.md` | Hermes, OpenClaw |

O corpo canonico de todas elas vive em `scripts/nf_agentes.py`. Ferramenta nova entra
adicionando uma linha em `PORTAS` — nunca escrevendo um arquivo a mao.

## Indice de regras

A primeira instrucao de toda porta e **consultar o indice antes de ler** — a regra de
entrada do protocolo Vetor de Contexto. Para que essa instrucao nao aponte para o vazio,
o instalador gera `.neural-flow/indice-regras.md` e `.json`: uma linha por regra, com a
fonte (`arquivo:linha`) e o guard que a trava.

O indice e **deterministico e em stdlib pura** (ADR-002): existe desde o minuto zero,
sem rede e sem LLM, e continua valendo quando o grafo do `graphify` nao subiu. Quando o
grafo sobe, o indice entra como corpus — as regras viram nos com fonte rastreavel, e a
consulta passa a ser `graphify query`, com o `.md` como fallback.

Regenerar: `python3 scripts/nf_indice_regras.py`. O JSON grava a impressao digital das
fontes; se um documento de governanca muda e o indice nao e regerado, o guard trava.

## Gate primario

`agentes` — `scripts/validate_agent_entrypoints.py`, no `nf_gate` e no pre-commit.

| ID | O que trava |
| --- | --- |
| P1 | Porta de entrada conhecida ausente |
| P2 | Porta divergente do corpo canonico, ou de versao anterior |
| P3 | Porta que aponta para arquivo inexistente |
| P4 | `CLAUDE.md` que nao cita `AGENTS.md` |
| P5 | Indice de regras ausente ou desatualizado em relacao as fontes |

Ausencia de `AGENTS.md` = governanca nao instalada = nada a validar (exit 0), como nos
demais guards.

## Falha critica

Um agente operando num projeto Neural-Flow **sem** ter lido `AGENTS.md`. O sintoma tipico
nao e um erro: e codigo plausivel que reimplementa infraestrutura existente e passa na
revisao humana porque parece razoavel.
