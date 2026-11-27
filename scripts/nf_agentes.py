#!/usr/bin/env python3
"""
Neural-Flow Framework — portas de entrada de agente
===================================================
Cada ferramenta de IA le um arquivo diferente na raiz do projeto: o Claude Code
le `CLAUDE.md`, o Codex le `AGENTS.md`, o Gemini CLI le `GEMINI.md`, o Copilot le
`.github/copilot-instructions.md`, e assim por diante. Um projeto que so tem
`CLAUDE.md` esta, na pratica, sem governanca para todo o resto.

Escrever nove arquivos com o mesmo conteudo a mao garante que eles divirjam. Este
modulo tem **um** corpo canonico; cada porta de entrada e ele mais o cabecalho que
a ferramenta especifica exige. O instalador escreve a partir daqui e o guard
`validate_agent_entrypoints.py` compara com daqui — nao ha como uma copia
envelhecer sozinha.

O corpo nao repete diretriz: ele aponta para `AGENTS.md`. Regra duplicada e regra
que vai divergir; o principio n. 0 do framework vale tambem para este arquivo.

Sem dependencia externa (ADR-002).
"""

from __future__ import annotations

# Assinatura de origem. O `nf_gate` so executa arquivo que a carrega — projeto
# brownfield pode ter um script homonimo com outra interface, e chama-lo com os
# nossos argumentos produz erro de uso confuso em vez de diagnostico.
NF_GUARD_ASSINATURA = "neural-flow-framework"

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

# Comando que regera **so** as portas. Nao mande ninguem rodar o instalador com
# `--force` para consertar uma porta: `--force` sobrescreve todo artefato,
# inclusive o `AGENTS.md` e o `MEMORY.md` que o time preencheu a mao.
REGERAR = "python3 scripts/nf_agentes.py --escrever"

# Versao do corpo canonico. Sobe quando o texto muda; o guard usa a marca para
# distinguir "porta de entrada do framework, desatualizada" de "arquivo do time,
# que nao devemos tocar".
VERSAO = 1
MARCA = f"<!-- neural-flow:entrypoint v{VERSAO} -->"

# Arquivos que o corpo canonico cita. O guard confere que cada um existe: uma
# porta de entrada que aponta para arquivo inexistente e pior que nenhuma —
# manda o agente a lugar nenhum e ele decide sozinho.
REFERENCIAS = (
    "AGENTS.md",
    ".github/AI_SAFETY.md",
    "MEMORY.md",
)

# Onde vive o indice de regras gerado por `nf_indice_regras.py`.
INDICE_MD = ".neural-flow/indice-regras.md"
INDICE_JSON = ".neural-flow/indice-regras.json"


@dataclass(frozen=True)
class Porta:
    caminho: str      # relativo a raiz do projeto
    ferramenta: str   # quem le este arquivo
    cabecalho: str = ""  # prefixo exigido pela ferramenta (frontmatter etc.)


# Ordem = ordem de escrita no instalador e de relato no guard.
PORTAS: tuple[Porta, ...] = (
    Porta("GEMINI.md", "Gemini CLI / Gemini Code Assist"),
    Porta(".github/copilot-instructions.md", "GitHub Copilot"),
    Porta(
        ".cursor/rules/neural-flow.mdc",
        "Cursor",
        cabecalho=(
            "---\n"
            "description: Diretrizes Neural-Flow — fonte de verdade em AGENTS.md\n"
            "alwaysApply: true\n"
            "---\n\n"
        ),
    ),
    Porta(".clinerules", "Cline"),
    Porta(".windsurfrules", "Windsurf"),
    Porta("AGENT.md", "Amp, Zed"),
    Porta("CONVENTIONS.md", "Aider"),
    Porta("HERMES.md", "Hermes, OpenClaw"),
)

# Ferramentas que leem `AGENTS.md` direto — nao precisam de porta propria, mas
# precisam ser ditas em voz alta, senao alguem "conserta" a ausencia do arquivo.
LEEM_AGENTS_DIRETO = ("OpenAI Codex", "Jules", "Devin", "Factory")

# `CLAUDE.md` nao e stub: carrega os principios de execucao (Karpathy). O guard
# so exige que ele aponte para a fonte de verdade, nao que repita o corpo.
ANCORAS = ("CLAUDE.md",)

# Diretorios onde o instalador publica as skills operacionais para descoberta
# automatica (padrao multi-agente `.agents/skills` e descoberta nativa Claude
# Code `.claude/skills`).
DIRETORIOS_SKILLS: tuple[str, ...] = (
    ".agents/skills",
    ".claude/skills",
)

