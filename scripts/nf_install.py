#!/usr/bin/env python3
"""
Neural-Flow Framework — instalador
==================================
Instala o framework num projeto, em dois modos:

  brownfield  Projeto que ja tem codigo. Instala guards, hooks, CI, AGENTS.md,
              AI_SAFETY.md, MEMORY.md e liga o smoke-gate. Nada do que ja existe
              e sobrescrito.

  greenfield  Projeto que ainda e uma ideia. Alem do acima, monta o andaime
              docs-first: padrao de especificacao, diretorio de modulos, ADRs,
              a sprint de descoberta e os quatro arquivos de estado do loop.
              O codigo so comeca depois que a spec passar no gate.

O modo e detectado sozinho; `--mode` forca.

Uso:
    python3 scripts/nf_install.py --target ../meu-projeto --name "Meu Projeto"
    python3 scripts/nf_install.py --target . --mode greenfield --dry-run

Sem dependencia externa: stdlib apenas (ver ADR-002).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

RAIZ_FW = Path(__file__).resolve().parent.parent

GUARDS = [
    "nf_gate.py", "nf_guards.py", "validate_sprint_state.py",
    "validate_token_budget.py", "validate_context_sources.py",
    "validate_adr.py", "validate_module_spec.py", "validate_calibration.py",
    "nf_dashboard.py",
]

SMOKE_GATE_REPO = "reimon/smoke-gate"
# Rede indisponivel ou API fora do ar nao pode impedir a instalacao — cai para a
# ultima versao conhecida em vez de falhar.
SMOKE_GATE_FALLBACK = "v0.5.0"


def resolver_ref_smoke_gate(ref: str | None) -> tuple[str, str | None]:
    """Descobre a versao mais recente do smoke-gate no momento da instalacao.

    Devolve (ref, aviso). `--smoke-gate-ref` sobrepoe: use `main` para acompanhar
    o branch sem pinagem, ou uma tag para congelar.

    A versao e resolvida na instalacao e gravada no projeto: cada instalacao
    nasce com a mais nova, e o projeto instalado continua reproduzivel. Gravar
    uma referencia flutuante faria o mesmo commit auditar de formas diferentes em
    dias diferentes — o oposto do que o framework pede.
    """
    if ref:
        return ref, None

    import json as _json
    import re as _re
    import urllib.error
    import urllib.request

    url = f"https://api.github.com/repos/{SMOKE_GATE_REPO}/tags?per_page=100"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "neural-flow-installer"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            tags = _json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        return SMOKE_GATE_FALLBACK, (
            f"nao consegui consultar as versoes do smoke-gate ({exc.__class__.__name__}); "
            f"usando {SMOKE_GATE_FALLBACK}. Ajuste com --smoke-gate-ref."
        )

    def chave(nome: str) -> tuple:
        m = _re.match(r"^v?(\d+)\.(\d+)\.(\d+)", nome)
        return tuple(int(g) for g in m.groups()) if m else (-1, -1, -1)

    validas = [t["name"] for t in tags if chave(t["name"]) != (-1, -1, -1)]
    if not validas:
        return SMOKE_GATE_FALLBACK, "nenhuma tag de versao encontrada; usando fallback"
    return max(validas, key=chave), None

# Sinais de que o projeto ja tem codigo.
SINAIS_CODIGO = [
    "package.json", "pyproject.toml", "setup.py", "go.mod", "Cargo.toml",
    "pom.xml", "build.gradle", "Gemfile", "composer.json", "src", "app", "lib",
]


class Instalacao:
    def __init__(self, alvo: Path, dry_run: bool, forcar: bool) -> None:
        self.alvo = alvo
        self.dry_run = dry_run
        self.forcar = forcar
        self.criados: list[str] = []
        self.mantidos: list[str] = []
        self.avisos: list[str] = []

    def rel(self, caminho: Path) -> str:
        try:
            return str(caminho.relative_to(self.alvo))
        except ValueError:
            return str(caminho)

    def escrever(self, destino: Path, conteudo: str, executavel: bool = False) -> None:
        if destino.exists() and not self.forcar:
            self.mantidos.append(self.rel(destino))
            return
        self.criados.append(self.rel(destino))
        if self.dry_run:
            return
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(conteudo, encoding="utf-8")
        if executavel:
            destino.chmod(destino.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP)

    def copiar(self, origem: Path, destino: Path, executavel: bool = False) -> None:
        self.escrever(destino, origem.read_text(encoding="utf-8"), executavel)

    def copiar_template(self, relativo: str, destino: Path) -> None:
        """Copia removendo o cabecalho '> TEMPLATE Neural-Flow ...'.

        O cabecalho existe para os guards ignorarem o template no repositorio do
        framework. Copiado tal e qual para o projeto, faria o artefato nascer
        permanentemente invisivel para o gate.
        """
        texto = (RAIZ_FW / relativo).read_text(encoding="utf-8")
        linhas, saida, pulando = texto.splitlines(), [], False
        for linha in linhas:
            if linha.startswith("> TEMPLATE Neural-Flow"):
                pulando = True
                continue
            if pulando:
                if linha.startswith(">") or not linha.strip():
                    continue
                pulando = False
            saida.append(linha)
        self.escrever(destino, "\n".join(saida).lstrip("\n") + "\n")


# ── Deteccao ───────────────────────────────────────────────────────────────────


def detectar_modo(alvo: Path) -> str:
    for sinal in SINAIS_CODIGO:
        if (alvo / sinal).exists():
            return "brownfield"
    for padrao in ("**/*.ts", "**/*.py", "**/*.go", "**/*.java", "**/*.rb"):
        for achado in alvo.glob(padrao):
            if not any(p in achado.parts for p in (".git", "node_modules", ".venv", "scripts")):
                return "brownfield"
    return "greenfield"


def eh_repo_git(alvo: Path) -> bool:
    return (alvo / ".git").exists()


# ── Blocos de instalacao ───────────────────────────────────────────────────────


def instalar_guards(inst: Instalacao) -> None:
    for nome in GUARDS:
        inst.copiar(RAIZ_FW / "scripts" / nome, inst.alvo / "scripts" / nome)
    inst.copiar(
        RAIZ_FW / "templates" / "githooks" / "pre-commit",
        inst.alvo / ".githooks" / "pre-commit",
        executavel=True,
    )
    inst.copiar(
        RAIZ_FW / ".github" / "workflows" / "neural-flow-gates.yml",
        inst.alvo / ".github" / "workflows" / "neural-flow-gates.yml",
    )


def instalar_governanca(inst: Instalacao, nome_projeto: str) -> None:
    inst.copiar_template("templates/AGENTS-template.md", inst.alvo / "AGENTS.md")
    # CLAUDE.md carrega os principios de execucao (Karpathy) e amarra cada um ao
    # protocolo que o torna verificavel. Vale nos dois modos: e a disciplina do
    # agente, independente de haver codigo ainda.
    inst.copiar_template("templates/CLAUDE-template.md", inst.alvo / "CLAUDE.md")
    inst.copiar_template(
        "templates/AI_SAFETY-template.md", inst.alvo / ".github" / "AI_SAFETY.md"
    )
    memoria = (RAIZ_FW / "templates" / "MEMORY-template.md").read_text(encoding="utf-8")
    memoria = memoria.replace("<Nome do Projeto>", nome_projeto)
    inst.escrever(inst.alvo / "MEMORY.md", memoria)


def instalar_sprint(inst: Instalacao, nome_projeto: str, modo: str) -> None:
    hoje = date.today()
    prazo = hoje + timedelta(days=14)

    if modo == "greenfield":
        titulo = "Sprint 1: Descoberta e especificacao"
        escopo = f"`{nome_projeto} — especificacao dos modulos, antes de qualquer codigo`"
        proxima = "`escrever a spec do primeiro modulo`"
        incluido = [
            "Definir o padrao obrigatorio de especificacao de modulo",
            "Especificar os modulos do MVP em `docs/modulos/`",
            "Levantar a base de dados de referencia (valores com fonte e data)",
            "Inventario de reuso: o que ja existe e cobre parte do escopo",
            "Registrar as decisoes estruturais como ADR",
        ]
        fora = [
            "Qualquer codigo de produto — o loop so comeca com a spec no gate",
            "Escolha de infraestrutura de nuvem",
            "Integracao com servico externo real",
        ]
        checklist = [
            ("1.1", "Preencher `docs/PADRAO-ESPECIFICACAO-MODULOS.md` com as secoes obrigatorias",
             "`docs/PADRAO-ESPECIFICACAO-MODULOS.md`", "`python3 scripts/nf_gate.py spec`"),
            ("1.2", "Escrever a spec do modulo 01 a partir do padrao",
             "`docs/modulos/01-*/spec.md`", "`python3 scripts/nf_gate.py spec`"),
            ("1.3", "Registrar as decisoes estruturais como ADR",
             "`docs/adr/`", "`python3 scripts/nf_gate.py adr`"),
            ("1.4", "Construir o indice de conhecimento sobre `docs/`",
             "`graphify-out/`", "consulta ao indice devolve resultado util"),
            ("1.5", "Preencher `build/PLANO.md` com itens ordenados por dependencia",
             "`build/PLANO.md`", "cada item tem criterio de aceite verificavel"),
        ]
    else:
        titulo = "Sprint 1: Adocao do Neural-Flow"
        escopo = f"`{nome_projeto} — governanca sobre o codigo existente`"
        proxima = "`mapear o que ja existe em AGENTS.md`"
        incluido = [
            "Preencher o mapa de capacidades em `AGENTS.md` (o que nao reimplementar)",
            "Preencher `.github/AI_SAFETY.md` com as proibicoes reais do projeto",
            "Consolidar decisoes ja tomadas em `MEMORY.md` e ADRs",
            "Ligar os guards no pre-commit e no CI",
        ]
        fora = [
            "Refatoracao do codigo existente",
            "Migracao de infraestrutura",
        ]
        checklist = [
            ("1.1", "Preencher o mapa de capacidades em `AGENTS.md`",
             "`AGENTS.md`", "revisao humana"),
            ("1.2", "Preencher as proibicoes absolutas em `.github/AI_SAFETY.md`",
             "`.github/AI_SAFETY.md`", "revisao humana"),
            ("1.3", "Registrar como ADR as decisoes estruturais ja vigentes",
             "`docs/adr/`", "`python3 scripts/nf_gate.py adr`"),
            ("1.4", "Rodar o primeiro audit do smoke-gate e triar os achados",
             "`audit-report.md`", "`npx smoke-gate audit --llm none`"),
            ("1.5", "Ligar os guards no CI e confirmar verde",
             "`.github/workflows/neural-flow-gates.yml`", "pipeline verde"),
        ]

    linhas = [
        f"# {titulo}", "",
        "## Snapshot Operacional", "",
        f"- App/Escopo: {escopo}",
        "- Status: `em andamento`",
        f"- Data de inicio: `{hoje.isoformat()}`",
        f"- Data planejada de conclusao: `{prazo.isoformat()}`",
        "- Data real de conclusao: `a definir`",
        f"- Ultima atualizacao: `{hoje.isoformat()}`",
        "- Nivel de autonomia: `A1`",
        "- Blocker principal: `nenhum`",
        f"- Proxima acao: {proxima}", "",
        "> Escopo que toque auth, segredo, infra, billing ou dado pessoal opera em A0/A1.",
        "> O guard S4 reprova A2/A3 nesse caso, salvo `Excecao formal` declarada como campo.",
        "", "## FinOps de Tokens", "",
        "- Token budget: `500k`",
        "- Limite de alerta: `70%`",
        "- Consumo observado: `em andamento`",
        "- Mitigacao aplicada: `nao se aplica`", "",
        "> Ajuste o budget a realidade do projeto. B4 exige registrar o consumo real",
        "> antes de marcar a sprint como `concluida` — nao preencha com valor plausivel.",
        "", "## Objetivo", "",
        f"Estabelecer a governanca Neural-Flow em {nome_projeto}.", "",
        "## Escopo incluido", "",
    ]
    linhas += [f"- {i}" for i in incluido]
    linhas += ["", "## Fora do escopo", ""]
    linhas += [f"- {i}" for i in fora]
    linhas += ["", "## Checklist de Acoes", "", "### Bloco 1: Fundacao", ""]
    for num, acao, arquivos, validacao in checklist:
        linhas += [
            f"- [ ] {num} {acao}",
            f"  - Arquivo(s): {arquivos}",
            f"  - Validacao: {validacao}",
            "  - Evidencia: a preencher",
            "",
        ]
    linhas += [
        "## Evidencias de Implementacao", "",
        "- a preencher conforme os itens forem concluidos", "",
        "## Pendencias para a Proxima Sprint", "",
        "- a preencher", "",
        "## Regras", "",
        "- Validar antes de commitar: `python3 scripts/nf_gate.py`",
        "- Item so recebe `[x]` quando a acao foi realmente executada.",
        "",
    ]
    inst.escrever(
        inst.alvo / "docs" / "sprints" / "sprint-01.md", "\n".join(linhas)
    )


def instalar_greenfield(inst: Instalacao, nome_projeto: str) -> None:
    inst.copiar_template(
        "templates/spec-modulo-template.md",
        inst.alvo / "docs" / "PADRAO-ESPECIFICACAO-MODULOS.md",
    )
    inst.escrever(
        inst.alvo / "docs" / "modulos" / "README.md",
        f"# Modulos de {nome_projeto}\n\n"
        "Um diretorio por modulo, contendo `spec.md` no padrao de\n"
        "`docs/PADRAO-ESPECIFICACAO-MODULOS.md`.\n\n"
        "O guard `spec` descobre os modulos **pelo diretorio**, nunca por lista fixa:\n"
        "modulo novo nao nasce sem gate por esquecimento de ninguem.\n\n"
        "    docs/modulos/01-<nome>/spec.md\n"
        "    docs/modulos/02-<nome>/spec.md\n\n"
        "Regra: nenhum codigo de produto antes da spec passar em\n"
        "`python3 scripts/nf_gate.py spec`.\n",
    )
    inst.escrever(
        inst.alvo / "docs" / "adr" / "README.md",
        "# Architecture Decision Records\n\n"
        "Numeracao sequencial, nunca reutilizada. ADR aceito e imutavel: mudanca de\n"
        "rumo gera novo ADR que o supera.\n\n"
        "Criar a partir de `docs/adr/_template.md`. Validar com\n"
        "`python3 scripts/nf_gate.py adr`.\n",
    )
    # O `_template.md` mantem o cabecalho TEMPLATE de proposito: e o que faz o
    # guard `adr` ignora-lo. Sem o cabecalho, o proprio modelo seria cobrado como
    # se fosse um ADR sem numero.
    inst.copiar(RAIZ_FW / "templates" / "adr-template.md", inst.alvo / "docs" / "adr" / "_template.md")

    for origem, destino in [
        ("templates/loop/PROTOCOLO-template.md", "build/PROTOCOLO.md"),
        ("templates/loop/PROMPT-LOOP-template.md", "build/PROMPT-LOOP.md"),
    ]:
        inst.copiar_template(origem, inst.alvo / destino)

    # PLANO/DIARIO/DIVERGENCIAS nascem VAZIOS e validos. Copiar os templates com
    # seus blocos de exemplo faria os placeholders (`<ID>`, `<titulo>`) serem lidos
    # como itens e divergencias reais — o projeto nasceria reprovado no gate.
    inst.escrever(
        inst.alvo / "build" / "PLANO.md",
        f"""# Plano de construcao — {nome_projeto}

