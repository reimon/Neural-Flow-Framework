# Comece em 5 minutos

Este guia adota o Neural-Flow num projeto existente e faz um gate **bloquear de verdade**
na sua maquina. Nenhuma nuvem, nenhum `pip install`, nenhuma conta.

Pre-requisitos: `git` e `python3` (3.10+). Nada mais.

---

## 1. Copiar os guards (30 s)

Do repositorio do Neural-Flow para o seu projeto:

```bash
cd /caminho/do/seu/projeto
NF=/caminho/do/neural-flow-framework

mkdir -p scripts .githooks .github/workflows
cp $NF/scripts/nf_gate.py $NF/scripts/nf_guards.py $NF/scripts/validate_*.py scripts/
cp $NF/templates/githooks/pre-commit .githooks/
cp $NF/.github/workflows/neural-flow-gates.yml .github/workflows/
chmod +x .githooks/pre-commit
git config core.hooksPath .githooks
```

Confira o que voce acabou de instalar:

```bash
python3 scripts/nf_gate.py --list
```

## 2. Rodar antes de mudar qualquer coisa (10 s)

```bash
python3 scripts/nf_gate.py
```

Voce vai ver `nada a validar — OK` em quase tudo. **Isso e o comportamento correto**: o
guard trava quem usa o protocolo errado, nao quem ainda nao o usa. Adocao e incremental —
cada protocolo comeca a valer quando o primeiro artefato dele aparece.

## 3. Criar a primeira sprint (2 min)

```bash
mkdir -p docs/sprints
cp $NF/templates/sprint-template.md docs/sprints/sprint-01.md
```

Abra e preencha o Snapshot Operacional. O minimo para passar:

```markdown
- App/Escopo: `api de faturamento`
- Status: `em andamento`
- Data de inicio: `2026-08-08`
- Data planejada de conclusao: `2026-08-22`
- Ultima atualizacao: `2026-08-08`
- Nivel de autonomia: `A1`
- Blocker principal: `nenhum`
- Proxima acao: `modelar tabela de faturas`
```

Preencha tambem **Escopo incluido**, **Fora do escopo**, **Token budget** e pelo menos um
item numerado no **Checklist de Acoes**.

Rode de novo:

```bash
python3 scripts/nf_gate.py sprint budget
```

## 4. Ver o gate bloquear (1 min)

Agora provoque uma violacao real. Troque a autonomia para `A3` e coloque algo sensivel no
escopo:

```bash
sed -i.bak 's/`A1`/`A3`/; s/api de faturamento/rotacao de segredo no key vault/' \
  docs/sprints/sprint-01.md && rm docs/sprints/sprint-01.md.bak

git add docs/sprints/sprint-01.md
git commit -m "sprint 1"
```

O commit **e recusado**:

```
[S4] docs/sprints/sprint-01.md:2 — escopo sensivel (key vault, segredo) operando em A3 —
     manifesto exige A0/A1, salvo excecao formal registrada

Commit bloqueado pelos gates do Neural-Flow.
```

Isso e a regra de seguranca do manifesto virando codigo: mudanca em auth, segredo, infra,
billing ou dado pessoal nao roda em autonomia alta. Volte para `A1` e o commit passa.

> **Nunca use `--no-verify`.** Se o gate reclamou, ou o artefato esta errado, ou o
> `git add` levou o que nao devia.

## 5. Escolher o proximo protocolo (1 min)

Ligue um de cada vez, na ordem em que doer menos:

| Quero que o agente... | Crie | Guard que passa a valer |
| --- | --- | --- |
| Nao comece sem plano validado | `docs/sprints/*.md` | `sprint` |
| Nao estoure orcamento de tokens em silencio | Secao FinOps na sprint | `budget` |
| Nao contradiga decisao ja tomada | `docs/adr/ADR-001-*.md` | `adr` |
| Nao invente dado de dominio | `docs/modulos/*/spec.md` | `spec` |
| Nao aponte para arquivo que nao existe | (ja vale) | `context` |
| Declare o quanto tem certeza | `build/PLANO.md` + `DIARIO.md` | `calibration` |

Rode so o que interessa:

```bash
python3 scripts/nf_gate.py adr spec
NF_GUARDS="sprint adr" git commit -m "..."   # subconjunto no hook
```

## 6. Ensinar o agente (2 min)

Os guards travam o artefato; o `AGENTS.md` muda o comportamento:

```bash
cp $NF/templates/AGENTS-template.md AGENTS.md
cp $NF/templates/AI_SAFETY-template.md .github/AI_SAFETY.md
cp $NF/templates/MEMORY-template.md MEMORY.md
```

Preencha os blocos `<...>`. Esses tres arquivos sao lidos por qualquer ferramenta de IA
(Claude Code, Copilot, Cursor) e definem: o que nao reimplementar, o que exige confirmacao
humana, e o que ja foi decidido.

---

## Ajuste fino

`.neural-flow.json` na raiz do projeto:

```json
{
  "spec_sections": ["Proposito", "Dominio de dados", "Invariantes", "Criterios de aceite"],
  "spec_globs": ["docs/modulos/*/spec.md"]
}
```

Globs de sprint e ADR tambem sao configuraveis por linha de comando:

```bash
python3 scripts/nf_gate.py --help
python3 scripts/validate_sprint_state.py --glob 'planning/sprints/*.md'
```

## Onde ler mais

| Voce quer | Leia |
| --- | --- |
| Entender a filosofia | `README.md` |
| A regra completa de cada protocolo | `docs/protocols/README.md` |
| Como construir um projeto do zero | secao "Ordem de Construcao" no `README.md` |
| O que cada codigo de erro significa | o protocolo citado no rodape da mensagem |

## Problemas comuns

**O hook nao roda.** `git config core.hooksPath` e por clone — cada pessoa do time precisa
rodar. Por isso o CI existe: guard que depende de configuracao de maquina nao e guard.

**Guard reclama de um arquivo que e exemplo.** Arquivos com `TEMPLATE NEURAL-FLOW` no
cabecalho sao ignorados. Se for outro caso, ajuste o glob em `.neural-flow.json`.

**Falso positivo de referencia pendurada.** O guard `context` so cobra caminho cujo
diretorio-pai existe. Se ainda assim errar, o caminho provavelmente esta fora de bloco de
codigo — mova para dentro de crases triplas.