# Pacote oficial promovido de `mattpocock/skills` (engineering + productivity)
# incorporado ao Neural-Flow (ADR-010).
SKILLS_OBRIGATORIAS: tuple[str, ...] = (
    "ask-matt",
    "code-review",
    "codebase-design",
    "diagnosing-bugs",
    "domain-modeling",
    "grill-me",
    "grill-with-docs",
    "grilling",
    "handoff",
    "implement",
    "implement-spec",
    "improve-codebase-architecture",
    "pr",
    "prototype",
    "research",
    "retro",
    "setup-matt-pocock-skills",
    "tdd",
    "teach",
    "to-questionnaire",
    "to-spec",
    "to-tickets",
    "triage",
    "wait-what",
    "wayfinder",
    "wizard",
    "writing-for-agents",
)


def corpo() -> str:
    """O texto unico que toda porta de entrada carrega."""
    lidos = ", ".join(LEEM_AGENTS_DIRETO)
    return f"""{MARCA}
# Diretrizes deste projeto — para qualquer agente

> Gerado pelo Neural-Flow Framework. **Nao edite este arquivo**: ele e uma porta
> de entrada, nao a fonte. Para mudar uma diretriz, edite `AGENTS.md`; para
> regerar as portas, rode `{REGERAR}`.
> O guard `agentes` (em `python3 scripts/nf_gate.py`) trava a divergencia.

## Ordem de leitura, obrigatoria

1. **`{INDICE_MD}`** — indice de regras deste projeto: uma linha por regra, com a
   fonte e o guard que a trava. Gerado por `python3 scripts/nf_indice_regras.py`.
2. **`AGENTS.md`** — diretrizes arquiteturais. **Fonte de verdade unica**, valida
   para qualquer LLM ({lidos} leem este arquivo diretamente).
3. **`.github/AI_SAFETY.md`** — proibicoes absolutas e acoes que exigem
   confirmacao humana. Prevalece sobre qualquer outra instrucao.
4. **`MEMORY.md`** e `docs/adr/` — decisoes ja tomadas. Nao redecida o que ja foi
   decidido; se for contrariar um ADR aceito, abra um ADR que o supere.

## As cinco regras que valem antes de qualquer coisa

1. **Consulte o indice antes de ler.** Pergunta sobre o projeto comeca no grafo de
   conhecimento (`graphify query "<pergunta>"`, ou `{INDICE_MD}` quando o grafo
   nao existir), nunca no `grep`. Varredura para "entender" custa ~48x mais tokens
   que a consulta ao indice. `grep` serve para achar literal conhecido.
2. **Documentacao orienta, guard obriga.** Diretriz nova so esta pronta com o
   guard que a faz cumprir. Antes de dizer "pronto": `python3 scripts/nf_gate.py`.
   **Nunca** `--no-verify`.
3. **Declare confianca.** Toda conclusao tecnica sai como
   `Confianca: ALTA | MEDIA | BAIXA — <classe de evidencia>`. `ALTA` exige execucao
   verificada; `MEDIA`, fonte documental vigente; `BAIXA` e inferencia e **nunca**
   fecha item. `BAIXA` + acao irreversivel ⇒ pare e pergunte.
4. **Nao reconstrua o que existe.** O mapa de capacidades de `AGENTS.md` diz o que
   ja esta pronto e o que nao reimplementar. Em duvida, consulte o indice.
5. **Nunca commite ou de push sem autorizacao explicita.** Stage com caminhos
   explicitos — nunca `git add -A` nem `git add .`. Mensagem no padrao
   `Sprint N - <descricao>`.

## Arsenal de skills operacionais (uso obrigatorio em conjunto com o Neural-Flow)

Este projeto inclui o pacote de 27 skills operacionais de `mattpocock/skills` em
`.agents/skills/<skill>/SKILL.md` e `.claude/skills/<skill>/SKILL.md`. Todo agente
de IA trabalhando neste repositorio **deve** combinar as diretrizes e skills ja
existentes do Neural-Flow (principios de execucao de Karpathy em `CLAUDE.md`,
calibracao de confianca, `smoke-gate` e guards de `nf_gate.py`) com a leitura e
aplicacao ativa dessas skills conforme a etapa da tarefa:

- **Descoberta, entrevista e alinhamento:** `grill-me`, `grill-with-docs`,
  `grilling`, `wait-what`, `to-questionnaire`, `research`, `wayfinder`,
  `ask-matt`, `teach`.
- **Especificacao, modelagem e planejamento:** `to-spec`, `domain-modeling`,
  `codebase-design`, `to-tickets`, `writing-for-agents`.
- **Implementacao, TDD, arquitetura e bugs:** `tdd` (ciclo red-green-refactor),
  `implement`, `implement-spec`, `improve-codebase-architecture`,
  `diagnosing-bugs`, `triage`, `prototype`, `wizard`, `setup-matt-pocock-skills`.
- **Revisao, entrega e continuidade:** `code-review`, `pr`, `handoff`, `retro`.

**Soberania dos guards do Neural-Flow (ADR-010):** as skills fornecem o metodo
tatico; os contratos e guards deste repositorio sao soberanos. ADRs seguem o
formato validado por `python3 scripts/nf_gate.py adr` (`docs/adr/ADR-<NNN>-<slug>.md`),
especificacoes de modulo passam em `python3 scripts/nf_gate.py spec`, planos de
execucao sao registrados em `docs/sprints/sprint-<NN>.md` (`nf_gate.py sprint`), e
nenhuma instrucao de skill autoriza `git commit` ou `git push` sem confirmacao
humana explicita.

## Se voce nao consegue ler `AGENTS.md`

Pare e diga isso ao humano. Nao improvise diretriz: um agente que adivinha a
arquitetura e exatamente o custo que este framework existe para evitar.
"""