Estado vivo do loop. **Este arquivo e a fonte de verdade do que ja foi feito.**
Atualize ao fim de cada iteracao, conforme `build/PROTOCOLO.md`.

Marcacao: `[ ]` a fazer - `[x]` pronto e verificado - `[BLOQUEADO: motivo]`.

## Definicao de Pronto (a meta do loop)

O loop encerra quando todos os itens estiverem `[x]` ou `[BLOQUEADO]` e isto for verdade
**numa maquina limpa**. Preencha com criterios verificaveis do seu projeto:

1. a preencher — ex: subir dependencias
2. a preencher — ex: aplicar migrations
3. a preencher — ex: health check devolve 200
4. a preencher — ex: comando de verificacao verde (formato, lint, testes)
5. Nada disso exige uma unica credencial externa

## Decisoes ja tomadas — nao reabrir

Cada decisao aponta para a spec ou ADR que a fundamenta. Reabrir decisao registrada e
desperdicio de iteracao.

- a preencher

## Fora do escopo deste loop

Liste **nominalmente**. Escopo sem fronteira explicita e escopo que o agente amplia
sozinho — sempre com boa intencao, sempre na direcao errada.

- a preencher

## Fase E — Esqueleto que roda

Itens ordenados por dependencia. Um item por iteracao. Cada item precisa de criterio de
aceite verificavel e da spec que deve seguir.

- [ ] **E1 — a preencher**
""",
    )
    inst.escrever(
        inst.alvo / "build" / "DIARIO.md",
        """# Diario do loop

Uma entrada por iteracao, escrita pelo agente. Formato de cada linha:

    <ID do item> - <o que foi feito> - <verificar: verde|vermelho> - <confianca: ALTA|MEDIA|BAIXA> - <o que a proxima precisa saber>

Regras:

- 1 a 3 linhas por iteracao. Nao e relatorio, e rastro.
- Registrar tambem iteracao que **falhou** — e como as 3 tentativas sao contadas.
- Confianca e derivada da evidencia: ALTA = execucao verificada, MEDIA = spec/ADR
  vigente, BAIXA = inferencia. Item marcado `[x]` nunca e BAIXA.
- Decisao de produto tomada pelo agente vai em `DIVERGENCIAS.md`, nao aqui.

---
""",
    )
    inst.escrever(
        inst.alvo / "build" / "DIVERGENCIAS.md",
        """# Divergencias

**Este e o arquivo mais importante para o humano revisar.** Cada entrada e uma decisao
de produto que o loop tomou sozinho porque a spec nao respondeu. O diario e cronologico;
as divergencias sao o que se le **antes de decidir**.

Regra de ouro: o agente **nao edita a spec**. Quando ela e ambigua, incompleta ou
contraditoria, registra aqui e segue com a decisao **mais conservadora**.