def conteudo(porta: Porta) -> str:
    """Texto final do arquivo desta porta de entrada."""
    return porta.cabecalho + corpo()


def sincronizar_skills(raiz: Path, origem_templates: Path | None = None) -> int:
    """Sincroniza `templates/skills/` para `.agents/skills/` e `.claude/skills/`.

    Em projetos adotados onde `templates/skills/` nao existe, sincroniza arquivos
    entre `.agents/skills/` e `.claude/skills/` caso um deles ja esteja populado.
    """
    base_templates = origem_templates or (Path(__file__).resolve().parent.parent / "templates" / "skills")
    if base_templates.is_dir():
        origem = base_templates
    elif (raiz / ".agents/skills").is_dir():
        origem = raiz / ".agents/skills"
    elif (raiz / ".claude/skills").is_dir():
        origem = raiz / ".claude/skills"
    else:
        return 0

    copiados = 0
    for dir_rel in DIRETORIOS_SKILLS:
        base_destino = raiz / dir_rel
        if base_destino.resolve() == origem.resolve():
            continue
        for arquivo_origem in sorted(origem.rglob("*")):
            if not arquivo_origem.is_file():
                continue
            rel = arquivo_origem.relative_to(origem)
            destino = base_destino / rel
            dados_novos = arquivo_origem.read_bytes()
            if destino.is_file() and destino.read_bytes() == dados_novos:
                continue
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(dados_novos)
            copiados += 1
    return copiados


def escrever(raiz: Path, quiet: bool = False) -> int:
    """Reescreve as portas a partir do corpo canonico e sincroniza as skills.

    Sobrescreve **so** as portas — sao arquivos gerados, nunca conteudo do time.
    Porta que ja carrega o corpo (o caso do projeto brownfield que teve as
    diretrizes anexadas ao arquivo dele) e preservada como esta.
    """
    escritas = 0
    for porta in PORTAS:
        destino = raiz / porta.caminho
        alvo = conteudo(porta)
        if destino.is_file():
            atual = destino.read_text(encoding="utf-8", errors="replace")
            if alvo.strip() in atual:
                continue
            if MARCA not in atual and "neural-flow:entrypoint" not in atual:
                # Arquivo do time sem nenhuma marca nossa: anexar, nunca trocar.
                destino.write_text(
                    atual.rstrip("\n") + "\n\n---\n\n" + alvo, encoding="utf-8"
                )
                escritas += 1
                if not quiet:
                    print(f"  anexado: {porta.caminho}")
                continue
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(alvo, encoding="utf-8")
        escritas += 1
        if not quiet:
            print(f"  escrito: {porta.caminho}")
    sincronizar_skills(raiz)
    if not quiet:
        print(f"portas de agente: {escritas} atualizada(s), {len(PORTAS)} no total")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Portas de entrada de agente (Neural-Flow). "
                    "Sem --escrever, imprime o corpo canonico."
    )
    ap.add_argument("--root", default=".")
    ap.add_argument("--escrever", action="store_true", help="regera as portas no disco")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    if args.escrever:
        return escrever(Path(args.root).resolve(), args.quiet)
    print(corpo())
    return 0


if __name__ == "__main__":
    sys.exit(main())