Antes de abrir uma divergencia, percorra a escada de verificacao: buscar fonte
documental e, se for executavel, executar. Divergencia aberta sem os dois degraus e
preguica registrada como incerteza.

Formato de cada entrada (uma secao `##` por divergencia):

```markdown
## <ID do item> — <titulo curto>

- **Data:** AAAA-MM-DD
- **Spec consultada:** <arquivo, secao>
- **Consultas ao indice tentadas:** <formulacao 1>, <formulacao 2 reformulada>
- **O que falta / o que conflita:** <descricao objetiva>
- **Confianca:** BAIXA — <por que nao subiu>
- **Decisao tomada para seguir:** <a opcao mais conservadora>
- **Reversivel?** sim | nao
- **Impacto se a decisao estiver errada:** <o que precisaria ser refeito>
- **Status:** pendente de revisao humana
```

Decisao **irreversivel** sob incerteza nao vira divergencia: vira pergunta ao humano.

---
""",
    )

    inst.escrever(
        inst.alvo / "COMECE-AQUI.md",
        f"""# {nome_projeto} — por onde comecar

Este projeto foi iniciado com o Neural-Flow: **a especificacao vem antes do codigo.**
Com geracao assistida por IA, escrever codigo e a parte barata; o caro e decidir o que
construir e impedir que o agente invente o que a spec nao disse.

## A ordem (nao inverta)

| Etapa | O que fazer | Gate |
| --- | --- | --- |
| 1. Especificar | Uma pasta por modulo em `docs/modulos/`, seguindo `docs/PADRAO-ESPECIFICACAO-MODULOS.md` | `python3 scripts/nf_gate.py spec` |
| 2. Inventariar | O que ja existe (biblioteca, kit interno, servico) que cobre parte do escopo. O inventario e como se descobre o que **falta** | decisao registrada como ADR |
| 3. Indexar | Grafo de conhecimento sobre `docs/` — consulta ao indice custa ~48x menos que reler | `graphify <caminho>` |
| 4. Planejar | `build/PLANO.md`: itens ordenados por dependencia, cada um com criterio de aceite e Definicao de Pronto | revisao humana |
| 5. Construir | Loop de uma iteracao por item, estado em disco | comando de verificacao verde |
| 6. Registrar | Diario, divergencias, memoria, indice atualizado | fim de agente arruma a casa |

Especificar antes de inventariar produz reuso ruim. Indexar antes de especificar indexa o
vazio. Construir antes de planejar produz codigo que ninguem consegue verificar.

## Agora

1. Abra `docs/sprints/sprint-01.md` — e a sprint de descoberta, ja valida no gate.
2. Preencha `docs/PADRAO-ESPECIFICACAO-MODULOS.md` com as secoes que **este** dominio exige.
3. Escreva a spec do primeiro modulo em `docs/modulos/01-<nome>/spec.md`.
4. Rode `python3 scripts/nf_gate.py` antes de cada commit (o hook ja faz isso).

## Quando as specs estiverem prontas

Preencha `build/PLANO.md` e rode o loop:

```
/loop Leia build/PROTOCOLO.md e execute UMA iteracao do protocolo, do inicio ao fim.
```

O estado vive em disco (`PLANO`, `DIARIO`, `DIVERGENCIAS`), nunca na conversa — o loop
pode ser interrompido e retomado com o mesmo prompt.

## Regras que valem desde ja

- Nenhum dado de dominio inventado: valor sem fonte **bloqueia o item**, nunca vira
  numero plausivel.
- A spec e entrada, nao saida: o agente que constroi nao edita `docs/`; divergencia vai
  para `build/DIVERGENCIAS.md`.
- Escopo sensivel (auth, segredo, infra, billing, dado pessoal) opera em A0/A1.
""",
    )


# ── smoke-gate ─────────────────────────────────────────────────────────────────


def _merge_json(inst: Instalacao, destino: Path, chave_raiz: str, servidor: dict) -> None:
    dados: dict = {}
    if destino.exists():
        try:
            dados = json.loads(destino.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            inst.avisos.append(f"{inst.rel(destino)} tem JSON invalido — nao alterado")
            return
    bloco = dados.setdefault(chave_raiz, {})
    if "smoke-gate" in bloco and not inst.forcar:
        inst.mantidos.append(f"{inst.rel(destino)} (smoke-gate ja registrado)")
        return
    bloco["smoke-gate"] = servidor
    inst.criados.append(inst.rel(destino))
    if not inst.dry_run:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(json.dumps(dados, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def instalar_smoke_gate(inst: Instalacao, ref: str) -> None:
    """Liga o smoke-gate: MCP sempre; devDependency e Action quando ha package.json.

    O MCP vale para qualquer stack — `audit_check_sql` valida SQL contra o schema
    antes do agente gerar a query. Os detectores atuais sao Node/TS + Postgres,
    entao a dependencia e a Action so entram onde fazem sentido.
    """
    pacote = f"github:{SMOKE_GATE_REPO}#{ref}"
    action = f"{SMOKE_GATE_REPO}/action@{ref}"
    servidor = {
        "type": "stdio",
        "command": "npx",
        "args": ["-y", pacote, "smoke-gate", "mcp", "serve"],
    }
    _merge_json(inst, inst.alvo / ".mcp.json", "mcpServers", servidor)
    _merge_json(inst, inst.alvo / ".vscode" / "mcp.json", "servers", servidor)

    pkg = inst.alvo / "package.json"
    if not pkg.exists():
        inst.avisos.append(
            "sem package.json: smoke-gate ligado via MCP apenas. "
            "Os detectores cobrem Node/TS + Postgres; o runtime gate entra "
            "quando o projeto tiver HTTP + banco."
        )
        return

    try:
        dados = json.loads(pkg.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        inst.avisos.append("package.json com JSON invalido — dependencia nao adicionada")
        return

    dev = dados.setdefault("devDependencies", {})
    if "@kaiketsu/smoke-gate" in dev and not inst.forcar:
        inst.mantidos.append("package.json (smoke-gate ja declarado)")
    else:
        dev["@kaiketsu/smoke-gate"] = pacote
        dados.setdefault("scripts", {}).setdefault("audit", "smoke-gate audit --llm none")
        inst.criados.append("package.json (devDependency + script audit)")
        if not inst.dry_run:
            pkg.write_text(json.dumps(dados, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        inst.avisos.append("rode `npm install` para baixar o smoke-gate")

    inst.escrever(
        inst.alvo / ".github" / "workflows" / "smoke-gate.yml",
        f"""name: smoke-gate

# Audit estatico diff-only no PR: drift entre SQL e schema, IDOR, error leak,
# race condition e endpoint sem cobertura de smoke test. Bloqueia merge em
# achado `critical`.

on:
  pull_request:
  workflow_dispatch:

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0   # necessario para o audit --since
      - uses: {action}
        with:
          fail-on: critical
          comment: summary
""",
    )


# ── git ────────────────────────────────────────────────────────────────────────


def configurar_git(inst: Instalacao, iniciar: bool) -> None:
    alvo = inst.alvo
    if not eh_repo_git(alvo):
        if not iniciar:
            inst.avisos.append("nao e repositorio git — hook nao ativado (use --git-init)")
            return
        if not inst.dry_run:
            subprocess.run(["git", "init", "-q"], cwd=alvo, check=True)
        inst.criados.append(".git/ (repositorio inicializado)")

    if inst.dry_run:
        return
    atual = subprocess.run(
        ["git", "config", "--get", "core.hooksPath"],
        cwd=alvo, capture_output=True, text=True,
    ).stdout.strip()
    if atual and atual != ".githooks":
        inst.avisos.append(
            f"core.hooksPath ja aponta para '{atual}' — nao alterado. "
            "Adicione a chamada de scripts/nf_gate.py no seu hook."
        )
        return
    subprocess.run(["git", "config", "core.hooksPath", ".githooks"], cwd=alvo, check=True)

    gitignore = alvo / ".gitignore"
    marca = "# Neural-Flow"
    conteudo = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    if marca not in conteudo and not inst.dry_run:
        gitignore.write_text(
            conteudo.rstrip("\n") + "\n\n# Neural-Flow\n__pycache__/\nscripts/__pycache__/\n"
            "audit-report.md\n.neural-flow/\n",
            encoding="utf-8",
        )


# ── CLI ────────────────────────────────────────────────────────────────────────


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Instala o Neural-Flow Framework num projeto.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("--target", default=".", help="diretorio do projeto (default: .)")
    ap.add_argument("--name", help="nome do projeto (default: nome do diretorio)")
    ap.add_argument(
        "--mode", choices=["auto", "greenfield", "brownfield"], default="auto",
        help="auto detecta pela presenca de codigo",
    )
    ap.add_argument(
        "--smoke-gate", choices=["auto", "yes", "no"], default="auto",
        help="auto = sempre MCP, e dependencia/Action quando ha package.json",
    )
    ap.add_argument(
        "--smoke-gate-ref",
        help="versao do smoke-gate (default: a mais recente publicada). "
             "Use `main` para acompanhar o branch sem pinagem.",
    )
    ap.add_argument("--git-init", action="store_true", help="inicializa repo git se nao houver")
    ap.add_argument("--force", action="store_true", help="sobrescreve arquivos existentes")
    ap.add_argument("--dry-run", action="store_true", help="mostra o que faria, sem escrever")
    args = ap.parse_args()

    alvo = Path(args.target).resolve()
    if not alvo.is_dir():
        if args.dry_run:
            print(f"erro: {alvo} nao existe", file=sys.stderr)
            return 1
        alvo.mkdir(parents=True)
    nome = args.name or alvo.name
    modo = args.mode if args.mode != "auto" else detectar_modo(alvo)

    print(f"Neural-Flow — instalando em {alvo}")
    print(f"  projeto: {nome}")
    print(f"  modo:    {modo}" + ("  (detectado)" if args.mode == "auto" else ""))
    if args.dry_run:
        print("  DRY-RUN: nada sera escrito\n")

    inst = Instalacao(alvo, args.dry_run, args.force)
    instalar_guards(inst)
    instalar_governanca(inst, nome)
    instalar_sprint(inst, nome, modo)
    if modo == "greenfield":
        instalar_greenfield(inst, nome)
    if args.smoke_gate != "no":
        ref, aviso = resolver_ref_smoke_gate(args.smoke_gate_ref)
        if aviso:
            inst.avisos.append(aviso)
        print(f"  smoke-gate: {ref}")
        instalar_smoke_gate(inst, ref)
    configurar_git(inst, args.git_init or modo == "greenfield")

    print(f"\nCriados ({len(inst.criados)}):")
    for c in inst.criados:
        print(f"  + {c}")
    if inst.mantidos:
        print(f"\nMantidos, ja existiam ({len(inst.mantidos)}):")
        for m in inst.mantidos:
            print(f"  = {m}")
    if inst.avisos:
        print("\nAvisos:")
        for a in inst.avisos:
            print(f"  ! {a}")

    if args.dry_run:
        print("\nDry-run concluido.")
        return 0

    print("\nValidando a instalacao...")
    proc = subprocess.run(
        [sys.executable, "scripts/nf_gate.py", "--quiet"],
        cwd=alvo, capture_output=True, text=True,
    )
    print(proc.stdout.strip() or proc.stderr.strip())
    if proc.returncode != 0:
        print("\nA instalacao gerou artefato que nao passa no gate — isto e um bug do")
        print("instalador, nao seu. Rode `python3 scripts/nf_gate.py` para ver os detalhes.")
        return 1

    proximos = (
        "COMECE-AQUI.md — a ordem: especificar, inventariar, indexar, planejar, construir"
        if modo == "greenfield"
        else "AGENTS.md — preencha o mapa de capacidades (o que o agente NAO deve reimplementar)"
    )
    print(f"""
Instalado. Proximos passos:

  1. {proximos}
  2. docs/sprints/sprint-01.md — sua primeira sprint, ja valida no gate
  3. python3 scripts/nf_gate.py --list        (o que cada guard trava)
  4. python3 scripts/nf_dashboard.py --open  (o estado da governanca, visual)

O hook de pre-commit ja esta ativo: o proximo commit passa pelos guards.""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
