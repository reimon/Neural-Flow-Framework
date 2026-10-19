#!/usr/bin/env python3
"""
Neural-Flow Framework — dashboard
=================================
Le os artefatos do repositorio e gera um HTML auto-contido com o estado da
governanca: sprint ativa, guards, FinOps de tokens, smoke-gate, grafo de
conhecimento, ADRs e o loop.

Nao e servidor. E um arquivo unico, sem CDN e sem JavaScript de terceiros —
coerente com o ADR-002 (stdlib pura). Abre no navegador, roda no CI, publica no
GitHub Pages.

Uso:
    python3 scripts/nf_dashboard.py                    # gera .neural-flow/dashboard.html
    python3 scripts/nf_dashboard.py --open             # gera e abre no navegador
    python3 scripts/nf_dashboard.py --out docs/x.html
    python3 scripts/nf_dashboard.py --root ../projeto

Fontes de dados (todas opcionais — o que faltar aparece como "nao configurado"):
    docs/sprints/*.md      snapshot, FinOps, checklist
    docs/adr/*.md          decisoes e status
    build/*.md             plano, diario, divergencias
    graphify-out/          grafo, comunidades, custo de tokens
    audit-report.md        ultimo audit do smoke-gate
    scripts/nf_gate.py     estado dos guards, executado na hora
"""

from __future__ import annotations

# Assinatura de origem. O `nf_gate` so executa arquivo que a carrega — projeto
# brownfield pode ter um script homonimo com outra interface, e chama-lo com os
# nossos argumentos produz erro de uso confuso em vez de diagnostico.
NF_GUARD_ASSINATURA = "neural-flow-framework"

import argparse
import base64
import html
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nf_guards import (  # noqa: E402
    arquivos, campos, chave, eh_placeholder, eh_template, ler, numero,
    secao, sem_acento,
)
from nf_product_docs import diagnostico as diagnosticar_documentos_produto  # noqa: E402
from nf_tokens import coletar_tokens  # noqa: E402

AQUI = Path(__file__).resolve().parent
ASSETS = AQUI.parent / "docs" / "img"


SEM_TEMA = False


def imagem_embutida(nome: str) -> str:
    """Retorna um JPEG como data URI para o dashboard continuar abrindo offline.

    `SEM_TEMA` desliga a incorporacao. A pagina de demonstracao versionada e
    gerada assim: os assets de tema sao opcionais e nao versionados, entao
    embuti-los faria a demo divergir entre uma maquina que os tem e o CI, que
    nao — teste que falha so na maquina do dono treina o time a ignorar o CI.
    """
    if SEM_TEMA:
        return "none"
    try:
        conteudo = (ASSETS / nome).read_bytes()
    except OSError:
        return "none"
    return "data:image/jpeg;base64," + base64.b64encode(conteudo).decode("ascii")


def diagrama_arquitetura(prefixo: str = "") -> str:
    """Incorpora o diagrama para que a pagina explicativa tambem abra offline."""
    try:
        svg = (ASSETS / "arquitetura.svg").read_text(encoding="utf-8")
        for identificador in re.findall(r'\bid="([^"]+)"', svg):
            svg = svg.replace(f'id="{identificador}"', f'id="{prefixo}{identificador}"')
            svg = svg.replace(f'url(#{identificador})', f'url(#{prefixo}{identificador})')
        return svg
    except OSError:
        return '<p class="vazio">Diagrama de arquitetura não encontrado.</p>'

GUARDS = [
    ("sprint", "State Protocol", "Sprint validada antes de executar"),
    ("budget", "Circuit Breaker", "Orcamento de tokens declarado"),
    ("context", "Vetor de Contexto", "Decisao ancorada em fonte que existe"),
    ("adr", "ADR Governance", "Decisao numerada, sem ciclo nem pendura"),
    ("spec", "Spec-First", "Spec completa antes do codigo"),
    ("calibration", "Calibracao", "Confianca declarada e derivada de evidencia"),
    ("action", "Action Gateway", "Allowlist e aprovacao antes de risco alto"),
]

PROTOCOLOS = [
    ("State Protocol", "sprint"), ("Circuit Breaker", "budget"),
    ("Vetor de Contexto", "context"), ("Evidencia Sintetica", "smoke"),
    ("Aegis", None), ("Neural-Memory", None), ("ADR Governance", "adr"),
    ("Spec-First", "spec"), ("Loop Autonomo", None), ("Calibracao", "calibration"),
    ("Action Gateway", "action"),
]

RE_ITEM = re.compile(r"^\s*[-*]\s*\[(?P<marca>[ xX])\]\s*(?:\*\*)?(?P<id>[\w.]+)")
RE_BLOQUEADO = re.compile(r"\[BLOQUEADO", re.IGNORECASE)
RE_CODIGO = re.compile(r"^\s*\[([A-Z]\d)\]\s*(.*)$", re.MULTILINE)


# ── Coleta ─────────────────────────────────────────────────────────────────────


@dataclass
class Sprint:
    arquivo: str
    numero: str
    titulo: str
    status: str
    autonomia: str
    inicio: str
    prazo: str
    budget: float | None
    consumo: float | None
    feitos: int
    total: int
    bloqueados: int
    proxima_acao: str = ""
    blocker: str = ""

    @property
    def progresso(self) -> float:
        return (self.feitos / self.total * 100) if self.total else 0.0

    @property
    def razao_budget(self) -> float | None:
        if self.budget and self.consumo is not None:
            return self.consumo / self.budget
        return None


@dataclass
class Dados:
    projeto: str
    gerado_em: str
    sprints: list[Sprint] = field(default_factory=list)
    guards: list[dict] = field(default_factory=list)
    adrs: dict = field(default_factory=dict)
    grafo: dict | None = None
    smoke: dict = field(default_factory=dict)
    loop: dict = field(default_factory=dict)
    documentos_produto: dict = field(default_factory=dict)
    tokens: object = None
    janela_dias: int = 30
    # Os guards rodam mesmo sem o framework instalado no alvo (fallback para a
    # arvore deste script). Quando isso acontece, a pagina nao pode instruir a
    # rodar `scripts/nf_gate.py` — nao existe la.
    guards_locais: bool = True
    atualizacoes: dict = field(default_factory=dict)
    skills: list[dict] = field(default_factory=list)
    info_projeto: dict = field(default_factory=dict)

    @property
    def ativa(self) -> Sprint | None:
        candidatas = [s for s in self.sprints if s.status == "em andamento"]
        return max(candidatas, key=lambda s: (s.numero.zfill(4), s.arquivo), default=None)


def coletar_sprints(raiz: Path) -> list[Sprint]:
    saida: list[Sprint] = []
    for caminho in arquivos(
        raiz, "docs/sprints/*.md", "sprints/*.md", "apps/*/sprints/*.md"
    ):
        linhas = ler(caminho)
        if linhas is None or eh_template(linhas):
            continue
        snap = campos(linhas, *(secao(linhas, "Snapshot Operacional") or (0, len(linhas))))
        fin = secao(linhas, "FinOps")
        dados_fin = campos(linhas, *fin) if fin else {}

        def limpo(k: str, d: dict | None = None) -> str:
            v = (d or snap).get(k, "")
            return v.strip().strip("`*").strip()

        itens = [m for l in linhas if (m := RE_ITEM.match(l))]
        titulo = next((l.lstrip("# ").strip() for l in linhas if l.startswith("# ")), caminho.stem)
        m_num = re.search(r"(\d+)", caminho.stem)

        saida.append(Sprint(
            arquivo=str(caminho.relative_to(raiz)),
            numero=m_num.group(1) if m_num else "?",
            titulo=titulo,
            status=chave(limpo("status")) or "sem status",
            autonomia=limpo("nivel de autonomia") or "?",
            inicio=limpo("data de inicio"),
            prazo=limpo("data planejada de conclusao"),
            budget=numero(limpo("token budget", dados_fin) or limpo("token budget")),
            consumo=numero(limpo("consumo observado", dados_fin) or limpo("consumo observado")),
            feitos=sum(1 for m in itens if m.group("marca").lower() == "x"),
            total=len(itens),
            bloqueados=sum(1 for l in linhas if RE_BLOQUEADO.search(l)),
            proxima_acao=limpo("proxima acao"),
            blocker=limpo("blocker principal"),
        ))
    saida.sort(key=lambda s: (s.numero.zfill(4), s.arquivo))
    return saida


def coletar_guards(raiz: Path) -> list[dict]:
    arquivo_de = {
        "sprint": "sprint_state", "budget": "token_budget",
        "context": "context_sources", "adr": "adr",
        "spec": "module_spec", "calibration": "calibration",
        "action": "action_policy",
    }
    resultado = []
    for nome, protocolo, o_que in GUARDS:
        # Os guards podem estar instalados no projeto ou ao lado deste script.
        # Sem esse fallback, apontar --root para outro repositorio devolveria
        # "nao instalado" para tudo, mesmo com os guards disponiveis aqui.
        alvo = f"validate_{arquivo_de[nome]}.py"
        script = raiz / "scripts" / alvo
        if not script.is_file():
            script = AQUI / alvo
        if not script.is_file():
            resultado.append({"nome": nome, "protocolo": protocolo, "o_que": o_que,
                              "estado": "ausente", "achados": []})
            continue
        proc = subprocess.run(
            [sys.executable, str(script), "--root", str(raiz), "--quiet"],
            capture_output=True, text=True,
        )
        saida = (proc.stdout + proc.stderr).replace(str(raiz) + "/", "")
        achados = [{"codigo": c, "msg": m.strip()} for c, m in RE_CODIGO.findall(saida)]
        if "nada a validar" in saida or (proc.returncode == 0 and not achados and "PASS" not in saida):
            estado = "inativo"
        else:
            estado = "pass" if proc.returncode == 0 else "fail"
        resultado.append({"nome": nome, "protocolo": protocolo, "o_que": o_que,
                          "estado": estado, "achados": achados})
    return resultado


def coletar_adrs(raiz: Path) -> dict:
    por_status: dict[str, int] = {}
    lista = []
    for caminho in arquivos(raiz, "docs/adr/*.md", "docs/adrs/*.md", "docs/decisions/*.md"):
        linhas = ler(caminho)
        if linhas is None or eh_template(linhas) or caminho.stem.lower() in {"readme", "index"}:
            continue
        faixa = secao(linhas, "Status")
        status = "sem status"
        if faixa:
            for n in range(faixa[0], faixa[1]):
                t = linhas[n].strip().lstrip("-* ").strip()
                if t and not t.startswith("#"):
                    status = sem_acento(t).lower()
                    break
        curto = next((k for k in ("aceito", "proposto", "superado", "rejeitado")
                      if status.startswith(k)), "sem status")
        por_status[curto] = por_status.get(curto, 0) + 1
        titulo = next((l.lstrip("# ").strip() for l in linhas if l.startswith("# ")), caminho.stem)
        lista.append({"titulo": titulo, "status": curto, "arquivo": caminho.name})
    lista.sort(key=lambda a: a["arquivo"])
    return {"por_status": por_status, "lista": lista, "total": len(lista)}


def coletar_grafo(raiz: Path) -> dict | None:
    base = raiz / "graphify-out"
    grafo = base / "graph.json"
    if not grafo.is_file():
        return None
    try:
        d = json.loads(grafo.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    nos = d.get("nodes", [])
    arestas = d.get("links", d.get("edges", []))
    comunidades: dict[str, int] = {}
    for no in nos:
        nome = no.get("community_name") or (
            f"comunidade {no['community']}" if no.get("community") is not None else None
        )
        if nome:
            comunidades[nome] = comunidades.get(nome, 0) + 1
    top = sorted(comunidades.items(), key=lambda kv: -kv[1])[:8]

    custo = {}
    cost_json = base / "cost.json"
    if cost_json.is_file():
        try:
            custo = json.loads(cost_json.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            custo = {}

    arquivos_indexados = 0
    manifesto = base / "manifest.json"
    if manifesto.is_file():
        try:
            arquivos_indexados = len(json.loads(manifesto.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            pass

    ambiguas = sum(1 for a in arestas if str(a.get("_origin", "")).upper() == "AMBIGUOUS")

    # Artefatos navegaveis. O dashboard LINKA em vez de embutir: `graph.html`
    # costuma passar de 2 MB, e embuti-lo em cada geracao destruiria a promessa
    # de arquivo unico e leve. O link preserva as duas coisas.
    artefatos = []
    for nome, rotulo, descricao in (
        ("graph.html", "Grafo interativo", "force-directed, filtro por comunidade"),
        ("wiki/index.md", "Wiki", "um artigo por comunidade, navegavel"),
        ("GRAPH_REPORT.md", "Relatorio", "god nodes e comunidades, em texto"),
        ("graph.svg", "SVG", "para embutir em documento"),
    ):
        caminho = base / nome
        if caminho.is_file():
            artefatos.append({
                "rotulo": rotulo, "descricao": descricao, "arquivo": nome,
                "tamanho": caminho.stat().st_size,
            })
    return {
        "artefatos": artefatos,
        "nos": len(nos), "arestas": len(arestas), "comunidades": len(comunidades),
        "top": top, "ambiguas": ambiguas, "arquivos": arquivos_indexados,
        "tokens_in": custo.get("total_input_tokens", 0),
        "tokens_out": custo.get("total_output_tokens", 0),
        "atualizado": _mtime(grafo),
    }


def coletar_smoke(raiz: Path) -> dict:
    info: dict = {"configurado": False, "rodou": False, "versao": None, "achados": {}}
    for arq, chave_raiz in ((".mcp.json", "mcpServers"), (".vscode/mcp.json", "servers")):
        caminho = raiz / arq
        if not caminho.is_file():
            continue
        try:
            d = json.loads(caminho.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        srv = d.get(chave_raiz, {}).get("smoke-gate")
        if srv:
            info["configurado"] = True
            for a in srv.get("args", []):
                if "smoke-gate#" in a:
                    info["versao"] = a.split("#", 1)[1]

    pkg = raiz / "package.json"
    if pkg.is_file():
        try:
            d = json.loads(pkg.read_text(encoding="utf-8"))
            ref = d.get("devDependencies", {}).get("@kaiketsu/smoke-gate")
            if ref:
                info["configurado"] = True
                info["versao"] = info["versao"] or ref.split("#", 1)[-1]
        except (json.JSONDecodeError, OSError):
            pass

    relatorio = raiz / "audit-report.md"
    if relatorio.is_file():
        info["rodou"] = True
        # O relatorio e a prova de que rodou; exigir tambem o registro MCP
        # esconderia os achados atras de "nao configurado".
        info["configurado"] = True
        info["quando"] = _mtime(relatorio)
        texto = relatorio.read_text(encoding="utf-8", errors="replace")
        for rotulo, padrao in (
            ("critical", r"critical"), ("warning", r"warning"), ("info", r"info")
        ):
            m = re.search(rf"(\d+)\s*{padrao}", texto, re.IGNORECASE)
            if m:
                info["achados"][rotulo] = int(m.group(1))
    return info


def coletar_loop(raiz: Path) -> dict:
    base = raiz / "build"
    info: dict = {"ativo": False}
    plano = ler(base / "PLANO.md")
    if plano is None or eh_template(plano):
        return info
    info["ativo"] = True
    itens = [m for l in plano if (m := RE_ITEM.match(l))]
    info["feitos"] = sum(1 for m in itens if m.group("marca").lower() == "x")
    info["total"] = len(itens)
    info["bloqueados"] = sum(1 for l in plano if RE_BLOQUEADO.search(l))

    diario = ler(base / "DIARIO.md") or []
    entradas = [l for l in diario if re.match(r"^\s*[-*]\s+[A-Z]+[-_]?\d", l)]
    info["iteracoes"] = len(entradas)
    conf = {"ALTA": 0, "MEDIA": 0, "BAIXA": 0}
    for l in entradas:
        m = re.search(r"confianca\s*[:=]\s*(ALTA|MEDIA|BAIXA)", sem_acento(l), re.IGNORECASE)
        conf[m.group(1).upper() if m else "BAIXA"] += 1
    info["confianca"] = conf

    div = ler(base / "DIVERGENCIAS.md") or []
    pendentes, dentro = 0, False
    for l in div:
        if l.lstrip().startswith("```"):
            dentro = not dentro
            continue
        if not dentro and l.startswith("## "):
            pendentes += 1
    info["divergencias"] = pendentes
    return info


def _mtime(caminho: Path) -> str:
    try:
        return datetime.fromtimestamp(caminho.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    except OSError:
        return "?"


def coletar_atualizacoes(raiz: Path) -> dict:
    from nf_agentes import DIRETORIOS_SKILLS, MARCA, PORTAS, SKILLS_OBRIGATORIAS, VERSAO

    tem_gate = (raiz / "scripts" / "nf_gate.py").is_file()
    tem_agents = (raiz / "AGENTS.md").is_file()
    tem_nf = (raiz / ".neural-flow").is_dir()
    tem_portas = any((raiz / p.caminho).is_file() for p in PORTAS)

    instalado = tem_gate or tem_agents or tem_nf or tem_portas
    if not instalado:
        return {
            "instalado": False,
            "status": "nao_instalado",
            "versao_framework": f"v{VERSAO}",
            "skills_total": len(SKILLS_OBRIGATORIAS),
            "skills_agents": 0,
            "skills_claude": 0,
            "skills_ok": False,
            "portas_total": len(PORTAS),
            "portas_ok": 0,
            "indice_ok": False,
            "guards_ok": False,
            "pendencias": ["Framework nao instalado neste diretorio."],
        }

    pendencias: list[str] = []

    # 1. Skills operacionais (.agents/skills e .claude/skills)
    total_skills = len(SKILLS_OBRIGATORIAS)
    base_agents = raiz / ".agents" / "skills"
    skills_agents = sum(1 for s in SKILLS_OBRIGATORIAS if (base_agents / s / "SKILL.md").is_file()) if base_agents.is_dir() else 0

    base_claude = raiz / ".claude" / "skills"
    skills_claude = sum(1 for s in SKILLS_OBRIGATORIAS if (base_claude / s / "SKILL.md").is_file()) if base_claude.is_dir() else 0

    skills_ok = (skills_agents == total_skills and skills_claude == total_skills)
    if not skills_ok:
        pendencias.append(
            f"Skills operacionais pendentes: .agents/skills ({skills_agents}/{total_skills}), "
            f".claude/skills ({skills_claude}/{total_skills})"
        )

    # 2. Portas de entrada dos agentes
    portas_total = len(PORTAS)
    portas_conformes = 0
    for p in PORTAS:
        caminho = raiz / p.caminho
        if caminho.is_file():
            try:
                texto = caminho.read_text(encoding="utf-8")
                if MARCA in texto:
                    portas_conformes += 1
            except OSError:
                pass
    portas_ok = (portas_conformes == portas_total)
    if not portas_ok:
        pendencias.append(f"Portas de entrada desatualizadas ({portas_conformes}/{portas_total} conformes)")

    # 3. Indice de regras
    indice_ok = (raiz / ".neural-flow" / "indice-regras.md").is_file()
    if not indice_ok:
        pendencias.append("Indice de regras ausente (.neural-flow/indice-regras.md)")

    # 4. Guards locais
    guards_ok = tem_gate
    if not guards_ok:
        pendencias.append("Guards locais ausentes (scripts/nf_gate.py)")

    status = "pendente" if pendencias else "atualizado"

    return {
        "instalado": True,
        "status": status,
        "versao_framework": f"v{VERSAO}",
        "skills_total": total_skills,
        "skills_agents": skills_agents,
        "skills_claude": skills_claude,
        "skills_ok": skills_ok,
        "portas_total": portas_total,
        "portas_ok": portas_conformes,
        "indice_ok": indice_ok,
        "guards_ok": guards_ok,
        "pendencias": pendencias,
    }


CATALOGO_SKILLS: list[dict] = [
    # ── 1. Descoberta e Alinhamento ──
    {
        "id": "ask-matt",
        "categoria": "Descoberta e Alinhamento",
        "fase": 1,
        "titulo": "Roteador de Skills",
        "comando": "/ask-matt",
        "papel": "Standalone",
        "fluxo_principal": False,
        "descricao": "Roteador inteligente sobre as 27 skills: analisa a situacao atual e indica qual fluxo (Main Flow, On-Ramp ou Standalone) e qual acao de fronteira de fase adotar.",
        "quando": "Quando o agente ou humano tem duvida sobre qual skill invocar ou como gerenciar a janela de contexto.",
        "entradas": "Contexto da conversa + estado atual da tarefa",
        "saidas": "Recomendacao de rota tatica + decisao de Phase Boundary",
        "conecta": ["/grill-with-docs", "/triage", "/diagnosing-bugs", "/wayfinder"],
        "guias": ["SKILL.md", "PHASE-BOUNDARIES.md"],
        "passos": [
            "Identificar se o trabalho segue o fluxo principal (Idea -> Ship) ou um On-Ramp.",
            "Consultar a arvore de decisao em PHASE-BOUNDARIES.md (Continue, /clear, /handoff, Subagent, /compact).",
            "Ler o SKILL.md da skill recomendada antes de iniciar a execucao.",
        ],
        "soberania": "Direciona para skills compativeis sem desviar das regras de AGENTS.md e do State Protocol.",
    },
    {
        "id": "grill-with-docs",
        "categoria": "Descoberta e Alinhamento",
        "fase": 1,
        "titulo": "Entrevista com Documentacao",
        "comando": "/grill-with-docs",
        "papel": "Fluxo Principal",
        "fluxo_principal": True,
        "descricao": "Porta de entrada oficial do fluxo Idea -> Ship em diretorios de codigo: conduz entrevista implacavel e deixa rastro persistente em GLOSSARY.md e ADRs.",
        "quando": "No passo 1 de qualquer feature ou arquitetura nova dentro de um repositorio.",
        "entradas": "Ideia inicial + arvore de trabalho do repositorio",
        "saidas": "GLOSSARY.md atualizado + docs/adr/ADR-NNN-*.md",
        "conecta": ["/domain-modeling", "/prototype", "/to-spec"],
        "guias": ["SKILL.md"],
        "passos": [
            "Explorar o codigo e indice existentes para descobrir fatos antes de perguntar.",
            "Conduzir rodadas de entrevista focadas em decisoes de produto e fronteiras de dominio.",
            "Consolidar termos ubiquos no glossario e decisoes dificeis de reverter em ADRs.",
        ],
        "soberania": "ADRs gerados devem seguir docs/adr/ADR-<NNN>-<slug>.md e passar em nf_gate.py adr.",
    },
    {
        "id": "grill-me",
        "categoria": "Descoberta e Alinhamento",
        "fase": 1,
        "titulo": "Entrevista Rigorosa (Stateless)",
        "comando": "/grill-me",
        "papel": "Standalone",
        "fluxo_principal": True,
        "descricao": "Entrevista profunda e implacavel para estressar premissas, lacunas e trade-offs de um plano quando nao se deseja gravar glossario local.",
        "quando": "Antes de iniciar uma sprint, validar um plano abstrato ou explorar design sem alterar docs.",
        "entradas": "Plano, proposta tecnica ou ideia bruta",
        "saidas": "Entendimento alinhado e todas as ambiguidades resolvidas",
        "conecta": ["/grilling", "/to-spec", "/to-tickets"],
        "guias": ["SKILL.md"],
        "passos": [
            "Mapear a arvore de decisoes pendentes e identificar dependencias entre escolhas.",
            "Fazer uma pergunta de alto impacto por vez, recomendando a opcao mais simples.",
            "Desafiar complexidade prematura ate que todas as premissas estejam firmes.",
        ],
        "soberania": "Conclusoes aprovadas sao registradas formalmente no snapshot de docs/sprints/.",
    },
    {
        "id": "grilling",
        "categoria": "Descoberta e Alinhamento",
        "fase": 1,
        "titulo": "Primitiva de Stress-Test",
        "comando": "/grilling",
        "papel": "Standalone",
        "fluxo_principal": False,
        "descricao": "Motor primitivo de questionamento: separa o que e fato verificavel no codigo (dever do agente) do que e decisao de negocio (dever do humano).",
        "quando": "Acionada internamente por /grill-with-docs, /triage e /wayfinder, ou diretamente para questionar hipoteses.",
        "entradas": "Hipotese, proposta de arquitetura ou requisito ambiguo",
        "saidas": "Fronteira de decisao limpa e validada",
        "conecta": ["/grill-with-docs", "/grill-me", "/wayfinder"],
        "guias": ["SKILL.md"],
        "passos": [
            "Nunca perguntar ao humano o que o proprio codigo ou spec ja responde.",
            "Avancar pela fronteira de incerteza resolvendo um ramo por rodada.",
            "Ancorar cada resposta na classe de evidencia correspondente.",
        ],
        "soberania": "Subordinado ao protocolo de Calibracao (confianca declarada e baseada em evidencia).",
    },
    {
        "id": "wait-what",
        "categoria": "Descoberta e Alinhamento",
        "fase": 1,
        "titulo": "Pausa e Reformulacao",
        "comando": "/wait-what",
        "papel": "Standalone",
        "fluxo_principal": False,
        "descricao": "Freio de emergencia comunicacional: interrompe e reexplica a ultima mensagem sem jargao, usando a linguagem ubiqua do projeto.",
        "quando": "No meio de qualquer fluxo quando uma explicacao ou proposta nao ficou clara.",
        "entradas": "Mensagem anterior que gerou duvida ou desalinhamento",
        "saidas": "Reformulacao cristalina ancorada no vocabulario do dominio",
        "conecta": ["/domain-modeling", "/grill-with-docs"],
        "guias": ["SKILL.md"],
        "passos": [
            "Identificar exatamente qual salto de contexto ou termo causou ruido.",
            "Traduzir para linguagem direta usando os conceitos de GLOSSARY.md e AGENTS.md.",
            "Confirmar alinhamento antes de retomar o fluxo tecnico.",
        ],
        "soberania": "Retoma o foco na fonte de verdade e no indice de regras (.neural-flow/indice-regras.md).",
    },
    {
        "id": "to-questionnaire",
        "categoria": "Descoberta e Alinhamento",
        "fase": 1,
        "titulo": "Gerador de Questionarios",
        "comando": "/to-questionnaire",
        "papel": "Standalone",
        "fluxo_principal": False,
        "descricao": "Inverso do /grill-me: quando a resposta esta com um stakeholder externo, entrevista voce sobre o destinatario e gera um questionario cirurgico.",
        "quando": "Quando o bloqueio depende de produto, juridico, seguranca ou outra equipe.",
        "entradas": "Lacunas de negocio + perfil do destinatario",
        "saidas": "Questionario estruturado pronto para envio",
        "conecta": ["/grill-with-docs", "/to-spec"],
        "guias": ["SKILL.md"],
        "passos": [
            "Mapear quem respondera o documento e qual contexto essa pessoa domina.",
            "Formular perguntas fechadas com opcoes claras e implicacoes de cada escolha.",
            "Alimentar as respostas recebidas de volta em /grill-with-docs ou /to-spec.",
        ],
        "soberania": "Cumpre o protocolo de Calibracao: BAIXA + acao irreversivel obriga a perguntar.",
    },
    {
        "id": "research",
        "categoria": "Descoberta e Alinhamento",
        "fase": 1,
        "titulo": "Investigacao Primaria",
        "comando": "/research",
        "papel": "Standalone",
        "fluxo_principal": False,
        "descricao": "Delega pesquisa profunda a um subagente em background contra fontes primarias (codigo, RFCs, docs oficiais) e grava relatorio citado em Markdown.",
        "quando": "Antes de integrar APIs, bibliotecas ou subsistemas complexos.",
        "entradas": "Pergunta tecnica + fontes primarias alvo",
        "saidas": "Arquivo Markdown com citacoes verificaveis no repositorio",
        "conecta": ["/grill-with-docs", "/to-spec"],
        "guias": ["SKILL.md"],
        "passos": [
            "Isolar a leitura pesada em subagente para nao poluir a Smart Zone da sessao principal.",
            "Priorizar codigo-fonte, especificacoes oficiais e testes reais sobre opinioes secundarias.",
            "Consolidar achados com links e referencias exatas de linha.",
        ],
        "soberania": "Toda fonte consultada e registrada na secao Vetor de Contexto da sprint (nf_gate.py context).",
    },
    {
        "id": "wayfinder",
        "categoria": "Descoberta e Alinhamento",
        "fase": 1,
        "titulo": "Mapeamento Estrategico",
        "comando": "/wayfinder",
        "papel": "On-Ramp",
        "fluxo_principal": False,
        "descricao": "On-Ramp para esforcos gigantescos ou nebulosos que nao cabem em uma sessao: constroi um mapa compartilhado de tickets de decisao.",
        "quando": "Em projetos greenfield amplos, migracoes arquiteturais ou epicos multi-sprint.",
        "entradas": "Objetivo macro de longo prazo com caminho ainda incerto",
        "saidas": "Grafo de tickets de decisao resolvidos -> pronto para /to-spec",
        "conecta": ["/to-spec", "/to-tickets", "/grilling"],
        "guias": ["SKILL.md"],
        "passos": [
            "Criar tickets de decisao (nao de codigo) para dissipar a nevoa arquitetural passo a passo.",
            "Resolver cada ticket de decisao por entrevista e prototipagem quando necessario.",
            "Quando o caminho estiver limpo, entregar para /to-spec colapsar em plano executavel.",
        ],
        "soberania": "O macro-mapa e fatiado em sprints sequenciais validadas em docs/sprints/.",
    },
    {
        "id": "teach",
        "categoria": "Descoberta e Alinhamento",
        "fase": 1,
        "titulo": "Transferencia de Saber",
        "comando": "/teach",
        "papel": "Standalone",
        "fluxo_principal": False,
        "descricao": "Transforma o repositorio em ambiente de aprendizado guiado em multiplas sessoes, com missoes praticas, glossario e registro de evolucao.",
        "quando": "Para onboarding de engenheiros ou dominio de um novo paradigma/arquitetura.",
        "entradas": "Topico ou modulo a dominar + nivel atual do desenvolvedor",
        "saidas": "Missoes praticas + registro de aprendizado estruturado",
        "conecta": ["/domain-modeling", "/ask-matt"],
        "guias": ["SKILL.md", "MISSION-FORMAT.md", "LEARNING-RECORD-FORMAT.md", "GLOSSARY-FORMAT.md", "RESOURCES-FORMAT.md"],
        "passos": [
            "Estruturar plano pedagogico incremental ancorado em codigo real.",
            "Propor missoes praticas verificaveis e registrar progresso entre sessoes.",
            "Consolidar conceitos no formato padrao de glossario e recursos.",
        ],
        "soberania": "Baseia a exploracao estrutural no grafo de conhecimento do Graphify (~48x menos tokens).",
    },

    # ── 2. Especificacao e Modelagem ──
    {
        "id": "to-spec",
        "categoria": "Modelagem e Especificacao",
        "fase": 2,
        "titulo": "Sintetizador de Spec",
        "comando": "/to-spec",
        "papel": "Fluxo Principal",
        "fluxo_principal": True,
        "descricao": "Passo 3 do fluxo principal: sintetiza tudo o que foi decidido na entrevista (/grill-with-docs) em uma especificacao tecnica formal, sem reabrir entrevista.",
        "quando": "Logo apos o alinhamento na mesma janela de contexto (Smart Zone) para builds multi-sessao.",
        "entradas": "Decisoes da entrevista + ADRs + glossario na janela ativa",
        "saidas": "Especificacao tecnica completa e estruturada",
        "conecta": ["/to-tickets", "/implement-spec"],
        "guias": ["SKILL.md"],
        "passos": [
            "Manter a mesma janela de contexto de /grill-with-docs para preservar todo o raciocinio.",
            "Estruturar escopo, contratos de interface, estados de erro e criterios de aceite.",
            "Encaminhar imediatamente para /to-tickets antes de limpar o contexto.",
        ],
        "soberania": "Especificacoes de modulo seguem docs/modulos/<modulo>.md e passam em nf_gate.py spec.",
    },
    {
        "id": "domain-modeling",
        "categoria": "Modelagem e Especificacao",
        "fase": 2,
        "titulo": "Modelagem de Dominio",
        "comando": "/domain-modeling",
        "papel": "Vocabulario Base",
        "fluxo_principal": False,
        "descricao": "Camada de vocabulario subjacente: desafia termos vagos ou sobrecarregados, mantem GLOSSARY.md limpo e formaliza decisoes em ADRs.",
        "quando": "Acionada continuamente por /grill-with-docs ou diretamente ao modelar regras de negocio.",
        "entradas": "Conceitos de negocio, entidades e termos em disputa",
        "saidas": "Linguagem ubiqua em GLOSSARY.md + ADRs de dominio",
        "conecta": ["/grill-with-docs", "/codebase-design", "/to-spec"],
        "guias": ["SKILL.md", "ADR-FORMAT.md", "GLOSSARY-FORMAT.md"],
        "passos": [
            "Detectar palavras sobrecarregadas (ex.: 'conta' ou 'usuario' com multiplos sentidos).",
            "Definir limites claros de agregados, invariantes e ciclo de vida das entidades.",
            "Registrar decisoes estruturais seguindo o contrato de ADR do projeto.",
        ],
        "soberania": "Soberania do formato docs/adr/ADR-<NNN>-<slug>.md validado por nf_gate.py adr.",
    },
    {
        "id": "codebase-design",
        "categoria": "Modelagem e Especificacao",
        "fase": 2,
        "titulo": "Design de Modulos Profundos",
        "comando": "/codebase-design",
        "papel": "Vocabulario Base",
        "fluxo_principal": False,
        "descricao": "Vocabulario de arquitetura de modulos profundos (Ousterhout): muita capacidade escondida atras de uma interface pequena em uma costura (seam) limpa.",
        "quando": "Ao projetar interfaces publicas, escolher onde testar ou aprofundar modulos rasos.",
        "entradas": "Candidatos a refatoracao ou desenho de novo modulo",
        "saidas": "Design comparativo (Design It Twice) com interface enxuta e testavel",
        "conecta": ["/tdd", "/improve-codebase-architecture", "/implement"],
        "guias": ["SKILL.md", "DEEPENING.md", "DESIGN-IT-TWICE.md"],
        "passos": [
            "Aplicar Design It Twice: comparar pelo menos duas interfaces radicalmente diferentes.",
            "Maximizar profundidade: esconder complexidade interna atras de poucos metodos claros.",
            "Posicionar seams limpos para permitir testes de integracao sem mocks frageis.",
        ],
        "soberania": "Respeita os boundaries de camada da Secao 2 de AGENTS.md (guard nao importa guard).",
    },
    {
        "id": "to-tickets",
        "categoria": "Modelagem e Especificacao",
        "fase": 2,
        "titulo": "Fatiador de Tracer Bullets",
        "comando": "/to-tickets",
        "papel": "Fluxo Principal",
        "fluxo_principal": True,
        "descricao": "Quebra a spec em fatias verticais ponta-a-ponta (tracer bullets), declarando explicitamente as arestas de bloqueio (blocking edges) entre tickets.",
        "quando": "Imediatamente apos /to-spec, encerrando a primeira janela de contexto antes da construcao.",
        "entradas": "Especificacao tecnica aprovada",
        "saidas": "Grafo de tickets auto-contidos com dependencias de bloqueio",
        "conecta": ["/implement", "/implement-spec"],
        "guias": ["SKILL.md"],
        "passos": [
            "Evitar fatias horizontais (so banco, depois so API); cada ticket atravessa as camadas.",
            "Declarar arestas de bloqueio para definir a fronteira de execucao paralela.",
            "Escrever cada ticket de forma auto-contida para que /implement rode com /clear entre eles.",
        ],
        "soberania": "Sincroniza os itens acionaveis no Checklist Operacional da sprint em docs/sprints/.",
    },
    {
        "id": "writing-for-agents",
        "categoria": "Modelagem e Especificacao",
        "fase": 2,
        "titulo": "Escrita para Agentes",
        "comando": "/writing-for-agents",
        "papel": "Standalone",
        "fluxo_principal": False,
        "descricao": "Referencia de engenharia de prompts e documentos consumidos por agentes: como estruturar skills, AGENTS.md, CLAUDE.md e contratos sem ambiguidade.",
        "quando": "Ao criar ou editar skills, atualizar diretrizes em AGENTS.md ou escrever protocolos.",
        "entradas": "Diretriz, regra arquitetural ou fluxo de trabalho",
        "saidas": "Documento de alta densidade e zero ambiguidade para LLMs",
        "conecta": ["/retro", "/ask-matt"],
        "guias": ["SKILL.md", "SKILL-MECHANICS.md"],
        "passos": [
            "Substituir conselhos vagos por regras verificaveis e tabelas de decisao direta.",
            "Manter concisao extrema para preservar a Smart Zone de tokens do modelo.",
            "Acoplar toda nova diretriz ao guard executavel correspondente.",
        ],
        "soberania": "Alinhado ao Principio n. 0 do Neural-Flow: documentacao orienta, guard obriga.",
    },

    # ── 3. Implementacao e TDD ──
    {
        "id": "tdd",
        "categoria": "Implementacao e TDD",
        "fase": 3,
        "titulo": "Test-Driven Development",
        "comando": "/tdd",
        "papel": "Fluxo Principal",
        "fluxo_principal": True,
        "descricao": "Motor central de construcao: ciclo estrito Red-Green-Refactor uma fatia vertical por vez, testando comportamentos na interface publica sem mocks desnecessarios.",
        "quando": "Em toda construcao de codigo, seja via /implement, /implement-spec ou diretamente.",
        "entradas": "Comportamento especificado ou criterio de aceite do ticket",
        "saidas": "Codigo testado, refatorado e com suite 100% verde",
        "conecta": ["/codebase-design", "/implement", "/code-review"],
        "guias": ["SKILL.md", "tests.md", "mocking.md"],
        "passos": [
            "RED: escrever um unico teste falhando que descreve o comportamento na costura publica.",
            "GREEN: escrever o codigo mais simples possivel para fazer o teste passar.",
            "REFACTOR: eliminar duplicacao e aprofundar modulos mantendo os testes verdes.",
        ],
        "soberania": "Garante o protocolo Evidencia Sintetica e confianca ALTA antes de fechar qualquer item.",
    },
    {
        "id": "implement",
        "categoria": "Implementacao e TDD",
        "fase": 3,
        "titulo": "Implementacao Tatica",
        "comando": "/implement",
        "papel": "Fluxo Principal",
        "fluxo_principal": True,
        "descricao": "Executa um ticket auto-contido (ou feature pequena) conduzindo /tdd fatia por fatia e encerrando com /code-review sobre o diff produzido.",
        "quando": "Para executar cada ticket gerado por /to-tickets (limpando contexto com /clear entre tickets).",
        "entradas": "Ticket auto-contido ou escopo direto de sessao unica",
        "saidas": "Mudanca cirurgica implementada, testada e revisada",
        "conecta": ["/tdd", "/code-review", "/pr"],
        "guias": ["SKILL.md"],
        "passos": [
            "Ler os criterios de aceite e fronteiras do ticket em uma janela limpa.",
            "Conduzir ciclos curtos de /tdd ate cumprir todos os requisitos do ticket.",
            "Disparar /code-review (Standards + Spec) antes de considerar o ticket concluido.",
        ],
        "soberania": "Opera dentro do nivel de autonomia (A0-A3) da sprint e valida com nf_gate.py.",
    },
    {
        "id": "implement-spec",
        "categoria": "Implementacao e TDD",
        "fase": 3,
        "titulo": "Orquestrador de Spec",
        "comando": "/implement-spec",
        "papel": "Fluxo Principal",
        "fluxo_principal": True,
        "descricao": "Orquestra a construcao completa de uma spec: le os tickets como grafo de tarefas, despacha subagentes em paralelo na fronteira pronta e integra o resultado.",
        "quando": "Quando se deseja orquestrar multiplos tickets desbloqueados em paralelo via subagentes.",
        "entradas": "Spec completa + grafo de tickets de /to-tickets",
        "saidas": "Branch de integracao com todos os tickets implementados e revisados",
        "conecta": ["/to-tickets", "/tdd", "/code-review"],
        "guias": ["SKILL.md"],
        "passos": [
            "Identificar todos os tickets na fronteira sem bloqueios pendentes.",
            "Despachar subagentes implementadores (cada um rodando /tdd no seu escopo).",
            "Executar /code-review global sobre a branch integrada ao final.",
        ],
        "soberania": "Proibido divergir da spec sem registrar em build/DIVERGENCIAS.md; sem commit automatico.",
    },
    {
        "id": "improve-codebase-architecture",
        "categoria": "Implementacao e TDD",
        "fase": 3,
        "titulo": "Auditoria de Arquitetura",
        "comando": "/improve-codebase-architecture",
        "papel": "Saude Arquitetural",
        "fluxo_principal": False,
        "descricao": "Varre o repositorio em busca de modulos rasos, acoplamento excessivo e vazamento de abstracao, apresentando um relatorio visual HTML e entrevistando sobre a melhoria.",
        "quando": "Em manutencao evolutiva para manter o codigo navegavel por humanos e agentes.",
        "entradas": "Arvore de codigo do repositorio",
        "saidas": "Relatorio HTML de oportunidades de aprofundamento + proposta de design",
        "conecta": ["/codebase-design", "/grill-with-docs", "/to-spec"],
        "guias": ["SKILL.md", "HTML-REPORT.md"],
        "passos": [
            "Mapear onde a complexidade de interface supera a complexidade de implementacao.",
            "Apresentar candidatos de aprofundamento (deepening) com impacto na testabilidade.",
            "Conduzir /grilling sobre o candidato escolhido e levar para /grill-with-docs.",
        ],
        "soberania": "Mudancas arquiteturais estruturais exigem ADR aceito (nf_gate.py adr).",
    },
    {
        "id": "diagnosing-bugs",
        "categoria": "Implementacao e TDD",
        "fase": 3,
        "titulo": "Diagnostico Cientifico de Bugs",
        "comando": "/diagnosing-bugs",
        "papel": "On-Ramp",
        "fluxo_principal": False,
        "descricao": "On-Ramp para bugs dificeis, intermitentes ou regressoes: proibe teorizar no escuro ate construir um loop de feedback curto (um comando que ja fica vermelho neste bug).",
        "quando": "Quando algo quebrou, esta lento ou falha de forma nao trivial.",
        "entradas": "Sintoma de falha, stack trace ou regressao observada",
        "saidas": "Reproducao deterministica + correcao com teste de regressao",
        "conecta": ["/tdd", "/retro", "/improve-codebase-architecture"],
        "guias": ["SKILL.md", "scripts/hitl-loop.template.sh"],
        "passos": [
            "Estabelecer comando unico de reproducao rapida que falha de forma consistente.",
            "Formular hipotese falsificavel, instrumentar e isolar a causa raiz com evidencia.",
            "Corrigir com teste de regressao e rodar /retro na mesma sessao.",
        ],
        "soberania": "Cumpre Calibracao ALTA: bug so fecha com teste de regressao reproduzivel.",
    },
    {
        "id": "triage",
        "categoria": "Implementacao e TDD",
        "fase": 3,
        "titulo": "Triagem e Briefing",
        "comando": "/triage",
        "papel": "On-Ramp",
        "fluxo_principal": False,
        "descricao": "On-Ramp para issues brutas e PRs externos: move demandas por uma maquina de estados (categorizacao, verificacao, grilling) ate produzir briefs prontos para agentes.",
        "quando": "Ao processar fila de bugs reportados ou solicitacoes externas (nao usar para tickets de /to-tickets).",
        "entradas": "Issues brutas ou PRs externos nao triados",
        "saidas": "Agent-Ready Briefs validados e prontos para /implement",
        "conecta": ["/grilling", "/implement"],
        "guias": ["SKILL.md", "AGENT-BRIEF.md", "OUT-OF-SCOPE.md"],
        "passos": [
            "Verificar se a issue pertence ao escopo do produto (OUT-OF-SCOPE.md).",
            "Reproduzir e localizar os pontos de codigo afetados.",
            "Redigir Agent-Ready Brief completo (AGENT-BRIEF.md) para execucao limpa.",
        ],
        "soberania": "Classifica o nivel de autonomia (A0-A3) antes de autorizar a execucao.",
    },
    {
        "id": "prototype",
        "categoria": "Implementacao e TDD",
        "fase": 3,
        "titulo": "Prototipagem Descartavel",
        "comando": "/prototype",
        "papel": "Fluxo Principal",
        "fluxo_principal": True,
        "descricao": "Desvio tatico no passo 2 do fluxo principal: constroi programa pequeno e descartavel para responder a uma pergunta de estado, logica ou UI que o papel nao resolve.",
        "quando": "Quando uma duvida de design exige ver o codigo ou a interface rodando.",
        "entradas": "Pergunta especifica de design (via /handoff)",
        "saidas": "Resposta pratica validada + branch prototype/<nome> como fonte primaria",
        "conecta": ["/handoff", "/grill-with-docs", "/to-spec"],
        "guias": ["SKILL.md", "LOGIC.md", "UI.md"],
        "passos": [
            "Receber o contexto via /handoff em diretorio ou branch isolada.",
            "Construir spike rapido focado exclusivamente em responder a pergunta aberta.",
            "Devolver o aprendizado via /handoff para a thread principal de /grill-with-docs.",
        ],
        "soberania": "Codigo de prototipo nunca vai para main sem ser reconstruido via /tdd e nf_gate.py.",
    },
    {
        "id": "wizard",
        "categoria": "Implementacao e TDD",
        "fase": 3,
        "titulo": "Assistente Interativo Humano",
        "comando": "/wizard",
        "papel": "Standalone",
        "fluxo_principal": False,
        "descricao": "Gera um script bash interativo passo-a-passo para tarefas que somente um humano pode realizar (provisionar credenciais, secrets de CI, paineis externos).",
        "quando": "Quando o agente encontra uma barreira de permissao, segredo ou infraestrutura externa.",
        "entradas": "Procedimento manual que exige credenciais ou acao humana",
        "saidas": "Script bash interativo baseado em template.sh",
        "conecta": ["/implement", "/setup-matt-pocock-skills"],
        "guias": ["SKILL.md", "template.sh"],
        "passos": [
            "Identificar todos os passos manuais, URLs de dashboards e variaveis necessarias.",
            "Gerar wizard interativo que guia o humano, valida entradas e grava com seguranca.",
            "Transformar procedimentos repetitivos em automacao assistida versionada.",
        ],
        "soberania": "Cumpre a politica Aegis (.github/AI_SAFETY.md): zero segredo em prompt ou commit.",
    },
    {
        "id": "setup-matt-pocock-skills",
        "categoria": "Implementacao e TDD",
        "fase": 3,
        "titulo": "Configurador de Ambiente",
        "comando": "/setup-matt-pocock-skills",
        "papel": "Setup",
        "fluxo_principal": False,
        "descricao": "Pre-condicao de configuracao: define o issue tracker (GitHub, GitLab ou arquivos locais), vocabulario de labels de triagem e layout de docs de dominio.",
        "quando": "Executado uma vez antes do primeiro fluxo de engenharia no repositorio.",
        "entradas": "Estrutura do repositorio e preferencia de issue tracker",
        "saidas": "Configuracao de tracker, labels e layout de dominio",
        "conecta": ["/grill-with-docs", "/triage", "/to-tickets"],
        "guias": ["SKILL.md", "domain.md", "triage-labels.md", "issue-tracker-local.md", "issue-tracker-github.md", "issue-tracker-gitlab.md"],
        "passos": [
            "Detectar ou configurar o rastreador de tickets (local ou remoto).",
            "Padronizar rotulos de triagem e estrutura de documentacao de dominio.",
            "Habilitar as convencoes assumidas por /to-tickets e /triage.",
        ],
        "soberania": "Opera em harmonia com nf_install.py e preserva .agents/skills e .claude/skills.",
    },

    # ── 4. Revisao, Entrega e Continuidade ──
    {
        "id": "code-review",
        "categoria": "Revisao e Entrega",
        "fase": 4,
        "titulo": "Code Review Duplo Eixo",
        "comando": "/code-review",
        "papel": "Fluxo Principal",
        "fluxo_principal": True,
        "descricao": "Revisa as mudancas desde um ponto fixo em dois eixos paralelos via subagentes: Standards (padroes documentados do repo) e Spec (aderencia ao requisito).",
        "quando": "Ao fechar cada ticket em /implement, ao finalizar /implement-spec ou antes de abrir PR.",
        "entradas": "Diff da branch/commit + padroes do repo (AGENTS.md) + spec/ticket",
        "saidas": "Relatorio lado a lado de conformidade tecnica e funcional",
        "conecta": ["/implement", "/pr", "/retro"],
        "guias": ["SKILL.md"],
        "passos": [
            "Disparar subagente 1 (Standards): auditar codigo contra AGENTS.md e CLAUDE.md.",
            "Disparar subagente 2 (Spec): auditar mudancas contra criterios da spec e sprint.",
            "Consolidar achados lado a lado e bloquear entrega ate zerar desvios criticos.",
        ],
        "soberania": "Complementado obrigatoriamente por python3 scripts/nf_gate.py e smoke-gate.",
    },
    {
        "id": "pr",
        "categoria": "Revisao e Entrega",
        "fase": 4,
        "titulo": "Autor de Pull Request",
        "comando": "/pr",
        "papel": "Fluxo Principal",
        "fluxo_principal": True,
        "descricao": "Modela o corpo do Pull Request com a menor evidencia visual que prova a mudanca, comparativo antes/depois e classificacao de decisao (one-way vs two-way door).",
        "quando": "Ao preparar a submissao de uma entrega validada para revisao do time.",
        "entradas": "Commits da branch + evidencias de teste + contexto da sprint",
        "saidas": "Descricao de PR estruturada, concisa e baseada em prova",
        "conecta": ["/code-review", "/retro"],
        "guias": ["SKILL.md", "CREDITS.md"],
        "passos": [
            "Sintetizar o problema, a solucao adotada e o impacto arquitetural.",
            "Anexar evidencia real de execucao (testes, nf_gate, antes/depois).",
            "Destacar decisoes irreversiveis (one-way doors) para atencao do revisor.",
        ],
        "soberania": "Soberania absoluta da Secao 6 de AGENTS.md: nunca commitar ou dar push sem ordem explicita.",
    },
    {
        "id": "handoff",
        "categoria": "Revisao e Entrega",
        "fase": 4,
        "titulo": "Passagem de Bastao",
        "comando": "/handoff",
        "papel": "Fluxo Principal",
        "fluxo_principal": True,
        "descricao": "Compacta a conversa atual em um documento Markdown portavel para abrir nova sessao em outro diretorio, branch de prototipo, colega ou novo agente.",
        "quando": "Ao cruzar fronteiras de fase que exigem mudar de diretorio, harness ou isolar um /prototype.",
        "entradas": "Estado cognitivo da sessao atual + objetivo da proxima etapa",
        "saidas": "Documento de handoff auto-contido e portavel",
        "conecta": ["/prototype", "/implement", "/grill-with-docs"],
        "guias": ["SKILL.md"],
        "passos": [
            "Extrair decisoes tomadas, restricoes descobertas e arquivos relevantes.",
            "Omitir ruido de tentativa-e-erro para entregar contexto limpo ao proximo agente.",
            "Explicitar a pergunta exata ou acao que a nova sessao deve resolver.",
        ],
        "soberania": "Complementa o estado persistente em disco (docs/sprints/ e build/DIARIO.md).",
    },
    {
        "id": "retro",
        "categoria": "Revisao e Entrega",
        "fase": 4,
        "titulo": "Retrospectiva Operacional",
        "comando": "/retro",
        "papel": "Fluxo Principal",
        "fluxo_principal": True,
        "descricao": "Passo 4 que fecha o loop Idea -> Ship: analisa a sessao concluida e melhora o AMBIENTE do agente (guards, ponteiros de navegacao, AGENTS.md, MEMORY.md).",
        "quando": "Ao final de cada build ou correcao de bug, antes de limpar a janela da sessao.",
        "entradas": "Historico da sessao atual (ou transcript JSONL)",
        "saidas": "Melhorias em guards, regras de AGENTS.md e registros em MEMORY.md",
        "conecta": ["/writing-for-agents", "/improve-codebase-architecture"],
        "guias": ["SKILL.md"],
        "passos": [
            "Identificar onde o agente perdeu tempo, releu arquivos em excesso ou errou.",
            "Converter erros mecanicos em checks deterministicos (guards em nf_gate.py).",
            "Converter aprendizados de julgamento em padroes consolidados em MEMORY.md.",
        ],
        "soberania": "Fecha o ciclo evolucionario do Neural-Flow: toda falha vira guard ou memoria.",
    },
]


def coletar_skills(raiz: Path) -> list[dict]:
    base_agents = raiz / ".agents" / "skills"
    base_claude = raiz / ".claude" / "skills"
    resultado = []
    for item in CATALOGO_SKILLS:
        sk_id = item["id"]
        em_agents = (base_agents / sk_id / "SKILL.md").is_file()
        em_claude = (base_claude / sk_id / "SKILL.md").is_file()
        dados = dict(item)
        dados["em_agents"] = em_agents
        dados["em_claude"] = em_claude
        dados["ativa"] = em_agents and em_claude
        resultado.append(dados)
    return resultado


def coletar_projeto(raiz: Path) -> dict:
    from nf_agentes import MARCA, PORTAS

    artefatos_def = [
        ("AGENTS.md", "Constituicao dos Agentes", "Fonte de verdade unica e mapa de capacidades"),
        ("CLAUDE.md", "Principios de Execucao", "Principios de Karpathy e comandos de verificacao"),
        (".neural-flow/indice-regras.md", "Indice de Regras", "Consulta rapida (~48x menos tokens que grep)"),
        (".github/AI_SAFETY.md", "Politica Aegis (Safety)", "Proibicoes absolutas e operacoes sensiveis"),
        ("MEMORY.md", "Memoria Consolidada", "Decisoes estaveis e padroes arquiteturais"),
        (".neural-flow/action-policy.json", "Action Gateway Policy", "Allowlist de comandos e matriz A0-A3"),
        (".githooks/pre-commit", "Pre-Commit Gate", "Bloqueio local antes do commit"),
        (".github/workflows/neural-flow-gates.yml", "Pipeline CI Gate", "Validacao autoritativa em Pull Requests"),
    ]
    artefatos = []
    for rel, nome, desc in artefatos_def:
        existe = (raiz / rel).is_file()
        artefatos.append({"caminho": rel, "nome": nome, "descricao": desc, "presente": existe})

    regras_count = 0
    idx_json = raiz / ".neural-flow" / "indice-regras.json"
    idx_md = raiz / ".neural-flow" / "indice-regras.md"
    if idx_json.is_file():
        try:
            dados_idx = json.loads(idx_json.read_text(encoding="utf-8"))
            regras_count = len(dados_idx.get("regras", [])) if isinstance(dados_idx, dict) else len(dados_idx)
        except (json.JSONDecodeError, OSError):
            pass
    if not regras_count and idx_md.is_file():
        try:
            regras_count = sum(1 for l in idx_md.read_text(encoding="utf-8").splitlines() if l.strip().startswith("- **["))
        except OSError:
            pass

    acoes_safe = 0
    acoes_confirm = 0
    acoes_lista = []
    pol_path = raiz / ".neural-flow" / "action-policy.json"
    if pol_path.is_file():
        try:
            pol = json.loads(pol_path.read_text(encoding="utf-8"))
            acoes = pol.get("actions", [])
            lista_bruta = acoes.values() if isinstance(acoes, dict) else (acoes if isinstance(acoes, list) else [])
            for cfg in lista_bruta:
                if isinstance(cfg, dict):
                    req = bool(cfg.get("requires_human_approval")) or cfg.get("risk") in ("high", "critical", "sensitive", "irreversible")
                    if req:
                        acoes_confirm += 1
                    else:
                        acoes_safe += 1
                    acoes_lista.append({
                        "id": str(cfg.get("id", "?")),
                        "descricao": str(cfg.get("description", "")),
                        "risco": str(cfg.get("risk", "safe")),
                        "aprovacao": req,
                    })
        except (json.JSONDecodeError, OSError):
            pass

    portas_lista = [
        {
            "ferramenta": "OpenAI Codex / Jules / Devin / Factory",
            "caminho": "AGENTS.md",
            "tipo": "Fonte primaria",
            "ok": (raiz / "AGENTS.md").is_file(),
        },
        {
            "ferramenta": "Claude Code",
            "caminho": "CLAUDE.md",
            "tipo": "Porta + Karpathy",
            "ok": (raiz / "CLAUDE.md").is_file(),
        },
    ]
    for p in PORTAS:
        arq = raiz / p.caminho
        ok = False
        if arq.is_file():
            try:
                ok = MARCA in arq.read_text(encoding="utf-8")
            except OSError:
                ok = False
        portas_lista.append({
            "ferramenta": p.ferramenta,
            "caminho": p.caminho,
            "tipo": "Porta sincronizada",
            "ok": ok,
        })

    scripts_count = len(list((raiz / "scripts").glob("*.py"))) if (raiz / "scripts").is_dir() else 0
    tests_count = len(list((raiz / "tests").glob("test_*.py"))) if (raiz / "tests").is_dir() else 0
    protocols_count = (
        len([p for p in (raiz / "docs" / "protocols").glob("*.md") if p.name.lower() != "readme.md"])
        if (raiz / "docs" / "protocols").is_dir() else 0
    )

    return {
        "artefatos": artefatos,
        "regras_count": regras_count,
        "acoes_safe": acoes_safe,
        "acoes_confirm": acoes_confirm,
        "acoes_lista": acoes_lista,
        "portas": portas_lista,
        "scripts_count": scripts_count,
        "tests_count": tests_count,
        "protocols_count": protocols_count,
    }


def coletar(raiz: Path, projeto: str | None, gerado_em: str | None = None,
            transcripts: Path | None = None, dias: int = 30) -> Dados:
    return Dados(
        projeto=projeto or raiz.name,
        gerado_em=gerado_em or datetime.now().strftime("%Y-%m-%d %H:%M"),
        sprints=coletar_sprints(raiz),
        guards=coletar_guards(raiz),
        adrs=coletar_adrs(raiz),
        grafo=coletar_grafo(raiz),
        smoke=coletar_smoke(raiz),
        loop=coletar_loop(raiz),
        documentos_produto=diagnosticar_documentos_produto(raiz),
        tokens=coletar_tokens(raiz, dias=dias, diretorio=transcripts),
        janela_dias=dias,
        guards_locais=(raiz / "scripts" / "nf_gate.py").is_file(),
        atualizacoes=coletar_atualizacoes(raiz),
        skills=coletar_skills(raiz),
        info_projeto=coletar_projeto(raiz),
    )




# ── Graficos em SVG, desenhados a mao ──────────────────────────────────────────
# Sem biblioteca: a pagina precisa continuar auto-contida. Cada forma segue o
# trabalho do dado — sequencial para intensidade, area para serie temporal.


def nome_ferramenta(bruto: str) -> str:
    """Encurta nome de ferramenta MCP preservando o que distingue.

    `mcp__claude-in-chrome__computer` e `mcp__claude-in-chrome__navigate` truncam
    identicos numa coluna estreita — o rotulo passa a nao informar nada.
    """
    if bruto.startswith("mcp__"):
        partes = bruto.split("__")
        if len(partes) >= 3:
            servidor = partes[1].replace("claude-in-", "").replace("-", " ")
            return f"{servidor}: {partes[-1]}"
        return bruto[5:]
    return bruto


def area_temporal(pontos: list[tuple[str, int]], cor: str, altura: int = 76) -> str:
    """Serie no tempo: linha de 2px, area suave por baixo, ultimo ponto marcado.

    O endpoint destacado responde "onde estamos agora", que e a pergunta que se
    faz a uma serie temporal — sem obrigar a contar posicoes no eixo.
    """
    if len(pontos) < 2:
        return '<p class="vazio">serie curta demais para um grafico</p>'
    larg, pad = 100.0, 6.0
    valores = [v for _, v in pontos]
    teto = max(valores) or 1
    n = len(pontos)
    xs = [pad + i * (larg - 2 * pad) / (n - 1) for i in range(n)]
    ys = [altura - pad - (v / teto) * (altura - 2 * pad) for v in valores]
    linha = " ".join(f"{'M' if i == 0 else 'L'}{x:.2f},{y:.2f}" for i, (x, y) in enumerate(zip(xs, ys)))
    area = linha + f" L{xs[-1]:.2f},{altura - pad:.2f} L{xs[0]:.2f},{altura - pad:.2f} Z"
    ident = f"g{abs(hash(tuple(valores))) % 100000}"
    return f"""<svg class="svg-area" viewBox="0 0 100 {altura}" preserveAspectRatio="none"
 role="img" aria-label="serie temporal, {n} pontos, maximo {teto}">
<defs><linearGradient id="{ident}" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="{cor}" stop-opacity=".26"/>
<stop offset="1" stop-color="{cor}" stop-opacity="0"/></linearGradient></defs>
<path d="{area}" fill="url(#{ident})"/>
<path d="{linha}" fill="none" stroke="{cor}" stroke-width="2" vector-effect="non-scaling-stroke"
 stroke-linecap="round" stroke-linejoin="round"/>
<circle cx="{xs[-1]:.2f}" cy="{ys[-1]:.2f}" r="3" fill="{cor}"
 stroke="var(--surface)" stroke-width="2" vector-effect="non-scaling-stroke"/>
</svg>"""


def mapa_ritmo(por_hora: dict, dias: list[str]) -> str:
    """Intensidade por dia x hora — trabalho de magnitude continua, entao rampa
    sequencial de UMA cor (clara = perto de zero), nunca arco-iris."""
    if not dias:
        return '<p class="vazio">sem atividade registrada</p>'
    pico = max(por_hora.values()) if por_hora else 1
    # Rampa azul 100→700 da paleta validada.
    # A rampa vive em variavel CSS: no claro vai de claro para escuro, no escuro
    # de escuro para claro. Inverter automaticamente faria o valor alto sumir no
    # fundo escuro — exatamente o oposto do que a intensidade deve comunicar.
    rampa = [f"var(--ramp-{i})" for i in range(1, 8)]
    linhas = []
    for dia in dias:
        celulas = []
        for h in range(24):
            n = por_hora.get((dia, h), 0)
            if n:
                passo = rampa[min(int((n / pico) ** 0.55 * len(rampa)), len(rampa) - 1)]
                titulo = f"{dia} {h:02d}h — {n} requisicoes"
            else:
                passo, titulo = "var(--muted-fill)", f"{dia} {h:02d}h — sem atividade"
            celulas.append(f'<i class="cel" style="background:{passo}" title="{titulo}"></i>')
        linhas.append(
            f'<div class="ritmo-l"><span class="ritmo-d">{e(dia[5:])}</span>'
            f'<div class="ritmo-c">{"".join(celulas)}</div></div>'
        )
    escala = "".join(f'<i class="cel" style="background:{c}"></i>' for c in rampa)
    return (
        f'<div class="ritmo">{"".join(linhas)}'
        f'<div class="ritmo-l"><span class="ritmo-d"></span>'
        f'<div class="ritmo-h"><span>00h</span><span>06h</span><span>12h</span>'
        f'<span>18h</span><span>23h</span></div></div></div>'
        f'<div class="escala"><span>menos</span>{escala}<span>mais</span>'
        f'<span class="escala-p">pico {pico} req/h</span></div>'
    )


def anel(fracao: float, cor: str, rotulo: str) -> str:
    """Uma unica proporcao: anel le melhor que barra porque nao compete com as
    barras de comparacao ao lado."""
    raio, circ = 26.0, 2 * 3.14159265 * 26.0
    preenchido = max(0.0, min(1.0, fracao)) * circ
    return f"""<div class="anel"><svg viewBox="0 0 64 64" role="img"
 aria-label="{e(rotulo)}: {fracao:.0%}">
<circle cx="32" cy="32" r="{raio}" fill="none" stroke="var(--muted-fill)" stroke-width="6"/>
<circle cx="32" cy="32" r="{raio}" fill="none" stroke="{cor}" stroke-width="6"
 stroke-linecap="round" stroke-dasharray="{preenchido:.2f} {circ:.2f}"
 transform="rotate(-90 32 32)"/></svg>
<div class="anel-t"><span class="anel-v">{fracao:.0%}</span>
<span class="anel-l">{e(rotulo)}</span></div></div>"""


# ── Ajuda contextual ───────────────────────────────────────────────────────────
# Cada quadro e cada protocolo carrega um botao "?" que abre uma janela nativa
# (atributo `popover`) explicando o que aquilo e, o que representa e o que fazer
# quando reprova. E HTML declarativo: nenhum JavaScript, entao a pagina continua
# auto-contida e funcionando offline.

AJUDA_QUADROS = {
    "sprint": ("Sprint ativa", """
<p><strong>O que e.</strong> A sprint em andamento e o unico lugar onde trabalho tecnico
pode acontecer. O State Protocol e categorico: nenhuma execucao comeca sem uma sprint
validada.</p>
<p><strong>O que voce ve.</strong> O percentual e a fracao do checklist ja executada — item
so recebe <code>[x]</code> quando a acao foi <em>realmente</em> feita, nunca quando esta
"quase". <strong>Autonomia</strong> diz quanta liberdade o agente tem: A0 manual assistido,
A1 supervisionado, A2 semi-autonomo, A3 autonomo controlado.</p>
<p><strong>A trava que importa.</strong> Escopo que toque autenticacao, segredo,
infraestrutura, cobranca, dado pessoal ou producao opera em <strong>A0 ou A1</strong>. Pedir
A2/A3 nesse escopo reprova no guard (codigo S4), salvo excecao formal declarada como campo
na propria sprint.</p>"""),

    "guards": ("Guards", """
<p><strong>O que e.</strong> Os guards sao os protocolos virando codigo executavel. O
principio do framework e que <em>documentacao orienta, guard obriga</em>: diretriz sem guard
depende de qual modelo leu o que, e por isso ainda nao esta pronta.</p>
<p><strong>O que voce ve.</strong> Cada guard rodou <em>agora</em>, sobre a arvore de
trabalho. <strong>PASS</strong> = conforme. <strong>FAIL</strong> = ha violacao, e o codigo
(S1, B3, V1...) diz exatamente qual. <strong>inativo</strong> = o protocolo nao se aplica
ainda porque o artefato nao existe — projeto sem ADR nao e reprovado por nao ter ADR.</p>
<p><strong>Onde eles agem.</strong> No pre-commit, validando <em>o que esta em stage</em> e
nao a arvore de trabalho, e no CI, que e autoritativo porque o hook local depende de
configuracao por clone.</p>
<p><strong>Reprovou?</strong> Rode <code>python3 scripts/nf_gate.py</code> para o detalhe.
Nunca use <code>--no-verify</code>: se o gate reclamou, ou o artefato esta errado, ou o
<code>git add</code> levou o que nao devia.</p>"""),

    "finops": ("FinOps de tokens", """
<p><strong>O que e.</strong> Token e custo variavel de engenharia, nao recurso invisivel.
Toda sprint declara um orcamento, e o consumo e comparado com ele — e o Circuit Breaker,
o disjuntor financeiro do framework.</p>
<p><strong>Como ler as cores.</strong> Azul: dentro do orcamento. <strong>Ambar</strong>:
passou de 70%, o limite de alerta. <strong>Vermelho</strong>: estourou os 100%.</p>
<p><strong>A regra.</strong> Estouro <em>sem mitigacao registrada</em> reprova (codigo B3).
Mitigar nao e apagar o numero: e declarar no campo <code>Mitigacao aplicada</code> o que foi
feito — reduzir o tier de modelo, cortar escopo, ou registrar excecao formal. Sprint
concluida sem consumo registrado tambem reprova (B4).</p>
<p><strong>Tokens do indice.</strong> A segunda parte mostra o que a construcao do grafo
custou. Esses sao medidos de verdade, vindos do <code>cost.json</code>; o consumo da sprint
e o que voce declarou.</p>"""),

    "smoke": ("smoke-gate", """
<p><strong>O que e.</strong> Um gate que bate <em>todos</em> os endpoints HTTP contra um
banco real e bloqueia o deploy se algum devolver 500, mais um scanner estatico que acha
padroes frageis antes de virarem bug.</p>
<p><strong>O que ele pega.</strong> Coluna que existe no SQL e nao no schema
(<code>sqlDrift</code>), rota com <code>:userId</code> sem checagem de dono
(<code>authGaps</code>), <code>err.message</code> vazando em resposta 5xx
(<code>errorLeak</code>), SELECT+INSERT sem transacao, e endpoint sem cobertura de smoke
test.</p>
<p><strong>Por que existe.</strong> <code>pool.query("SELECT ...")</code> e uma string opaca
para o compilador: renomear uma coluna passa pelo build, passa pelos testes que mockam o
banco, e estoura em producao.</p>
<p><strong>Para o agente.</strong> Via MCP, <code>audit_check_sql</code> valida uma query
contra o schema em menos de 50 ms — <em>antes</em> de o agente gerar a query.</p>"""),

    "grafo": ("Indice de conhecimento", """
<p><strong>O que e.</strong> Um grafo construido sobre a documentacao do projeto: cada no e
um conceito, cada aresta uma relacao, e as comunidades sao agrupamentos que o algoritmo
descobriu sozinho.</p>
<p><strong>Por que ele existe.</strong> Consultar o indice custa cerca de <strong>48x menos
tokens</strong> que reler os arquivos. Mas o ganho maior nao e economia: e
<em>encontrar o que ninguem procurou</em> — a deteccao de comunidades expoe relacao entre
modulos que nenhuma pessoa teria pensado em consultar.</p>
<p><strong>Arestas AMBIGUOUS.</strong> Sao relacoes que o extrator identificou mas nao
conseguiu fechar com certeza. Na pratica, viram a lista de pendencias mais honesta do
projeto: os pontos onde a especificacao deixou algo em aberto.</p>
<p><strong>Os botoes.</strong> Levam ao grafo interativo, a wiki (um artigo por comunidade) e
ao relatorio em texto. Sao links e nao conteudo embutido: o grafo costuma passar de 2 MB.</p>
<p><strong>A regra de uso.</strong> Pergunta sobre o projeto comeca no indice, nunca no
<code>grep</code>. Varredura localiza texto literal; ela nao constroi compreensao.</p>"""),

    "loop": ("Loop autonomo", """
<p><strong>O que e.</strong> Execucao prolongada onde <em>todo</em> o estado vive em disco,
nunca na conversa. E o que resolve o problema que derruba a maioria das tentativas de
automacao: o contexto reinicia, e se o estado morava no chat, a iteracao seguinte refaz
trabalho ou pula etapa.</p>
<p><strong>Os quatro arquivos.</strong> <code>PROTOCOLO.md</code> (as regras de uma
iteracao), <code>PLANO.md</code> (backlog e fonte de verdade do que ja foi feito),
<code>DIARIO.md</code> (rastro cronologico) e <code>DIVERGENCIAS.md</code>.</p>
<p><strong>Divergencias sao o que voce revisa.</strong> Cada uma e uma decisao de produto que
o loop tomou sozinho porque a especificacao nao respondeu. O diario e cronologico; as
divergencias sao o que se le <em>antes de decidir</em>.</p>
<p><strong>Confianca.</strong> Nao e sensacao, e derivada da evidencia: ALTA = execucao
verificada, MEDIA = spec ou ADR vigente, BAIXA = inferencia. Item marcado pronto
<strong>nunca</strong> pode ser BAIXA (codigo C2), e BAIXA somada a acao irreversivel obriga
o agente a parar e perguntar.</p>"""),

    "protocolos": ("Protocolos", """
<p><strong>O que e.</strong> Os onze protocolos do framework e o estado de cada um neste
projeto.</p>
<p><strong>Como ler.</strong> <strong>trava</strong> = ha guard executavel e ele esta
passando. <strong>reprovando</strong> = ha guard e ele achou violacao.
<strong>inativo</strong> = ha guard, mas o artefato ainda nao existe.
<strong>manual</strong> = nao ha guard; a aderencia se audita.</p>
<p><strong>Por que "manual" aparece.</strong> Porque seria desonesto esconder. Nem tudo e
automatizavel: se o agente <em>de fato</em> consultou o indice antes de decidir, se a leitura
foi minima, se o tier de modelo era o mais barato viavel — isso ainda se audita, uma vez por
mes. Guard aspiracional declarado como tal nunca e apresentado como se travasse algo.</p>
<p>Clique no <strong>?</strong> de cada protocolo para entender o que ele garante.</p>"""),

    "tokens": ("Consumo real de tokens", """
<p><strong>O que e.</strong> O consumo <em>medido</em>, lido dos transcripts locais do
Claude Code — diferente do quadro de FinOps, que mostra o que a sprint
<em>declarou</em>. Ver os dois lado a lado revela se a estimativa esta perto da
realidade.</p>
<p><strong>Privacidade.</strong> So numeros sao lidos: contagem de tokens, modelo,
carimbo de tempo e identificador de sessao. <strong>O conteudo das mensagens nunca e
lido.</strong> Tudo acontece na sua maquina; nada sai dela.</p>
<p><strong>Aproveitamento de cache.</strong> A metrica mais acionavel daqui. Contexto
relido de cache custa uma fracao do que custaria reprocessado. Numero alto significa
sessao longa e barata; numero baixo indica que o contexto esta sendo reconstruido a cada
chamada — geralmente por reinicio frequente ou releitura de arquivos que o indice
resolveria.</p>
<p><strong>Faturavel.</strong> Entrada + saida + escrita de cache. A leitura de cache fica
de fora porque custa uma fracao — soma-la inflaria o numero e confundiria volume de
contexto com custo.</p>
<p><strong>Multi-provedor.</strong> Le tambem os rollouts do Codex
(<code>~/.codex/sessions</code>), filtrando pelo diretorio do projeto — o Codex organiza
sessoes por data, nao por projeto, entao sem esse filtro o numero seria de todos os seus
projetos somados. Antigravity ficou de fora: o historico local dele nao registra tokens.</p>
<p><strong>Por que nao ha valor em dinheiro.</strong> Precos mudam e variam por plano;
exibir um custo estimado seria inventar precisao que nao temos. Tokens sao o que o
sistema mede de fato.</p>"""),

    "ritmo": ("Ritmo e ferramentas", """
<p><strong>O mapa de calor</strong> mostra quantas requisicoes aconteceram em cada hora,
por dia, em UTC. Serve para enxergar o padrao real de trabalho: blocos longos e continuos
custam menos que muitas sessoes curtas, porque o cache sobrevive dentro da sessao e morre
entre elas.</p>
<p><strong>Ferramentas</strong> conta quais o agente chamou — nunca com que argumentos.
Muito <code>Read</code> e <code>Grep</code> em relacao a <code>Edit</code> sugere que o
contexto esta sendo reconstruido por varredura, exatamente o que o indice de conhecimento
existe para evitar.</p>
<p><strong>Sessoes</strong> lista as mais caras, com duracao e numero de requisicoes. Uma
sessao curta e cara costuma indicar releitura pesada logo no inicio.</p>
<p>Tudo vem dos transcripts locais; nada sai da sua maquina.</p>"""),

    "atualizacoes": ("Atualizacoes e Versao", """
<p><strong>O que e.</strong> Diagnostico das capacidades do framework instaladas neste
projeto: portas de entrada dos agentes, catalogo de 27 skills operacionais em
<code>.agents/skills/</code> e <code>.claude/skills/</code>, indice de regras e guards.</p>
<p><strong>Atualizacao sem perda.</strong> O comando de atualizacao preserva 100% dos seus
arquivos de negocio: seu <code>AGENTS.md</code>, <code>MEMORY.md</code>, sprints e
configuracoes nao sao sobrescritos.</p>
<p><strong>Como atualizar.</strong> Execute <code>python3 scripts/nf_install.py --target .</code>
para sincronizar os templates e skills, seguido de <code>python3 scripts/nf_agentes.py --escrever</code>
e <code>python3 scripts/nf_gate.py</code> para validar a conformidade.</p>"""),

    "skills": ("Skills operacionais (mattpocock/skills)", """
<p><strong>O que e.</strong> As 27 skills operacionais promovidas de <code>mattpocock/skills</code>
e incorporadas ao Neural-Flow (ADR-010). Estao disponiveis em <code>.agents/skills/</code> e
<code>.claude/skills/</code> para qualquer agente de IA.</p>
<p><strong>Invocacao autonoma.</strong> Todas as skills possuem ativacao autonoma habilitada: o modelo
seleciona e aplica cada skill conforme a fase da tarefa (Descoberta, Modelagem, Implementacao, Revisao).</p>
<p><strong>Soberania dos guards.</strong> O metodo tatico vem das skills; o contrato, a governanca e a
seguranca sao do Neural-Flow. Nenhuma skill executa <code>git commit</code> ou <code>git push</code> sem
autorizacao humana explicita.</p>"""),

    "projeto": ("Raio-X e Governanca do Projeto", """
<p><strong>O que e.</strong> Visao consolidada da arquitetura de governanca, ferramentas de IA
autorizadas, matriz de autonomia e integridade dos artefatos deste projeto.</p>
<p><strong>Como o framework atua.</strong> O Neural-Flow opera como camada de supervisao entre o
desenvolvedor e os modelos de IA, garantindo que intencao técnica vire mudanca verificavel e
imutavel.</p>"""),

    "historico": ("Historico de sprints", """
<p><strong>O que e.</strong> Todas as sprints do projeto, com progresso, nivel de autonomia e
consumo de tokens contra o orcamento.</p>
<p><strong>Para que serve.</strong> Retomada e onboarding. A regra de escala do framework diz
para ler o snapshot da sprint ativa, depois o delta desde a ultima atualizacao, e so entao o
historico completo — releitura integral e o maior desperdicio de tokens que existe.</p>
<p><strong>O que observar.</strong> Sprint apos sprint estourando o orcamento nao e problema
de estimativa: e sinal de que o escopo esta entrando maior do que cabe, ou de que o tier de
modelo esta alto demais para a tarefa.</p>"""),
}

AJUDA_TILES = {
    "governanca": ("Governanca", """
<p>Quantos guards estao conformes agora. Enquanto houver um reprovando, o commit e
bloqueado pelo hook de pre-commit — corrija antes de tentar commitar.</p>
<p>A contagem ignora guards inativos: protocolo cujo artefato ainda nao existe nao conta
como falha nem como acerto.</p>"""),
    "sprint": ("Sprint ativa", """
<p>A sprint com status <code>em andamento</code>. Se nao houver nenhuma, o State Protocol
considera que nao ha execucao autorizada: nenhuma mudanca tecnica deveria comecar.</p>"""),
    "divergencias": ("Divergencias", """
<p>Decisoes que o loop tomou sozinho porque a especificacao nao respondeu, e que aguardam
sua revisao. <strong>E a fila de revisao humana mais importante do projeto</strong> — cada
linha ali e uma escolha de produto feita sem voce.</p>
<p>Se esse numero cresce e ninguem revisa, o sistema esta sendo construido sobre suposicoes
acumuladas.</p>"""),
    "adrs": ("ADRs", """
<p>Architecture Decision Records: decisoes arquiteturais numeradas e imutaveis. Mudanca de
rumo nao edita o ADR antigo — cria um novo que o <em>supera</em>, preservando o historico do
porque.</p>
<p>O guard verifica numeracao unica, ausencia de referencia pendurada e de ciclo de
supersecao, alem de exigir que ADR aceito aponte a sprint de origem.</p>"""),
}

AJUDA_PROTOCOLOS = {
    "State Protocol": "Nenhuma execucao tecnica comeca sem sprint validada, com snapshot completo e status sem ambiguidade. Evita que o agente opere sem contexto minimo e reduz mudanca fora de escopo.",
    "Circuit Breaker": "Toda sprint declara orcamento de tokens e politica de bloqueio. Ao estourar, exige mitigacao registrada ou excecao formal — o FinOps deixa de ser revisao semanal e vira trava ativa.",
    "Vetor de Contexto": "Toda decisao tecnica ancorada em pelo menos uma fonte verificavel — e verificavel quer dizer que a fonte existe. Tambem define qual ferramenta usar para cada classe de pergunta: indice para estrutura, RAG para historico, execucao para comportamento.",
    "Evidencia Sintetica": "Conclusao tecnica depende de prova executada, nao de declaracao textual. Verde no comando de verificacao e a unica condicao para marcar um item como pronto.",
    "Aegis": "Classificacao de dado e zero segredo em prompt, memoria ou artefato. Define as proibicoes absolutas e as acoes que exigem confirmacao humana antes de acontecer.",
    "Neural-Memory": "Recuperacao semantica no lugar de leitura linear: o agente consulta o indice em vez de carregar arquivos inteiros no prompt. Torna o historico ilimitado com custo proporcional a relevancia.",
    "ADR Governance": "Decisao arquitetural registrada, numerada e imutavel. Mudanca de rumo gera novo ADR que supera o anterior, nunca edicao do antigo — o porque de cada escolha fica preservado.",
    "Spec-First": "Especificar e passar no gate antes de codificar. Dado de dominio ausente bloqueia o item; nunca vira valor plausivel. Em dominio regulado, 'soar razoavel' e o modo de falha mais caro que existe.",
    "Loop Autonomo": "Execucao prolongada com estado em disco, um item por iteracao, commit escopado. O loop pode ser interrompido e retomado com o mesmo prompt porque nada essencial vive na conversa.",
    "Calibracao": "Toda conclusao declara o grau de certeza, derivado da classe de evidencia — nunca de introspeccao. BAIXA nunca fecha item; BAIXA somada a acao irreversivel obriga a parar e perguntar.",
}


def ajuda(chave: str, titulo: str, corpo: str, pequeno: bool = False) -> tuple[str, str]:
    """Devolve (botao, janela) para a ajuda contextual."""
    ident = f"ajuda-{chave}"
    classe = "help help-sm" if pequeno else "help"
    botao = (
        f'<button type="button" class="{classe}" popovertarget="{ident}" '
        f'aria-label="O que e {e(titulo)}?">?</button>'
    )
    janela = (
        f'<div popover id="{ident}" class="pop" role="dialog" '
        f'aria-label="{e(titulo)}">'
        f'<div class="pop-h"><h3>{e(titulo)}</h3>'
        f'<button type="button" class="pop-x" popovertarget="{ident}" '
        f'popovertargetaction="hide" aria-label="Fechar">&times;</button></div>'
        f'<div class="pop-b">{corpo}</div></div>'
    )
    return botao, janela


# O dashboard nasce em portugues para preservar a leitura atual. O mapa traduz
# a interface e as explicacoes para ingles no proprio navegador, sem CDN ou
# servico externo. Valores do projeto (nomes, caminhos, titulos de sprint) ficam
# intactos: sao dados do adotante, nao texto da interface.
TRADUCOES_UI = {
    "Ir para o painel": "Skip to dashboard",
    "Navegacao do painel": "Dashboard navigation",
    "O que precisa de atencao": "What needs attention",
    "Sinais dos artefatos para orientar a proxima revisao": "Signals from project files to guide the next review",
    "Ver pendencias": "Review pending items",
    "Pendencias": "Pending items",
    "Controles": "Controls",
    "Skills": "Skills",
    "Projeto": "Project",
    "Atualizacoes": "Updates",
    "Atualizacoes e Versao": "Updates and Version",
    "Integridade das capacidades instaladas e instrucoes de atualizacao": "Integrity of installed capabilities and update instructions",
    "Conhecimento": "Knowledge",
    "Historico": "History",
    "Documentos": "Documents",
    "Resumo": "Overview",
    "Retrato local gerado em ": "Local snapshot generated ",
    "Os dados mudam quando o painel e gerado novamente.": "Data changes when the dashboard is generated again.",
    "Verificados ao gerar este retrato, sobre a arvore de trabalho": "Verified when generating this snapshot, against the working tree",
    "Ver documentos e modelos": "View documents and templates",
    "Proxima acao registrada": "Recorded next action",
    "Nenhuma proxima acao registrada.": "No next action recorded.",
    "Nenhuma sprint encontrada em andamento.": "No sprint in progress.",
    "Confira o historico ou registre uma sprint em ": "Check the history or record a sprint in ",
    "nenhuma sprint em andamento": "no sprint in progress",
    "nenhum controle ativo": "no active controls",
    "Nenhum controle ativo para avaliar este projeto.": "No active controls to evaluate this project.",
    "Configure os artefatos e gere o painel novamente para verificar o estado.": "Configure project files and generate the dashboard again to verify its status.",
    "Sem verificacao ativa": "No active verification",
    "Os controles ativos deste retrato estao conformes.": "Active controls in this snapshot pass.",
    "Acompanhe o consumo e mantenha as evidencias atualizadas.": "Track usage and keep evidence up to date.",
    "Verificacoes conformes": "Checks pass",
    " pontos precisam de revisao.": " items need review.",
    "Comece pelos controles reprovados, bloqueios e prazos.": "Start with failed controls, blocked work, and deadlines.",
    "Revisao pendente": "Review pending",
    "Corrija os achados desta verificacao.": "Address the findings from this check.",
    " achados criticos no ultimo audit": " critical findings in the last audit",
    "Revise o relatorio e confirme a correcao.": "Review the report and verify the fix.",
    " sprints em andamento": " sprints in progress",
    "A mais recente aparece em destaque. Revise os status no historico.": "The latest one is highlighted. Review statuses in the history.",
    " com bloqueio": " blocked",
    "Revise os itens bloqueados e registre o proximo passo.": "Review blocked items and record the next step.",
    " com checklist concluido": " with a completed checklist",
    "Revise as evidencias e atualize o status da sprint.": "Review evidence and update the sprint status.",
    " itens abertos. Revise o prazo planejado.": " open items. Review the planned deadline.",
    " do budget": " of budget",
    "Revise o consumo declarado e a mitigacao registrada.": "Review declared usage and recorded mitigation.",
    "Base documental precisa de revisao": "Document baseline needs review",
    "Confira lacunas, mapeamento e aprovacoes dos documentos.": "Check gaps, mapping, and document approvals.",
    " divergencias aguardando revisao": " discrepancies awaiting review",
    "Revise as decisoes pendentes antes de continuar o loop.": "Review pending decisions before continuing the loop.",
    "Nenhuma pendencia identificada nos sinais disponiveis. Confira tambem os controles inativos e os registros ausentes.": "No pending issues identified in the available signals. Also check inactive controls and missing records.",
    "Nenhuma sprint registrada.": "No sprint recorded.",
    "vence na data deste retrato": "due on this snapshot date",
    "Documentos do projeto": "Project documents",
    "Diagnostico, lacunas e modelos de referencia para a versao do produto": "Status, gaps, and reference models for this product version",
    "PRD": "Product requirements",
    "Fluxo do App": "App flow",
    "Esquema Backend": "Backend schema",
    "Plano de implementacao": "Implementation plan",
    "Requisitos, usuarios, funcionalidades e metas do produto.": "Product requirements, users, features, and goals.",
    "Arquitetura, escolhas tecnicas, operacao e custo de manutencao.": "Architecture, technical choices, operations, and maintenance cost.",
    "Jornadas, navegacao, acesso e estados de erro.": "Journeys, navigation, access, and error states.",
    "Brief visual, componentes e especificacao das telas.": "Visual brief, components, and screen specifications.",
    "Entidades, campos, relacoes e autenticacao.": "Entities, fields, relationships, and authentication.",
    "Ordem de construcao com dependencias e aceite.": "Build order with dependencies and acceptance criteria.",
    "Aprovado": "Approved",
    "Aguardando revisao": "Awaiting review",
    "Alterado apos aprovacao": "Changed after approval",
    "Incompleto": "Incomplete",
    "Ausente": "Missing",
    "Nenhum arquivo mapeado": "No file mapped",
    "Ver exemplo": "View example",
    "Exemplo do Neural-Flow. Adapte ao seu projeto.": "Neural-Flow example. Adapt it to your project.",
    "Fechar exemplo": "Close example",
    "Exemplo indisponivel nesta instalacao. Reinstale o Neural-Flow para restaurar os modelos oficiais.": "Example unavailable in this installation. Reinstall Neural-Flow to restore the official models.",
    "O diagnostico esta disponivel. O gate de sprints sera ativado quando o projeto adotar a base documental.": "Diagnostics are available. The sprint gate will activate when the project adopts the document baseline.",
    "A base aprovada esta vigente.": "The approved baseline is current.",
    "Solicite a revisao da IA e registre a aprovacao do usuario.": "Request an AI review and record user approval.",
    "Abra o arquivo e complete as lacunas listadas.": "Open the file and fill in the listed gaps.",
    "Mapeie um documento existente em .neural-flow.json ou crie-o usando o exemplo.": "Map an existing document in .neural-flow.json or create one from the example.",
    "A justificativa de nao aplicabilidade foi aprovada.": "The not-applicable rationale was approved.",
    "Proxima acao: revisao da IA e aprovacao do usuario.": "Next: AI review and user approval.",
    "Arquivo": "File",
    "nao se aplica: ": "not applicable: ",
    "Custo de manutencao": "Maintenance cost",
    "Visão de execução, risco e governança do projeto": "Execution, risk and governance view",
    "Seção do dashboard": "Dashboard section",
    "Painel": "Dashboard",
    "O Neural-Flow": "About Neural-Flow",
    "Escolha a paleta do dashboard": "Choose the dashboard palette",
    "Atualizado em ": "Updated ",
    "Resumo executivo": "Executive summary",
    "Execução em andamento, com ": "Work in progress, with ",
    " controle que exige ação antes do próximo commit.": " control requiring action before the next commit.",
    " controles que exigem ação antes do próximo commit.": " controls requiring action before the next commit.",
    "Prioridade: regularize os guards reprovados e registre a evidência pendente.": "Priority: fix failing guards and record the pending evidence.",
    "Atenção necessária": "Attention needed",
    "Controles conformes": "Controls compliant",
    "Ver controles": "View controls",
    "Governanca": "Governance",
    "guards conforme": "guards compliant",
    " reprovando — corrija antes do commit": " failing — fix before committing",
    "Sprint ativa": "Active sprint",
    "nenhuma sprint encontrada": "no sprint found",
    "Divergencias": "Divergences",
    "decisoes aguardando revisao humana": "decisions awaiting human review",
    "loop nao iniciado": "loop not started",
    "nenhum registrado": "none recorded",
    "aceito": "accepted",
    "superado": "superseded",
    "proposto": "proposed",
    "concluida": "completed",
    "em andamento": "in progress",
    "planejada": "planned",
    "bloqueada": "blocked",
    "cancelada": "cancelled",
    " dias restantes": " days remaining",
    " dias em atraso": " days overdue",
    "prazo nao definido": "deadline undefined",
    "Status": "Status",
    "Autonomia": "Autonomy",
    "Inicio": "Start",
    "Prazo": "Deadline",
    "Bloqueados": "Blocked",
    "Arquivo": "File",
    "Guards": "Guards",
    "Executados agora, sobre a arvore de trabalho": "Run now against the working tree",
    "Sprint validada antes de executar": "Sprint validated before execution",
    "Orcamento de tokens declarado": "Token budget declared",
    "Decisao ancorada em fonte que existe": "Decision anchored in an existing source",
    "Decisao numerada, sem ciclo nem pendura": "Numbered decision, without cycles or dangling references",
    "Spec completa antes do codigo": "Complete spec before coding",
    "Confianca declarada e derivada de evidencia": "Confidence declared and derived from evidence",
    "FinOps de tokens": "Token FinOps",
    "Orcamento declarado x consumo observado": "Declared budget vs observed consumption",
    "Limite de alerta em 70%. Consumo ≥ 100% do budget sem mitigacao registrada reprova no guard": "Alert threshold is 70%. Consumption ≥ 100% of the budget without recorded mitigation fails the guard",
    "Declarado x medido — sprint ativa": "Declared vs measured — active sprint",
    "Declarado": "Declared",
    "Medido": "Measured",
    "O medido vem dos transcripts locais e cobre 30 dias do projeto inteiro, nao so desta sprint — use como ordem de grandeza para calibrar o proximo budget, nao como substituto do registro.": "Measured usage comes from local transcripts and covers the whole project over 30 days, not only this sprint — use it as an estimate for the next budget, not as a replacement for the record.",
    "Tokens gastos na construcao do indice": "Tokens spent building the index",
    "Entrada": "Input",
    "Saida": "Output",
    "Gate de evidencia sobre codigo e schema": "Evidence gate for code and schema",
    "Versao": "Version",
    "Ultimo audit": "Last audit",
    "nunca": "never",
    "Rode": "Run",
    "no PR. O relatorio": "in the PR. The report",
    "e a evidencia do gate.": "is the gate evidence.",
    "Indice de conhecimento": "Knowledge index",
    "Grafo construido sobre a documentacao": "Graph built from project documentation",
    "nos": "nodes",
    "arestas": "edges",
    "comunidades": "communities",
    "arquivos": "files",
    "Grafo interativo": "Interactive graph",
    "Wiki": "Wiki",
    "Relatorio": "Report",
    "Maiores comunidades, por numero de nos": "Largest communities by node count",
    "Atualizado em ": "Updated ",
    "arestas AMBIGUOUS": "AMBIGUOUS edges",
    "— sao os pontos onde a especificacao deixou uma relacao sem fechar. Consulte o indice antes de ler arquivo: custa ~48x menos tokens.": "— these are the points where the specification left a relationship unresolved. Consult the index before reading files: it costs about 48x fewer tokens.",
    "Loop autonomo": "Autonomous loop",
    "Estado em disco, nao na conversa": "State on disk, not in the conversation",
    "Iteracoes": "Iterations",
    "Confianca declarada por iteracao": "Confidence declared per iteration",
    "Alta": "High",
    "Media": "Medium",
    "Baixa": "Low",
    "Item marcado pronto nunca pode ser": "An item marked ready can never be",
    "reprova (C2).": "fails (C2).",
    "Consumo real de tokens": "Actual token usage",
    "Medido nos transcripts locais, nao declarado": "Measured in local transcripts, not declared",
    "tokens faturaveis": "billable tokens",
    "de cache": "cached",
    "Cache escrito": "Cache written",
    "Cache lido": "Cache read",
    "Requisicoes": "Requests",
    "Sessoes": "Sessions",
    "Consumo por dia, tokens faturaveis": "Daily usage, billable tokens",
    "Por modelo, em tokens faturaveis": "By model, billable tokens",
    "Todo o periodo registrado. So numeros sao lidos — o conteudo das mensagens nunca e acessado.": "Entire recorded period. Only numbers are read — message content is never accessed.",
    "Ritmo e ferramentas": "Work rhythm and tools",
    "Como o trabalho se distribuiu": "How the work was distributed",
    "Requisicoes por hora, ": "Requests per hour, ",
    "ultimos ": "last ",
    " dias (UTC)": " days (UTC)",
    "no dia registrado": "on the recorded day",
    "Ferramentas mais usadas": "Most used tools",
    "Sessoes por consumo": "Sessions by usage",
    "menos": "less",
    "mais": "more",
    "pico ": "peak ",
    "Protocolos": "Protocols",
    "O que trava e o que se audita": "What blocks and what is audited",
    "trava": "blocking",
    "reprovando": "failing",
    "manual": "manual",
    "inativo": "inactive",
    "nao instalado": "not installed",
    "Historico de sprints": "Sprint history",
    "Titulo": "Title",
    "Aut.": "Aut.",
    "Itens": "Items",
    "Tokens": "Tokens",
    "Fechar": "Close",
    "Como uma mudança vira commit": "How a change becomes a commit",
    "O que é.": "What it is.",
    "O que e.": "What it is.",
    "O que você vê.": "What you see.",
    "O que voce ve.": "What you see.",
    "Como ler as cores.": "How to read the colors.",
    "A regra.": "The rule.",
    "Por que existe.": "Why it exists.",
    "Por que ele existe.": "Why it exists.",
    "Os botões.": "The links.",
    "Os botoes.": "The links.",
    "A regra de uso.": "Usage rule.",
    "Os quatro arquivos.": "The four files.",
    "Divergências são o que você revisa.": "Divergences are what you review.",
    "Divergencias sao o que voce revisa.": "Divergences are what you review.",
    "Confianca.": "Confidence.",
    "O que observar.": "What to watch.",
    "Para que serve.": "What it is for.",
    "Arquitetura do fluxo": "Flow architecture",
    "Nenhuma sprint encontrada": "No sprint found",
    "Nenhum sprint encontrado": "No sprint found",
    "Loop nao iniciado": "Loop not started",
    "Nenhum registrado": "None recorded",
    "Sobre o Neural-Flow Framework": "About the Neural-Flow Framework",
    "Método de engenharia assistida por IA": "AI-assisted engineering method",
    "Transformar intenção em mudança verificável.": "Turn intent into a verifiable change.",
    "Neural-Flow é um framework de governança para trabalho técnico executado por pessoas e agentes. Ele organiza a execução em artefatos legíveis, regras verificáveis e evidências reproduzíveis, para que velocidade não dependa de confiança cega.": "Neural-Flow is a governance framework for technical work carried out by people and agents. It organizes execution into readable artifacts, verifiable rules, and reproducible evidence, so speed does not depend on blind trust.",
    "O objetivo é simples: cada mudança deve ter escopo, contexto, decisão e prova. Assim, o projeto permanece compreensível quando a conversa acaba, o agente muda ou a equipe cresce.": "The goal is simple: every change needs scope, context, a decision, and proof. This keeps the project understandable when the conversation ends, the agent changes, or the team grows.",
    "Clique para ampliar": "Click to enlarge",
    "Arquitetura do fluxo: os artefatos registram a intenção, os guards bloqueiam desvios e o CI confirma a autoridade do processo.": "Flow architecture: artifacts record intent, guards block deviations, and CI confirms the process authority.",
    "O que o framework resolve": "What the framework solves",
    "Projetos guiados por IA frequentemente perdem contexto, misturam hipótese com fato e deixam decisões importantes só no chat. Neural-Flow torna o estado do trabalho explícito em disco, reduzindo retrabalho e tornando a retomada confiável.": "AI-guided projects often lose context, mix hypotheses with facts, and leave important decisions only in chat. Neural-Flow makes work state explicit on disk, reducing rework and making resumption reliable.",
    "Estado persistente": "Persistent state",
    "Plano, diário, divergências e sprint registram o que foi feito e o que falta.": "The plan, journal, divergences, and sprint record what is done and what remains.",
    "Decisão rastreável": "Traceable decisions",
    "ADRs preservam o porquê de mudanças arquiteturais sem reescrever o histórico.": "ADRs preserve why architectural changes happened without rewriting history.",
    "Como ele preserva autonomia": "How it preserves autonomy",
    "Autonomia não significa ausência de limites. O framework define até onde um agente pode avançar e quais decisões exigem revisão humana, especialmente em escopos sensíveis ou irreversíveis.": "Autonomy does not mean an absence of limits. The framework defines how far an agent may go and which decisions require human review, especially for sensitive or irreversible scopes.",
    "Guards executáveis": "Executable guards",
    "Regras críticas deixam de ser recomendação e passam a bloquear o commit quando violadas.": "Critical rules stop being recommendations and block the commit when violated.",
    "Evidência antes de conclusão": "Evidence before completion",
    "Um item só está pronto quando a verificação foi executada e registrada.": "An item is ready only after verification has been run and recorded.",
    "O ciclo operacional": "The operating cycle",
    "Defina a sprint, o escopo, a autonomia e o orçamento.": "Define the sprint, scope, autonomy, and budget.",
    "Consulte o índice e registre fontes que sustentam a decisão.": "Consult the index and record the sources supporting the decision.",
    "Implemente uma mudança pequena e deixe o estado no plano.": "Implement a small change and leave the state in the plan.",
    "Execute os guards; se reprovar, corrija o artefato ou a mudança.": "Run the guards; if one fails, fix the artifact or the change.",
    "Registre evidência, faça o commit e deixe o CI validar novamente.": "Record evidence, commit, and let CI validate again.",
    "Ampliar diagrama de arquitetura": "Enlarge architecture diagram",
    "Diagrama de arquitetura ampliado": "Enlarged architecture diagram",
    "Neural-Flow Framework — gerado por ": "Neural-Flow Framework — generated by ",
}


def controle_idioma() -> str:
    return (
        '<fieldset class="language-picker">'
        '<legend>Idioma / Language</legend>'
        '<input type="radio" name="language" id="lang-pt" value="pt" checked>'
        '<label class="view-tab" for="lang-pt">PT</label>'
        '<input type="radio" name="language" id="lang-en" value="en">'
        '<label class="view-tab" for="lang-en">EN</label>'
        '</fieldset>'
    )


def script_idioma() -> str:
    import json

    dados = json.dumps(TRADUCOES_UI, ensure_ascii=False, separators=(",", ":"))
    dados = dados.replace("<", "\\u003c")
    return f"""<script id="nf-dashboard-i18n">
(() => {{
  const translations = {dados};
  const pairs = Object.entries(translations).sort((a, b) => b[0].length - a[0].length);
  const originals = new WeakMap();
  const attrs = ["aria-label", "title"];
  const skip = "code,pre,script,style";
  const translate = (value, lang) => {{
    if (lang !== "en") return value;
    return pairs.reduce((text, [source, target]) => text.split(source).join(target), value);
  }};
  const apply = (lang) => {{
    document.documentElement.lang = lang === "en" ? "en" : "pt-BR";
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let node;
    while ((node = walker.nextNode())) {{
      if (node.parentElement && node.parentElement.closest(skip)) continue;
      if (!originals.has(node)) originals.set(node, node.nodeValue);
      node.nodeValue = translate(originals.get(node), lang);
    }}
    document.querySelectorAll("[aria-label],[title]").forEach((element) => {{
      attrs.forEach((attr) => {{
        if (!element.hasAttribute(attr)) return;
        const key = "data-nf-" + attr + "-original";
        if (!element.hasAttribute(key)) element.setAttribute(key, element.getAttribute(attr));
        element.setAttribute(attr, translate(element.getAttribute(key), lang));
      }});
    }});
    document.querySelectorAll("[name=language]").forEach((input) => {{ input.checked = input.value === lang; }});
    try {{ localStorage.setItem("nf-dashboard-language", lang); }} catch (_) {{}}
  }};
  document.querySelectorAll("[name=language]").forEach((input) => input.addEventListener("change", () => apply(input.value)));
  let initial = "pt";
  try {{ initial = localStorage.getItem("nf-dashboard-language") || "pt"; }} catch (_) {{}}
  apply(initial === "en" ? "en" : "pt");
}})();
</script>"""


def script_interface() -> str:
    return """<script id="nf-dashboard-navigation">
(() => {
  const links = [...document.querySelectorAll('.section-nav a')];
  const select = () => {
    const target = location.hash || '#resumo';
    links.forEach(link => {
      if (link.getAttribute('href') === target) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    });
  };
  window.addEventListener('hashchange', select);
  select();
  document.querySelector('.skip-link').addEventListener('click', () => {
    document.getElementById('view-dashboard').checked = true;
  });
  const themes = [...document.querySelectorAll('[name=theme]')];
  try {
    const saved = localStorage.getItem('nf-dashboard-theme');
    const input = themes.find(theme => theme.id === saved);
    if (input) input.checked = true;
  } catch (_) {}
  themes.forEach(theme => theme.addEventListener('change', () => {
    try { localStorage.setItem('nf-dashboard-theme', theme.id); } catch (_) {}
  }));
})();
</script>"""


# ── Render ─────────────────────────────────────────────────────────────────────


def e(t) -> str:
    return html.escape(str(t), quote=True)


def fmt(n: float | int | None) -> str:
    if n is None:
        return "—"
    n = float(n)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M".replace(".0M", "M")
    if n >= 10_000:
        return f"{n / 1_000:.0f}k"
    if n >= 1_000:
        # 1310 nao pode virar "1k": abaixo de 10k a casa decimal muda a leitura
        return f"{n / 1_000:.1f}k".replace(".0k", "k")
    return f"{n:.0f}"


def barra(pct: float, cor: str, altura: int = 8) -> str:
    """Barra fina com extremidade arredondada de 4px, ancorada na base."""
    pct = max(0.0, min(100.0, pct))
    return (
        f'<div class="track" style="height:{altura}px">'
        f'<div class="fill" style="width:{pct:.1f}%;background:{cor}"></div></div>'
    )


def pill(estado: str) -> str:
    mapa = {
        "pass": ("ok", "&#10003;", "PASS"),
        "fail": ("bad", "&#10007;", "FAIL"),
        "inativo": ("idle", "&#9679;", "inativo"),
        "ausente": ("idle", "&#9679;", "nao instalado"),
    }
    cls, icone, rotulo = mapa.get(estado, ("idle", "&#9679;", estado))
    return f'<span class="pill {cls}"><span aria-hidden="true">{icone}</span>{rotulo}</span>'


def barras_horizontais(itens: list[tuple[str, int]], cor: str,
                      compacto: bool = False) -> str:
    """Magnitude por categoria — uma serie, sem legenda (o titulo ja a nomeia).

    `compacto` abrevia o valor (4.3M em vez de 4325344): numero cru de milhoes
    e ilegivel de relance, que e justamente o uso de um grafico de barras.
    """
    if not itens:
        return '<p class="vazio">sem dados</p>'
    maior = max(v for _, v in itens) or 1
    linhas = []
    for rotulo, valor in itens:
        pct = valor / maior * 100
        texto = fmt(valor) if compacto else str(valor)
        linhas.append(
            f'<div class="hbar"><span class="hbar-label" title="{e(rotulo)}">{e(rotulo)}</span>'
            f'<div class="hbar-track"><div class="hbar-fill" style="width:{pct:.1f}%;'
            f'background:{cor}"></div></div>'
            f'<span class="hbar-val">{e(texto)}</span></div>'
        )
    return "".join(linhas)


def botoes_grafo(artefatos: list[dict], prefixo: str) -> str:
    """Acesso direto aos artefatos do graphify, relativo ao arquivo gerado."""
    if not artefatos:
        return ('<p class="nota">Nenhum artefato navegavel em <code>graphify-out/</code>. '
                'Gere com <code>graphify &lt;caminho&gt;</code>.</p>')
    itens = []
    for a in artefatos:
        b = a["tamanho"]
        if b >= 1_048_576:
            peso = f"{b / 1_048_576:.1f} MB"
        elif b >= 1024:
            peso = f"{b / 1024:.0f} KB"
        else:
            peso = f"{b} B"   # "0 KB" parece defeito, nao arquivo pequeno
        itens.append(
            f'<a class="btn" href="{e(prefixo)}{e(a["arquivo"])}" '
            f'target="_blank" rel="noopener noreferrer">'
            f'<span class="btn-t">{e(a["rotulo"])}</span>'
            f'<span class="btn-d">{e(a["descricao"])} · {e(peso)}</span></a>'
        )
    return f'<div class="btns">{"".join(itens)}</div>'


def card(titulo: str, corpo: str, sub: str = "", extra: str = "") -> str:
    s = f'<p class="sub">{sub}</p>' if sub else ""
    return (
        f'<section class="card {extra}"><h2>{e(titulo)}</h2>{s}{corpo}</section>'
    )


def data_snapshot(d: Dados) -> date | None:
    """Usa o carimbo do retrato, sem fazer a demo variar com o relogio."""
    try:
        return date.fromisoformat(d.gerado_em.split()[0])
    except (ValueError, IndexError):
        return None


def prioridades(d: Dados) -> list[tuple[str, str, str]]:
    """Sinais para revisao, sem inferir aprovacao ou alterar artefatos."""
    itens = []
    for g in d.guards:
        if g["estado"] == "fail":
            itens.append((g["protocolo"], "Corrija os achados desta verificacao.", "guards"))
    criticos = d.smoke.get("achados", {}).get("critical", 0)
    if criticos:
        itens.append((f"{criticos} achados criticos no ultimo audit",
                      "Revise o relatorio e confirme a correcao.", "smoke"))
    ativas = [s for s in d.sprints if s.status == "em andamento"]
    if len(ativas) > 1:
        itens.append((f"{len(ativas)} sprints em andamento",
                      "A mais recente aparece em destaque. Revise os status no historico.", "historico"))
    referencia = data_snapshot(d)
    for s in d.sprints:
        if s.status not in {"em andamento", "bloqueada"}:
            continue
        tem_blocker = (s.blocker and not eh_placeholder(s.blocker)
                       and chave(s.blocker) not in {"nenhum", "nenhuma", "nao se aplica", "n/a", "-"})
        if s.status == "bloqueada" or s.bloqueados or tem_blocker:
            detalhe = s.blocker if tem_blocker else "Revise os itens bloqueados e registre o proximo passo."
            itens.append((f"Sprint {s.numero} com bloqueio", detalhe, "historico"))
        if s.total and s.feitos == s.total and s.status == "em andamento":
            itens.append((f"Sprint {s.numero} com checklist concluido",
                          "Revise as evidencias e atualize o status da sprint.", "historico"))
        elif referencia and s.total > s.feitos:
            try:
                atraso = (referencia - date.fromisoformat(s.prazo)).days
            except (ValueError, TypeError):
                atraso = 0
            if atraso > 0:
                itens.append((f"Sprint {s.numero}: {atraso} dias em atraso",
                              f"{s.total - s.feitos} itens abertos. Revise o prazo planejado.", "historico"))
        if s.razao_budget is not None and s.razao_budget >= .7:
            itens.append((f"Sprint {s.numero}: {s.razao_budget:.0%} do budget",
                          "Revise o consumo declarado e a mitigacao registrada.", "finops"))
    docs = d.documentos_produto
    if docs.get("configuration_error") or docs.get("enabled") and not docs.get("ready"):
        itens.append(("Base documental precisa de revisao",
                      "Confira lacunas, mapeamento e aprovacoes dos documentos.", "documentos-produto"))
    divergencias = d.loop.get("divergencias", 0) if d.loop.get("ativo") else 0
    if divergencias:
        itens.append((f"{divergencias} divergencias aguardando revisao",
                      "Revise as decisoes pendentes antes de continuar o loop.", "loop"))
    if d.atualizacoes.get("status") == "pendente":
        n_pend = len(d.atualizacoes.get("pendencias", []))
        itens.append((
            f"{n_pend} atualizacoes do framework disponiveis" if n_pend > 1 else "Atualizacao do framework disponivel",
            "Sincronize skills operacionais e portas de entrada. Veja instrucoes na secao Atualizacoes.",
            "atualizacoes",
        ))
    return itens


def render(d: Dados, rel_grafo: str = "graphify-out/") -> str:
    ativa = d.ativa
    tel = d.tokens          # usado tanto no FinOps quanto no quadro de consumo
    guards_pass = sum(1 for g in d.guards if g["estado"] == "pass")
    guards_fail = sum(1 for g in d.guards if g["estado"] == "fail")
    guards_ativos = sum(1 for g in d.guards if g["estado"] in ("pass", "fail"))

    # ── Tiles de topo ──
    saude = "bad" if guards_fail else "ok" if guards_ativos else "idle"
    saude_txt = (f"{guards_fail} reprovando; revise os achados" if guards_fail else
                 "guards conforme" if guards_ativos else "nenhum controle ativo")
    tiles = [
        ("Governanca", f"{guards_pass}/{guards_ativos}" if guards_ativos else "—", saude_txt, saude),
        ("Sprint ativa",
         f"#{ativa.numero}" if ativa else "—",
         (ativa.titulo if ativa else "nenhuma sprint em andamento"),
         "ok" if ativa and ativa.status == "em andamento" else "idle"),
        ("Divergencias",
         str(d.loop.get("divergencias", 0)) if d.loop.get("ativo") else "—",
         "decisoes aguardando revisao humana" if d.loop.get("ativo") else "loop nao iniciado",
         "warn" if d.loop.get("divergencias") else "idle"),
        ("ADRs", str(d.adrs["total"]) if d.adrs["total"] else "—",
         " · ".join(f"{v} {k}" for k, v in sorted(d.adrs["por_status"].items())) or "nenhum registrado",
         "ok" if d.adrs["total"] else "idle"),
    ]
    chaves_tile = ["governanca", "sprint", "divergencias", "adrs"]
    partes_tile, janelas = [], []
    for (k, v, s, cls), ck in zip(tiles, chaves_tile):
        titulo, corpo = AJUDA_TILES[ck]
        botao, janela = ajuda(f"tile-{ck}", titulo, corpo, pequeno=True)
        janelas.append(janela)
        partes_tile.append(
            f'<div class="tile {cls}"><span class="tile-k">{e(k)}{botao}</span>'
            f'<span class="tile-v">{e(v)}</span><span class="tile-s">{e(s)}</span></div>'
        )
    html_tiles = "".join(partes_tile)

    # ── Sprint ativa ──
    if ativa:
        restante = ""
        try:
            # Conta a partir da data de GERACAO, nao de hoje. A pagina afirma
            # "gerado em X"; um contador relativo a hoje contradiria o proprio
            # carimbo — e faria a demo versionada mudar sozinha a cada dia.
            referencia = data_snapshot(d)
            if referencia is None:
                raise ValueError("carimbo sem data valida")
            faltam = (date.fromisoformat(ativa.prazo) - referencia).days
            restante = (f"{faltam} dias restantes" if faltam > 0 else
                        "vence na data deste retrato" if faltam == 0 else f"{-faltam} dias em atraso")
        except (ValueError, TypeError):
            restante = "prazo nao definido"
        aut_alerta = ativa.autonomia.upper() in ("A2", "A3")
        corpo_sprint = f"""
        <p class="sprint-title">{e(ativa.titulo)}</p>
        <div class="row">
          <div class="hero"><span class="hero-n">{ativa.progresso:.0f}<span class="hero-u">%</span></span>
            <span class="hero-l">{ativa.feitos} de {ativa.total} itens</span></div>
          <div class="grow">
            {barra(ativa.progresso, "var(--series-1)", 10)}
            <dl class="kv">
              <div><dt>Status</dt><dd>{e(ativa.status)}</dd></div>
              <div><dt>Autonomia</dt><dd class="{'warn-t' if aut_alerta else ''}">{e(ativa.autonomia)}</dd></div>
              <div><dt>Inicio</dt><dd>{e(ativa.inicio or '—')}</dd></div>
              <div><dt>Prazo</dt><dd>{e(ativa.prazo or '—')}<br><span class="muted small">{e(restante)}</span></dd></div>
              <div><dt>Bloqueados</dt><dd>{ativa.bloqueados}</dd></div>
              <div class="span"><dt>Arquivo</dt><dd class="mono">{e(ativa.arquivo)}</dd></div>
            </dl>
          </div>
        </div>
        <div class="next-step"><span>Proxima acao registrada</span><p>{e(ativa.proxima_acao or 'Nenhuma proxima acao registrada.')}</p></div>"""
    else:
        corpo_sprint = ('<p class="vazio">Nenhuma sprint encontrada em andamento. '
                        'Confira o historico ou registre uma sprint em <code>docs/sprints/</code>.</p>')

    # ── Guards ──
    linhas_g = []
    for g in d.guards:
        det = ""
        if g["achados"]:
            itens = "".join(
                f'<li><code>{e(a["codigo"])}</code> {e(a["msg"][:150])}</li>'
                for a in g["achados"][:5]
            )
            resto = (f'<li class="muted">+ {len(g["achados"]) - 5} outros</li>'
                     if len(g["achados"]) > 5 else "")
            det = f'<ul class="achados">{itens}{resto}</ul>'
        linhas_g.append(
            f'<div class="guard {g["estado"]}"><div class="guard-h">'
            f'<span class="guard-n">{e(g["protocolo"])}</span>{pill(g["estado"])}</div>'
            f'<span class="guard-d">{e(g["o_que"])}</span>'
            f'<code class="guard-c">nf_gate.py {e(g["nome"])}</code>{det}</div>'
        )
    corpo_guards = f'<div class="guards">{"".join(linhas_g)}</div>'
    if not d.guards_locais:
        corpo_guards += (
            '<p class="nota"><strong class="warn-t">Framework nao instalado neste '
            'projeto.</strong> Os guards acima rodaram a partir da arvore do '
            'Neural-Flow, sobre este repositorio — o resultado vale, mas '
            '<code>scripts/nf_gate.py</code> nao existe aqui, entao os comandos '
            'citados nesta pagina ainda nao rodam. Para instalar: '
            '<code>python3 CAMINHO/DO/Neural-Flow-Framework/scripts/nf_install.py '
            f'--target . --name "{e(d.projeto)}"</code>.</p>'
        )

    # ── FinOps ──
    com_budget = [s for s in d.sprints if s.budget]
    if com_budget:
        linhas_f = []
        for s in com_budget:
            razao = s.razao_budget
            if razao is None:
                estado, pct, txt = "idle", 0.0, "em andamento"
            else:
                pct = razao * 100
                estado = "bad" if razao >= 1 else ("warn" if razao >= 0.7 else "ok")
                txt = f"{fmt(s.consumo)} / {fmt(s.budget)} ({pct:.0f}%)"
            cor = {"ok": "var(--series-1)", "warn": "var(--st-warning)",
                   "bad": "var(--st-critical)", "idle": "var(--muted-fill)"}[estado]
            linhas_f.append(
                f'<div class="fin"><span class="fin-l">Sprint {e(s.numero)}</span>'
                f'{barra(min(pct, 100), cor)}'
                f'<span class="fin-v {estado}-t">{e(txt)}</span></div>'
            )
        aviso = ('<p class="nota">Limite de alerta em 70%. Consumo &ge; 100% do budget sem '
                 'mitigacao registrada reprova no guard <code>budget</code> (B3).</p>')
        corpo_fin = "".join(linhas_f) + aviso
    else:
        corpo_fin = ('<p class="vazio">Nenhuma sprint declara <code>Token budget</code>. '
                     'O Circuit Breaker exige orcamento declarado por sprint (B1).</p>')

    if tel is not None and getattr(tel, "disponivel", False) and com_budget:
        ativa_b = ativa if ativa and ativa.budget else None
    else:
        ativa_b = None
    if ativa_b is not None:
        medido = tel.geral.faturavel
        declarado = ativa_b.consumo
        corpo_fin += (
            '<div class="sep"></div><p class="sub">Declarado x medido — sprint ativa</p>'
            f'<div class="fin"><span class="fin-l">Declarado</span>'
            f'{barra(100 if declarado else 0, "var(--muted-fill)")}'
            f'<span class="fin-v">{fmt(declarado) if declarado else "em andamento"}</span></div>'
            f'<div class="fin"><span class="fin-l">Medido</span>'
            f'{barra(min(medido / (ativa_b.budget or medido or 1) * 100, 100), "var(--series-3)")}'
            f'<span class="fin-v">{fmt(medido)}</span></div>'
            f'<p class="nota">O medido vem dos transcripts locais e cobre {d.janela_dias} dias do projeto '
            'inteiro, nao so desta sprint — use como ordem de grandeza para calibrar o '
            'proximo budget, nao como substituto do registro.</p>'
        )

    if d.grafo and (d.grafo["tokens_in"] or d.grafo["tokens_out"]):
        tin, tout = d.grafo["tokens_in"], d.grafo["tokens_out"]
        corpo_fin += (
            '<div class="sep"></div><p class="sub">Tokens gastos na construcao do indice</p>'
            f'<div class="fin"><span class="fin-l">Entrada</span>{barra(100, "var(--series-1)")}'
            f'<span class="fin-v">{fmt(tin)}</span></div>'
            f'<div class="fin"><span class="fin-l">Saida</span>'
            f'{barra(min(tout / max(tin, 1) * 100, 100), "var(--series-2)")}'
            f'<span class="fin-v">{fmt(tout)}</span></div>'
        )

    # ── smoke-gate ──
    s = d.smoke
    if not s["configurado"]:
        corpo_smoke = ('<p class="vazio">smoke-gate nao configurado. '
                       'Instale com <code>install.sh</code> ou registre o servidor MCP.</p>')
    else:
        estado = "ok" if s["rodou"] else "warn"
        quando = s.get("quando", "nunca")
        achados = s.get("achados", {})
        det = ""
        if achados:
            ordem = [("critical", "critical"), ("warning", "warning"), ("info", "info")]
            det = '<div class="sev">' + "".join(
                f'<span class="sev-i {k}"><span aria-hidden="true">&#9679;</span>'
                f'{achados.get(k, 0)} {rot}</span>'
                for k, rot in ordem if k in achados
            ) + "</div>"
        corpo_smoke = f"""
        <dl class="kv">
          <div><dt>Versao</dt><dd class="mono">{e(s.get('versao') or 'nao fixada')}</dd></div>
          <div><dt>Ultimo audit</dt><dd class="{estado}-t">{e(quando)}</dd></div>
        </dl>{det}
        <p class="nota">Rode <code>npx smoke-gate audit --since origin/main</code> no PR.
        O relatorio <code>audit-report.md</code> e a evidencia do gate.</p>"""

    # ── Grafo ──
    if d.grafo:
        g = d.grafo
        corpo_grafo = f"""
        <div class="stats">
          <div><span class="s-v">{fmt(g['nos'])}</span><span class="s-k">nos</span></div>
          <div><span class="s-v">{fmt(g['arestas'])}</span><span class="s-k">arestas</span></div>
          <div><span class="s-v">{fmt(g['comunidades'])}</span><span class="s-k">comunidades</span></div>
          <div><span class="s-v">{fmt(g['arquivos'])}</span><span class="s-k">arquivos</span></div>
        </div>
        {botoes_grafo(g['artefatos'], rel_grafo)}
        <p class="sub">Maiores comunidades, por numero de nos</p>
        {barras_horizontais(g['top'], "var(--series-1)")}
        <p class="nota">Atualizado em {e(g['atualizado'])}.
        {'<strong>' + str(g['ambiguas']) + ' arestas AMBIGUOUS</strong> — sao os pontos onde a especificacao deixou uma relacao sem fechar.' if g['ambiguas'] else ''}
        Consulte o indice antes de ler arquivo: custa ~48x menos tokens.</p>"""
    else:
        corpo_grafo = (
            '<p class="vazio">Nenhum indice em <code>graphify-out/</code>. '
            'O Vetor de Contexto pede indice antes de leitura: consultar o grafo custa '
            '~48x menos tokens que reler os arquivos, e a deteccao de comunidades expoe '
            'relacao que ninguem pensaria em consultar.</p>'
            '<p class="nota">Para construir: <code>graphify &lt;caminho&gt;</code>. '
            'Depois disso este card passa a linkar o grafo interativo, a wiki e o '
            'relatorio. Exemplo do que e gerado: '
            '<a href="https://github.com/Graphify-Labs/graphify" target="_blank" '
            'rel="noopener noreferrer">graphify</a>.</p>'
        )

    # ── Loop ──
    if d.loop.get("ativo"):
        l = d.loop
        pct = (l["feitos"] / l["total"] * 100) if l["total"] else 0
        conf = l["confianca"]
        total_conf = sum(conf.values()) or 1
        barras_conf = "".join(
            f'<div class="hbar"><span class="hbar-label">{k.title()}</span>'
            f'<div class="hbar-track"><div class="hbar-fill" '
            f'style="width:{v / total_conf * 100:.1f}%;background:{cor}"></div></div>'
            f'<span class="hbar-val">{v}</span></div>'
            for (k, v), cor in zip(
                conf.items(),
                ("var(--st-good)", "var(--series-1)", "var(--st-warning)"),
            )
        )
        corpo_loop = f"""
        <div class="row">
          <div class="hero"><span class="hero-n">{pct:.0f}<span class="hero-u">%</span></span>
            <span class="hero-l">{l['feitos']} de {l['total']} itens</span></div>
          <div class="grow">{barra(pct, "var(--series-3)", 10)}
            <dl class="kv">
              <div><dt>Iteracoes</dt><dd>{l['iteracoes']}</dd></div>
              <div><dt>Bloqueados</dt><dd>{l['bloqueados']}</dd></div>
              <div><dt>Divergencias</dt><dd class="{'warn-t' if l['divergencias'] else ''}">{l['divergencias']}</dd></div>
            </dl>
          </div>
        </div>
        <div class="sep"></div>
        <p class="sub">Confianca declarada por iteracao</p>{barras_conf}
        <p class="nota">Item marcado pronto nunca pode ser <code>BAIXA</code> —
        o guard <code>calibration</code> reprova (C2).</p>"""
    else:
        corpo_loop = ('<p class="vazio">Loop nao iniciado. O estado vive em '
                      '<code>build/</code> — plano, diario e divergencias.</p>')

    # ── Consumo real ──
    if tel is not None and getattr(tel, "disponivel", False):
        g = tel.geral
        por_modelo = sorted(tel.por_modelo.items(), key=lambda kv: -kv[1].faturavel)[:5]
        dias_ord = sorted(tel.por_dia.items())[-14:]
        ferramentas = [(nome_ferramenta(n), v) for n, v in
                       sorted(tel.ferramentas.items(), key=lambda kv: -kv[1])[:7]]
        dias_ritmo = sorted({d for d, _ in tel.por_hora})[-7:]
        sessoes = sorted(tel.detalhe_sessoes.values(),
                         key=lambda s: -s.consumo.faturavel)[:5]

        serie = (
            f'<p class="sub">Consumo por dia, tokens faturaveis</p>'
            f'{area_temporal([(d, c.faturavel) for d, c in dias_ord], "var(--series-1)")}'
            f'<div class="eixo"><span>{e(dias_ord[0][0][5:])}</span>'
            f'<span>{e(dias_ord[-1][0][5:])}</span></div>'
            if len(dias_ord) > 1 else ""
        )
        provedores = ""
        if len(getattr(tel, "por_provedor", {})) > 1:
            itens = sorted(tel.por_provedor.items(), key=lambda kv: -kv[1].faturavel)
            provedores = (
                '<div class="sep"></div><p class="sub">Por provedor</p>'
                + barras_horizontais([(n, c.faturavel) for n, c in itens],
                                     "var(--series-3)", True)
                + '<p class="nota">Volume, nao custo: o preco por token difere entre '
                  'provedores e modelos, entao a soma serve para comparar esforco, '
                  'nao gasto.</p>'
            )
        html_sessoes = "".join(
            f'<div class="ses"><span class="ses-n">{e(s.id[:8])}</span>'
            f'<span class="ses-d">{s.duracao_min} min · {s.consumo.requisicoes} req</span>'
            f'<span class="ses-v num">{fmt(s.consumo.faturavel)}</span></div>'
            for s in sessoes
        )
        corpo_tokens = f"""
        <div class="topo-t">
          <div class="hero"><span class="hero-n num">{fmt(g.faturavel)}</span>
            <span class="hero-l">tokens faturaveis</span></div>
          {anel(g.aproveitamento_cache, "var(--series-3)", "de cache")}
        </div>
        <dl class="kv kv-4">
          <div><dt>Entrada</dt><dd class="num">{fmt(g.entrada)}</dd></div>
          <div><dt>Saida</dt><dd class="num">{fmt(g.saida)}</dd></div>
          <div><dt>Cache escrito</dt><dd class="num">{fmt(g.cache_escrito)}</dd></div>
          <div><dt>Cache lido</dt><dd class="num">{fmt(g.cache_lido)}</dd></div>
          <div><dt>Requisicoes</dt><dd class="num">{g.requisicoes}</dd></div>
          <div><dt>Sessoes</dt><dd class="num">{tel.sessoes}</dd></div>
        </dl>
        {serie}
        {provedores}
        <div class="sep"></div>
        <p class="sub">Por modelo, em tokens faturaveis</p>
        {barras_horizontais([(m, c.faturavel) for m, c in por_modelo], "var(--series-1)", True)}
        <p class="nota">{"Todo o periodo registrado" if d.janela_dias > 3650 else f"Janela de {d.janela_dias} dias"}. So numeros sao lidos —
        o conteudo das mensagens nunca e acessado.</p>"""

        corpo_ritmo = (
            f'<p class="sub">Requisicoes por hora, '
            f'{"ultimos " + str(len(dias_ritmo)) + " dias" if len(dias_ritmo) > 1 else "no dia registrado"}'
            f' (UTC)</p>'
            f'{mapa_ritmo(tel.por_hora, dias_ritmo)}'
            f'<div class="sep"></div><p class="sub">Ferramentas mais usadas</p>'
            f'{barras_horizontais(ferramentas, "var(--series-2)", True)}'
            f'<div class="sep"></div><p class="sub">Sessoes por consumo</p>'
            f'<div class="sess">{html_sessoes}</div>'
        )
    else:
        motivo = getattr(tel, "motivo", "coletor indisponivel") if tel else "coletor indisponivel"
        corpo_ritmo = f'<p class="vazio">Sem telemetria: {e(motivo)}.</p>'
        corpo_tokens = (
            f'<p class="vazio">Sem telemetria: {e(motivo)}.</p>'
            '<p class="nota">O consumo medido vem dos transcripts locais do Claude Code. '
            'Sem eles, o quadro de FinOps continua valendo — so que com o valor '
            '<em>declarado</em> na sprint, nao o medido.</p>'
        )

    # ── Protocolos ──
    mapa_estado = {g["nome"]: g["estado"] for g in d.guards}
    linhas_p = []
    for nome, guard in PROTOCOLOS:
        if guard == "smoke":
            est = "pass" if d.smoke.get("rodou") else ("inativo" if d.smoke.get("configurado") else "ausente")
            rot = "smoke-gate"
        elif guard:
            est = mapa_estado.get(guard, "ausente")
            rot = f"nf_gate {guard}"
        else:
            est, rot = "manual", "auditoria mensal"
        cls = {"pass": "ok", "fail": "bad", "manual": "idle"}.get(est, "idle")
        icone = {"pass": "&#10003;", "fail": "&#10007;"}.get(est, "&#9679;")
        texto_ajuda = AJUDA_PROTOCOLOS.get(nome)
        botao_p = ""
        if texto_ajuda:
            slug = sem_acento(nome).lower().replace(" ", "-")
            botao_p, janela_p = ajuda(f"prot-{slug}", nome, f"<p>{texto_ajuda}</p>", True)
            janelas.append(janela_p)
        linhas_p.append(
            f'<div class="prot"><span class="prot-n">{e(nome)}{botao_p}</span>'
            f'<code class="prot-g">{e(rot)}</code>'
            f'<span class="pill {cls}"><span aria-hidden="true">{icone}</span>'
            f'{e({"pass": "trava", "fail": "reprovando", "manual": "manual"}.get(est, "inativo"))}'
            f'</span></div>'
        )
    corpo_prot = (
        f'<div class="prots">{"".join(linhas_p)}</div>'
        '<p class="nota">"manual" nao e falha: sao os protocolos cuja aderencia se audita, '
        'nao se trava. Guard aspiracional declarado como tal — nunca apresentado como se travasse.</p>'
    )

    # ── Historico de sprints ──
    botao_h, janela_h = ajuda(*(("historico",) + AJUDA_QUADROS["historico"]))
    janelas.append(janela_h)
    if d.sprints:
        linhas_s = "".join(
            f'<tr><td>{e(s.numero)}</td><td>{e(s.titulo)}</td>'
            f'<td>{e(s.status)}</td><td class="mono">{e(s.autonomia)}</td>'
            f'<td>{s.feitos}/{s.total}</td>'
            f'<td class="mono">{fmt(s.consumo)} / {fmt(s.budget)}</td></tr>'
            for s in d.sprints
        )
        corpo_hist = (
            '<div class="tbl-scroll"><table class="tbl">'
            '<thead><tr><th>#</th><th>Titulo</th><th>Status</th>'
            '<th>Aut.</th><th>Itens</th><th>Tokens</th></tr></thead>'
            f'<tbody>{linhas_s}</tbody></table></div>'
        )
        card_hist = (f'<section class="card wide" id="historico"><h2>Historico de sprints{botao_h}</h2>'
                     f'{corpo_hist}</section>')
    else:
        card_hist = f'<section class="card wide" id="historico"><h2>Historico de sprints{botao_h}</h2><p class="vazio">Nenhuma sprint registrada.</p></section>'

    # ── Base documental do produto ──
    linhas_doc = []
    rotulos_doc = {
        "aprovado": ("&#10003;", "Aprovado", "ok"),
        "aguardando_revisao": ("&#9679;", "Aguardando revisao", "idle"),
        "alterado_apos_aprovacao": ("&#8635;", "Alterado apos aprovacao", "bad"),
        "incompleto": ("&#9888;", "Incompleto", "bad"),
        "ausente": ("&#8212;", "Ausente", "idle"),
    }
    for doc in d.documentos_produto.get("documents", []):
        icone_doc, rotulo_doc, estado_doc = rotulos_doc.get(
            doc["status"], ("&#9679;", "Aguardando revisao", "idle")
        )
        arquivo_doc = (f'<code class="mono">{e(doc["arquivo"])}</code>'
                       if doc.get("arquivo") else '<span class="muted">Nenhum arquivo mapeado</span>')
        lacunas = "".join(f"<li>{e(item)}</li>" for item in doc.get("lacunas", []))
        candidatos = "".join(f"<li>{e(item)}</li>" for item in doc.get("candidatos", []))
        detalhes_doc = (f'<ul class="doc-gaps">{lacunas}{candidatos}</ul>'
                        if lacunas or candidatos else "")
        if doc.get("arquivo"):
            proxima = ('Abra o arquivo e complete as lacunas listadas.' if doc["status"] in {"incompleto", "alterado_apos_aprovacao"}
                       else 'Solicite a revisao da IA e registre a aprovacao do usuario.'
                       if doc["status"] == "aguardando_revisao" else
                       'A justificativa de nao aplicabilidade foi aprovada.'
                       if doc.get("revisao") == "nao_se_aplica" else 'A base aprovada esta vigente.')
        else:
            proxima = ('Mapeie um documento existente em .neural-flow.json ou crie-o usando o exemplo.'
                       if doc["status"] != "aprovado" else 'A justificativa de nao aplicabilidade foi aprovada.')
        sample = doc.get("exemplo")
        if sample is None:
            corpo_exemplo = '<p class="vazio">Exemplo indisponivel nesta instalacao. Reinstale o Neural-Flow para restaurar os modelos oficiais.</p>'
        else:
            corpo_exemplo = f'<pre class="doc-example">{e(sample)}</pre>'
        alvo_exemplo = f"exemplo-documento-{e(doc['id'])}"
        janelas.append(
            f'<div popover id="{alvo_exemplo}" class="pop doc-pop" role="dialog" '
            f'aria-label="Exemplo: {e(doc["titulo"])}">'
            f'<div class="doc-pop-head"><div><span class="eyebrow">Exemplo do Neural-Flow. Adapte ao seu projeto.</span>'
            f'<h3>{e(doc["titulo"])}</h3></div>'
            f'<button type="button" class="pop-x" popovertarget="{alvo_exemplo}" '
            f'popovertargetaction="hide" aria-label="Fechar exemplo">&times;</button></div>'
            f'<div class="doc-pop-body">{corpo_exemplo}</div></div>'
        )
        linhas_doc.append(
            f'<article class="doc-card"><div class="doc-card-head"><div><h3>{e(doc["titulo"])}</h3>'
            f'<p>{e(doc["descricao"])}</p></div><span class="pill {estado_doc}">'
            f'<span aria-hidden="true">{icone_doc}</span>{e(rotulo_doc)}</span></div>'
            f'<div class="doc-path"><span>Arquivo</span>{arquivo_doc}</div>{detalhes_doc}'
            f'<p class="doc-next">Proxima acao: {e(proxima)}</p>'
            f'<button type="button" class="doc-example-trigger" popovertarget="{alvo_exemplo}" '
            f'aria-haspopup="dialog" aria-controls="{alvo_exemplo}">Ver exemplo</button></article>'
        )
    doc_aviso = ""
    if not d.documentos_produto.get("enabled"):
        doc_aviso += '<p class="nota">O diagnostico esta disponivel. O gate de sprints sera ativado quando o projeto adotar a base documental.</p>'
    if d.documentos_produto.get("configuration_error"):
        doc_aviso += f'<p class="nota warn-t">{e(d.documentos_produto["configuration_error"])}</p>'
    doc_issue_html = "".join(f"<li>{e(item)}</li>" for item in d.documentos_produto.get("issues", []))
    if doc_issue_html:
        doc_aviso += f'<ul class="doc-gaps">{doc_issue_html}</ul>'
    corpo_documentos = (
        '<div class="doc-list">' + "".join(linhas_doc) + "</div>" + doc_aviso
        if linhas_doc else '<p class="vazio">Nenhum papel documental configurado.</p>'
    )

    # ── Atualizacoes e Versao ──
    info_up = d.atualizacoes or {}
    status_up = info_up.get("status", "atualizado")
    versao_up = info_up.get("versao_framework", "v1")
    skills_tot = info_up.get("skills_total", 27)
    skills_ag = info_up.get("skills_agents", 0)
    skills_cl = info_up.get("skills_claude", 0)
    portas_ok = info_up.get("portas_ok", 0)
    portas_tot = info_up.get("portas_total", 8)
    indice_ok = info_up.get("indice_ok", False)
    guards_ok = info_up.get("guards_ok", False)
    pendencias_up = info_up.get("pendencias", [])

    if status_up == "atualizado":
        banner_cls = "ok"
        banner_tag = "Versao do framework"
        banner_titulo = f"Instalacao conforme e atualizada · {versao_up}"
        banner_sub = (
            "Todas as 27 skills operacionais estao instaladas em .agents/skills e .claude/skills, "
            "portas de entrada sincronizadas e guards ativos."
        )
    elif status_up == "nao_instalado":
        banner_cls = "alerta"
        banner_tag = "Nao instalado"
        banner_titulo = "Neural-Flow ainda nao instalado neste projeto"
        banner_sub = "Execute o instalador para configurar governanca, 27 skills operacionais e guards."
    else:
        banner_cls = "alerta"
        banner_tag = "Atualizacao disponivel"
        banner_titulo = f"{len(pendencias_up)} atualizacao(oes) pendente(s) · {versao_up}"
        banner_sub = (
            "Ha componentes ou capacidades recentes do framework prontas para sincronizacao neste projeto."
        )

    badge_skills = "ok" if (skills_ag == skills_tot and skills_cl == skills_tot) else ("pendente" if (skills_ag > 0 or skills_cl > 0) else "ausente")
    badge_portas = "ok" if (portas_ok == portas_tot) else ("pendente" if portas_ok > 0 else "ausente")
    badge_indice = "ok" if indice_ok else "ausente"
    badge_guards = "ok" if guards_ok else "ausente"

    grid_items = f"""<div class="update-grid">
  <div class="update-item">
    <div class="update-item-head"><strong>Skills Operacionais</strong><span class="update-badge {badge_skills}">{"OK" if badge_skills == "ok" else ("Pendente" if badge_skills == "pendente" else "Ausente")}</span></div>
    <p>27 skills (mattpocock/skills): {skills_ag}/{skills_tot} em <code>.agents/skills</code>, {skills_cl}/{skills_tot} em <code>.claude/skills</code>.</p>
  </div>
  <div class="update-item">
    <div class="update-item-head"><strong>Portas de Entrada</strong><span class="update-badge {badge_portas}">{"OK" if badge_portas == "ok" else ("Pendente" if badge_portas == "pendente" else "Ausente")}</span></div>
    <p>{portas_ok}/{portas_tot} arquivos com marca e instrucoes de skills (Gemini, Claude, Copilot, Cursor...).</p>
  </div>
  <div class="update-item">
    <div class="update-item-head"><strong>Indice de Regras</strong><span class="update-badge {badge_indice}">{"OK" if badge_indice == "ok" else "Ausente"}</span></div>
    <p>Fonte de verdade compacta em <code>.neural-flow/indice-regras.md</code>.</p>
  </div>
  <div class="update-item">
    <div class="update-item-head"><strong>Guards Locais</strong><span class="update-badge {badge_guards}">{"OK" if badge_guards == "ok" else "Ausente"}</span></div>
    <p>Gate local de pre-commit e CI em <code>scripts/nf_gate.py</code>.</p>
  </div>
</div>"""

    pendencias_html = ""
    if pendencias_up:
        lista_p = "".join(f"<li>{e(p)}</li>" for p in pendencias_up)
        pendencias_html = f"""<div class="update-pendencias">
  <strong>Diagnostico de itens pendentes:</strong>
  <ul class="update-pendencias-list">{lista_p}</ul>
</div>"""

    instrucoes_html = """<div class="update-box">
  <div class="update-box-head"><strong>Como atualizar este projeto com seguranca:</strong></div>
  <p class="sub">A atualizacao e <strong>nao-destrutiva</strong>: seu <code>AGENTS.md</code>, <code>MEMORY.md</code>, <code>docs/sprints/</code> e codigo de negocio nunca sao sobrescritos.</p>
  <ol class="update-steps">
    <li><span class="update-step-num">1</span><div class="update-step-body"><strong>Sincronizar templates e skills operacionais:</strong><p>Copia as 27 skills para <code>.agents/skills/</code> e <code>.claude/skills/</code> preservando arquivos existentes:</p><code>python3 scripts/nf_install.py --target .</code></div></li>
    <li><span class="update-step-num">2</span><div class="update-step-body"><strong>Regerar portas de entrada dos agentes:</strong><p>Atualiza as portas (GEMINI.md, Copilot, Cursor, etc.) com a versao e instrucoes de skills:</p><code>python3 scripts/nf_agentes.py --escrever</code></div></li>
    <li><span class="update-step-num">3</span><div class="update-step-body"><strong>Validar conformidade com os guards:</strong><p>Executa a bateria de guards para certificar que tudo esta integro antes do commit:</p><code>python3 scripts/nf_gate.py</code></div></li>
  </ol>
</div>"""

    corpo_atualizacoes = f"""<div class="update-banner {banner_cls}">
  <div>
    <span class="eyebrow">{e(banner_tag)}</span>
    <h3>{e(banner_titulo)}</h3>
    <p class="sub" style="margin-bottom:0">{e(banner_sub)}</p>
  </div>
</div>
{grid_items}
{pendencias_html}
{instrucoes_html}"""

    # ── Skills Operacionais (mattpocock/skills) ──
    skills_lista = d.skills if d.skills else [dict(s, ativa=True, em_agents=True, em_claude=True) for s in CATALOGO_SKILLS]
    skills_ativas_cnt = sum(1 for s in skills_lista if s.get("ativa"))
    skills_total_cnt = len(skills_lista)
    skills_fluxo_cnt = sum(1 for s in skills_lista if s.get("fluxo_principal"))

    def modal_skill(s: dict) -> str:
        pop_id = f"ficha-skill-{s['id']}"
        passos_li = "".join(
            f'<li><span class="skill-step-idx">{idx}</span><span>{e(passo)}</span></li>'
            for idx, passo in enumerate(s.get("passos", []), 1)
        )
        conecta_chips = "".join(f'<code class="skill-chip">{e(c)}</code>' for c in s.get("conecta", []))
        guias_chips = "".join(
            f'<code class="skill-chip guide">{e(g)}</code>' for g in s.get("guias", [])
        ) or '<span class="muted small">Embutido em SKILL.md (sem arquivo auxiliar externo)</span>'
        fluxo_badge = (
            '<span class="skill-role-badge main">Fluxo Principal · Idea → Ship</span>'
            if s.get("fluxo_principal")
            else f'<span class="skill-role-badge">{e(s.get("papel", "Operacional"))}</span>'
        )
        return (
            f'<div popover id="{pop_id}" class="pop doc-pop" role="dialog" aria-label="Guia tatico — {e(s["titulo"])}">'
            f'<div class="doc-pop-head">'
            f'<div><span class="eyebrow" style="color:var(--marca)">Ficha Tatica da Skill · Fase {s.get("fase", 1)}</span>'
            f'<h3>{e(s["titulo"])} <code class="skill-cmd">{e(s["comando"])}</code></h3></div>'
            f'<button type="button" class="pop-x" popovertarget="{pop_id}" popovertargetaction="hide" aria-label="Fechar">×</button>'
            f'</div>'
            f'<div class="doc-pop-body skill-pop-body">'
            f'<div class="skill-pop-top">{fluxo_badge}'
            f'<span class="skill-path-tag"><code>.agents/skills/{e(s["id"])}/SKILL.md</code></span>'
            f'<span class="skill-path-tag"><code>.claude/skills/{e(s["id"])}/SKILL.md</code></span></div>'
            f'<p class="skill-pop-desc">{e(s["descricao"])}</p>'
            f'<div class="skill-pop-io">'
            f'<div class="skill-io-box"><span class="eyebrow">Quando acionar</span><p>{e(s["quando"])}</p></div>'
            f'<div class="skill-io-box"><span class="eyebrow">Entrada esperada</span><p>{e(s.get("entradas", "Contexto da tarefa"))}</p></div>'
            f'<div class="skill-io-box"><span class="eyebrow">Saida produzida</span><p>{e(s.get("saidas", "Artefato ou decisao validada"))}</p></div>'
            f'</div>'
            f'<div class="skill-pop-section"><h4>Passo a passo tatico da skill</h4>'
            f'<ol class="skill-steps-list">{passos_li}</ol></div>'
            f'<div class="skill-pop-dual">'
            f'<div class="skill-pop-section"><h4>Conecta com</h4><div class="skill-chip-row">{conecta_chips}</div></div>'
            f'<div class="skill-pop-section"><h4>Arquivos de apoio no pacote</h4><div class="skill-chip-row">{guias_chips}</div></div>'
            f'</div>'
            f'<div class="skill-pop-sovereignty"><strong>Regra de Soberania Neural-Flow (ADR-010):</strong> {e(s["soberania"])}</div>'
            f'</div></div>'
        )

    def card_skill(s: dict) -> str:
        st_cls = "ok" if s.get("ativa") else ("pendente" if (s.get("em_agents") or s.get("em_claude")) else "idle")
        st_txt = "Ativa" if s.get("ativa") else ("Pendente" if (s.get("em_agents") or s.get("em_claude")) else "Ausente")
        main_cls = " sc-main-flow" if s.get("fluxo_principal") else ""
        papel_cls = "main" if s.get("fluxo_principal") else "aux"
        papel_txt = s.get("papel", "Operacional")
        pop_id = f"ficha-skill-{s['id']}"
        conecta_html = "".join(f'<code class="skill-chip">{e(c)}</code>' for c in s.get("conecta", [])[:3])
        guias_lista = s.get("guias", [])
        guias_badge = (
            f'<span class="skill-guide-count">+{len(guias_lista)} {"guia" if len(guias_lista) == 1 else "guias"}</span>'
            if guias_lista else ""
        )
        return (
            f'<article class="skill-card{main_cls}">'
            f'<div class="skill-card-top">'
            f'<div class="skill-card-head">'
            f'<div><div class="skill-title-row"><strong>{e(s["titulo"])}</strong>{guias_badge}</div>'
            f'<div class="skill-badges-row"><code class="skill-cmd">{e(s["comando"])}</code>'
            f'<span class="skill-role-badge {papel_cls}">{e(papel_txt)}</span></div></div>'
            f'<span class="pill {st_cls}"><span aria-hidden="true">&#9679;</span> {st_txt}</span>'
            f'</div>'
            f'<p class="skill-desc">{e(s["descricao"])}</p>'
            f'</div>'
            f'<div class="skill-meta">'
            f'<div class="skill-row"><strong>Quando usar:</strong> {e(s["quando"])}</div>'
            f'<div class="skill-io-grid">'
            f'<div class="skill-io-cell"><span>Entrada</span><strong>{e(s.get("entradas", "—"))}</strong></div>'
            f'<div class="skill-io-cell"><span>Saida</span><strong>{e(s.get("saidas", "—"))}</strong></div>'
            f'</div>'
            f'<div class="skill-row skill-soberania"><strong>Soberania NF:</strong> {e(s["soberania"])}</div>'
            f'<div class="skill-card-foot">'
            f'<div class="skill-chip-row">{conecta_html}</div>'
            f'<button type="button" class="skill-detail-btn" popovertarget="{pop_id}">Ver guia tatico ↗</button>'
            f'</div>'
            f'</div>'
            f'</article>'
        )

    for s_item in skills_lista:
        janelas.append(modal_skill(s_item))

    fases_skills = [
        ("descoberta", 1, "Descoberta, Entrevista e Alinhamento", "9 skills",
         "Entrevista implacavel, alinhamento com ADRs/glossario, pesquisa de fontes primarias e decomposicao de ambiguidades antes do codigo."),
        ("modelagem", 2, "Especificacao, Modelagem e Planejamento", "5 skills",
         "Sintese em especificacao estruturada, modelo de dominio (ubiquitous language), deep modules e tickets tracer-bullet."),
        ("implementacao", 3, "Implementacao, TDD, Arquitetura e Bugs", "9 skills",
         "Ciclo estrito red-green-refactor, execucao de spec/tickets, auditoria de acoplamento, diagnostico cientifico e prototipos."),
        ("revisao", 4, "Revisao, Entrega e Continuidade", "4 skills",
         "Auditoria em dois eixos paralelos (Standards + Spec), corpo de PR rastreavel, handoff entre sessoes e retrospectiva."),
    ]

    blocos_fases = []
    for cls_fase, num_fase, nome_fase, rotulo_fase, desc_fase in fases_skills:
        itens_fase = [s for s in skills_lista if s.get("fase") == num_fase]
        ativas_fase = sum(1 for s in itens_fase if s.get("ativa"))
        total_fase = len(itens_fase)
        status_fase = f"{ativas_fase}/{total_fase} ativas" if total_fase else rotulo_fase
        cards_html = "".join(card_skill(s) for s in itens_fase)
        blocos_fases.append(
            f'<div class="skill-group sg-{cls_fase}">'
            f'<div class="skill-group-head">'
            f'<div class="skill-group-title"><span class="skill-group-badge">{num_fase}</span>'
            f'<div><h3>{e(nome_fase)}</h3><p class="skill-group-desc">{e(desc_fase)}</p></div></div>'
            f'<span class="pill ok"><span aria-hidden="true">&#9679;</span> {e(status_fase)}</span></div>'
            f'<div class="skills-grid">{cards_html}</div>'
            f'</div>'
        )

    mapa_arquitetura_skills = """<div class="skills-flow-map">
  <div class="flow-col flow-col-main">
    <div class="flow-col-head">
      <span class="eyebrow">Caminho Critico · Idea → Ship</span>
      <h4>Fluxo Principal em 6 Etapas</h4>
      <p>O pipeline padrao de ponta a ponta desenhado por Matt Pocock e ancorado nos gates do Neural-Flow.</p>
    </div>
    <ol class="flow-pipeline">
      <li><span class="flow-num">01</span><div><strong>Entrevista &amp; Decisao</strong><p><code>/grill-with-docs</code> ou <code>/grill-me</code> estressam premissas e gravam ADRs (<code>nf_gate.py adr</code>).</p></div></li>
      <li><span class="flow-num">02</span><div><strong>Desvio Opcional: Spike</strong><p><code>/prototype</code> valida UI ou modelo de estado em branch isolada descartavel.</p></div></li>
      <li><span class="flow-num">03</span><div><strong>Spec &amp; Tracer Bullets</strong><p><code>/to-spec</code> formaliza <code>docs/modulos/</code> (<code>nf_gate.py spec</code>) e <code>/to-tickets</code> fatia em fatias verticais.</p></div></li>
      <li><span class="flow-num">04</span><div><strong>Execucao + TDD Estrito</strong><p><code>/implement</code> + <code>/tdd</code> rodam um teste por vez (Red → Green → Refactor) no escopo da sprint.</p></div></li>
      <li><span class="flow-num">05</span><div><strong>Review Duplo &amp; PR</strong><p><code>/code-review</code> audita Standards + Spec em paralelo; <code>/pr</code> redige a entrega apos <code>nf_gate.py</code> verde.</p></div></li>
      <li><span class="flow-num">06</span><div><strong>Retro &amp; Evolucao</strong><p><code>/retro</code> + <code>/writing-for-agents</code> transformam atritos da sessao em regras permanentes.</p></div></li>
    </ol>
  </div>
  <div class="flow-col">
    <div class="flow-col-head">
      <span class="eyebrow">Portas de Entrada Taticas</span>
      <h4>3 On-Ramps + Saude Arquitetural</h4>
      <p>Nem todo trabalho comeca de uma ideia em branco. Entre pelo ponto exato do problema:</p>
    </div>
    <div class="flow-cards-stack">
      <div class="flow-mini-card">
        <div class="flow-mini-top"><strong>1. Fila Bruta de Issues/PRs</strong><code class="skill-cmd">/triage</code></div>
        <p>Classifica bugs, features e duvidas em estado bruto e produz briefs prontos para agentes.</p>
      </div>
      <div class="flow-mini-card">
        <div class="flow-mini-top"><strong>2. Bug Dificil ou Regressao</strong><code class="skill-cmd">/diagnosing-bugs</code></div>
        <p>Loop cientifico: reproduzir → isolar → hipotese → testar → corrigir com teste de regressao via <code>/tdd</code>.</p>
      </div>
      <div class="flow-mini-card">
        <div class="flow-mini-top"><strong>3. Iniciativa Multi-Sessao</strong><code class="skill-cmd">/wayfinder</code></div>
        <p>Mapeia trabalho grande demais para uma sessao como grafo de tickets de decisao.</p>
      </div>
      <div class="flow-mini-card highlight">
        <div class="flow-mini-top"><strong>Saude &amp; Deep Modules</strong><code class="skill-cmd">/improve-codebase-architecture</code></div>
        <p>Escaneia acoplamento e modulos rasos, gera relatorio HTML e conduz refatoracao estrutural.</p>
      </div>
    </div>
  </div>
  <div class="flow-col">
    <div class="flow-col-head">
      <span class="eyebrow">Camada de Vocabulario &amp; Contexto</span>
      <h4>Base Conceitual &amp; Smart Zone (~150k)</h4>
      <p>Duas skills de vocabulario alimentam todas as demais, e 5 fronteiras protegem a janela de contexto:</p>
    </div>
    <div class="flow-cards-stack">
      <div class="flow-mini-card">
        <div class="flow-mini-top"><strong>Linguagem Ubiqua</strong><code class="skill-cmd">/domain-modeling</code></div>
        <p>Alinha termos do negocio com os tipos do codigo e mantem <code>GLOSSARY.md</code> sem sinonimos ambiguos.</p>
      </div>
      <div class="flow-mini-card">
        <div class="flow-mini-top"><strong>Interfaces Profundas</strong><code class="skill-cmd">/codebase-design</code></div>
        <p>Principios de John Ousterhout: interface simples escondendo implementacao rica e testavel na fronteira.</p>
      </div>
      <div class="flow-boundary-box">
        <strong>Fronteiras de Fase (Smart Zone ~150k tokens)</strong>
        <p>A qualidade do raciocinio degrada apos ~150k tokens. Em cada transicao de fase, escolha:</p>
        <div class="boundary-pills">
          <span class="boundary-pill"><strong>Continue</strong> &lt;100k tokens</span>
          <span class="boundary-pill"><strong>/clear</strong> artefato salvo em disco</span>
          <span class="boundary-pill"><strong>/handoff</strong> 100k–150k tokens</span>
          <span class="boundary-pill"><strong>Subagent</strong> leitura pesada isolada</span>
          <span class="boundary-pill"><strong>/compact</strong> recurso de emergencia</span>
        </div>
      </div>
    </div>
  </div>
</div>"""

    filtro_skills_html = (
        '<fieldset class="skills-nav-filter">'
        '<legend style="position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)">Filtrar skills por fase</legend>'
        f'<input type="radio" name="sf-filter" id="sf-todas" checked><label class="skills-filter-tab" for="sf-todas">Todas as Skills <span>({skills_total_cnt})</span></label>'
        f'<input type="radio" name="sf-filter" id="sf-fluxo"><label class="skills-filter-tab" for="sf-fluxo">Fluxo Principal: Idea → Ship <span>({skills_fluxo_cnt})</span></label>'
        '<input type="radio" name="sf-filter" id="sf-descoberta"><label class="skills-filter-tab" for="sf-descoberta">1. Descoberta &amp; Alinhamento <span>(9)</span></label>'
        '<input type="radio" name="sf-filter" id="sf-modelagem"><label class="skills-filter-tab" for="sf-modelagem">2. Modelagem &amp; Especificacao <span>(5)</span></label>'
        '<input type="radio" name="sf-filter" id="sf-implementacao"><label class="skills-filter-tab" for="sf-implementacao">3. Implementacao &amp; TDD <span>(9)</span></label>'
        '<input type="radio" name="sf-filter" id="sf-revisao"><label class="skills-filter-tab" for="sf-revisao">4. Revisao &amp; Entrega <span>(4)</span></label>'
        '</fieldset>'
    )

    status_skills_str = f"{skills_ativas_cnt}/{skills_total_cnt}" if skills_total_cnt else "—"
    corpo_skills = (
        '<div class="command-bar healthy" style="margin-bottom:18px">'
        '<div class="command-copy"><span class="eyebrow" style="color:var(--st-good)">Arsenal Integrado (ADR-010 · mattpocock/skills)</span>'
        f'<strong>{e(status_skills_str)} Skills Operacionais Prontas para Invocacao Autonoma e Manual</strong>'
        '<span>Instaladas simultaneamente em <code>.agents/skills/</code> e <code>.claude/skills/</code> com <code>disable-model-invocation: false</code> e subordinadas aos guards do Neural-Flow. Clique em <em>Ver guia tatico</em> em qualquer card para abrir o passo a passo completo.</span></div>'
        '<div class="command-actions"><span class="risk-badge healthy"><i></i> Autonomia + Guards Ativos</span></div></div>'
        + mapa_arquitetura_skills
        + filtro_skills_html
        + f'<div class="skills-groups">{"".join(blocos_fases)}</div>'
    )

    # ── Raio-X e Governanca do Projeto ──
    total_sprints = len(d.sprints)
    sprints_concluidas = sum(1 for s in d.sprints if s.status == "concluida")
    sprints_andamento = sum(1 for s in d.sprints if s.status == "em andamento")
    total_adrs = d.adrs.get("total", 0)
    adrs_aceitos = d.adrs.get("por_status", {}).get("aceito", 0)

    info_p = d.info_projeto or {}
    regras_total = info_p.get("regras_total", 19)
    acoes_seguras = info_p.get("acoes_seguras", 3)
    acoes_aprovacao = info_p.get("acoes_aprovacao", 3)
    scripts_total = info_p.get("scripts_total", 21)
    testes_total = info_p.get("testes_total", 2)
    protocolos_total = info_p.get("protocolos_total", len(PROTOCOLOS))

    artefatos_core = info_p.get("artefatos_core") or [
        {"nome": "AGENTS.md", "caminho": "AGENTS.md", "papel": "Fonte unica de verdade (tool-agnostica)", "guard": "nf_gate.py agentes", "existe": True},
        {"nome": "CLAUDE.md", "caminho": "CLAUDE.md", "papel": "Principios de execucao Karpathy + Skills", "guard": "nf_gate.py agentes", "existe": True},
        {"nome": "Indice de Regras", "caminho": ".neural-flow/indice-regras.md", "papel": "Mapa estruturado de regras e guards", "guard": "nf_indice_regras.py", "existe": True},
        {"nome": "AI Safety Policy", "caminho": ".github/AI_SAFETY.md", "papel": "Proibicoes absolutas e acoes criticas", "guard": "A0/A1 Gatekeeper", "existe": True},
        {"nome": "Memoria Consolidada", "caminho": "MEMORY.md", "papel": "Padroes e aprendizados permanentes", "guard": "Ciclo de revisao", "existe": True},
        {"nome": "Action Policy Gateway", "caminho": ".neural-flow/action-policy.json", "papel": "Allowlist de comandos e sandbox", "guard": "nf_action_gateway.py", "existe": True},
        {"nome": "Pre-commit Hook", "caminho": ".githooks/pre-commit", "papel": "Bloqueio local antes do commit", "guard": "nf_gate.py", "existe": True},
        {"nome": "CI Autorizativo", "caminho": ".github/workflows/neural-flow-gates.yml", "papel": "Verificacao soberana no GitHub Actions", "guard": "CI Pipeline", "existe": True},
    ]
    portas_agentes = info_p.get("portas_agentes") or [
        {"ferramenta": "OpenAI Codex / Jules / Devin", "arquivo": "AGENTS.md", "modo": "Leitura direta da fonte", "existe": True},
        {"ferramenta": "Claude Code (Anthropic)", "arquivo": "CLAUDE.md", "modo": "Principios Karpathy + 27 Skills", "existe": True},
        {"ferramenta": "Gemini Code Assist / CLI", "arquivo": "GEMINI.md", "modo": "Porta gerada e sincronizada", "existe": True},
        {"ferramenta": "GitHub Copilot", "arquivo": ".github/copilot-instructions.md", "modo": "Porta gerada e sincronizada", "existe": True},
        {"ferramenta": "Cursor IDE", "arquivo": ".cursor/rules/neural-flow.mdc", "modo": "Regra MDC alwaysApply: true", "existe": True},
        {"ferramenta": "Cline", "arquivo": ".clinerules", "modo": "Porta gerada e sincronizada", "existe": True},
        {"ferramenta": "Windsurf", "arquivo": ".windsurfrules", "modo": "Porta gerada e sincronizada", "existe": True},
        {"ferramenta": "Amp / Sourcegraph", "arquivo": "AGENT.md", "modo": "Porta gerada e sincronizada", "existe": True},
        {"ferramenta": "Aider", "arquivo": "CONVENTIONS.md", "modo": "Porta gerada e sincronizada", "existe": True},
        {"ferramenta": "Hermes Agent", "arquivo": "HERMES.md", "modo": "Porta gerada e sincronizada", "existe": True},
    ]

    art_ok_cnt = sum(1 for a in artefatos_core if a.get("existe"))
    art_tot_cnt = len(artefatos_core)
    art_ratio_str = f"{art_ok_cnt}/{art_tot_cnt}" if art_tot_cnt else "—"

    portas_ok_cnt = sum(1 for p in portas_agentes if p.get("existe"))
    portas_tot_cnt = len(portas_agentes)
    portas_ratio_str = f"{portas_ok_cnt}/{portas_tot_cnt}" if portas_tot_cnt else "—"

    linhas_artefatos = "".join(
        f'<div class="inv-row">'
        f'<div class="inv-main"><strong>{e(a["nome"])}</strong><code>{e(a["caminho"])}</code><span class="inv-role">{e(a["papel"])}</span></div>'
        f'<div class="inv-side"><span class="inv-guard">{e(a["guard"])}</span>'
        f'<span class="pill {"ok" if a.get("existe") else "idle"}"><span aria-hidden="true">&#9679;</span> {"Ativo" if a.get("existe") else "Opcional"}</span></div>'
        f'</div>'
        for a in artefatos_core
    )

    linhas_portas = "".join(
        f'<div class="inv-row">'
        f'<div class="inv-main"><strong>{e(p["ferramenta"])}</strong><code>{e(p["arquivo"])}</code><span class="inv-role">{e(p["modo"])}</span></div>'
        f'<div class="inv-side"><span class="pill {"ok" if p.get("existe") else "bad"}"><span aria-hidden="true">&#9679;</span> {"Sincronizada" if p.get("existe") else "Ausente"}</span></div>'
        f'</div>'
        for p in portas_agentes
    )

    adrs_lista_proj = d.adrs.get("lista", [])
    if adrs_lista_proj:
        cards_adrs = "".join(
            f'<div class="adr-card">'
            f'<div class="adr-card-top"><code class="adr-num">{e("-".join(a.get("arquivo", "ADR").replace(".md", "").split("-")[:2]))}</code>'
            f'<span class="pill {"ok" if a.get("status") == "aceito" else "idle"}"><span aria-hidden="true">&#9679;</span> {e(a.get("status", "proposto").capitalize())}</span></div>'
            f'<strong>{e(a.get("titulo") or a.get("arquivo", ""))}</strong>'
            f'<span class="adr-meta"><code>docs/adr/{e(a.get("arquivo", ""))}</code></span>'
            f'</div>'
            for a in adrs_lista_proj
        )
        bloco_adrs_html = (
            f'<div class="project-subpanel" style="margin-top:16px">'
            f'<div class="project-subpanel-head">'
            f'<div><span class="eyebrow">Decisoes Arquiteturais Imutaveis</span><h4>Catalogo de ADRs do Projeto ({total_adrs})</h4></div>'
            f'<span class="pill ok"><span aria-hidden="true">&#9679;</span> {adrs_aceitos} Aceitos · Sequenciais</span>'
            f'</div>'
            f'<div class="adr-grid">{cards_adrs}</div>'
            f'</div>'
        )
    else:
        bloco_adrs_html = ""

    corpo_projeto = f"""<div class="project-stats-grid">
  <div class="project-stat-box">
    <span class="eyebrow">Pilar 1 · Supervisao em 3 Camadas</span>
    <h4>Karpathy + 27 Skills + Guards</h4>
    <p>Combina postura comportamental (<code>CLAUDE.md</code>), metodo tatico por etapa (<code>mattpocock/skills</code>) e validadores deterministicos em stdlib pura (ADR-002 e ADR-010).</p>
    <div class="project-tools-list">
      <span class="tool-chip"><i></i> {f"{guards_pass}/{guards_ativos} Guards Verdes" if guards_ativos else "Guards sob demanda"}</span>
      <span class="tool-chip"><i></i> {regras_total} Regras Indexadas</span>
      <span class="tool-chip"><i></i> {scripts_total} Scripts Stdlib</span>
    </div>
  </div>

  <div class="project-stat-box">
    <span class="eyebrow">Pilar 2 · Matriz de Autonomia A0–A3</span>
    <h4>Action Gateway &amp; Git Seguro</h4>
    <p>Escopos sensiveis (auth, segredos, migracoes, billing, producao) exigem A0/A1. Toda acao passa por allowlist versionada; <code>git commit</code> e <code>git push</code> exigem ordem explicita.</p>
    <div class="project-tools-list">
      <span class="tool-chip"><i></i> {acoes_seguras} Acoes Allowlist</span>
      <span class="tool-chip"><i></i> {acoes_aprovacao} Acoes A0/A1</span>
      <span class="tool-chip"><i></i> Commit/Push Protegidos</span>
    </div>
  </div>

  <div class="project-stat-box">
    <span class="eyebrow">Pilar 3 · Protocolo de Calibracao</span>
    <h4>Evidencia Antes de Conclusao</h4>
    <p>Toda afirmacao tecnica declara nivel de confianca lido da evidencia: <strong>ALTA</strong> (execucao verificada), <strong>MEDIA</strong> (contrato/ADR vigente) ou <strong>BAIXA</strong> (inferencia — nunca fecha item).</p>
    <div class="project-tools-list">
      <span class="tool-chip"><i></i> {protocolos_total} Protocolos Ativos</span>
      <span class="tool-chip"><i></i> {testes_total} Suites de Teste</span>
      <span class="tool-chip"><i></i> smoke-gate Integrado</span>
    </div>
  </div>

  <div class="project-stat-box">
    <span class="eyebrow">Pilar 4 · Economia de Contexto &amp; FinOps</span>
    <h4>Indice Primeiro &amp; Estado em Disco</h4>
    <p>Consultar <code>.neural-flow/indice-regras.md</code> ou o grafo antes de varrer codigo economiza ~48x em tokens. Sprints, ADRs e diario mantem a memoria fora do chat.</p>
    <div class="project-tools-list">
      <span class="tool-chip"><i></i> {total_adrs} ADRs ({adrs_aceitos} Aceitos)</span>
      <span class="tool-chip"><i></i> {total_sprints} Sprints ({sprints_concluidas} Concluidas{f", {sprints_andamento} Ativa" if sprints_andamento else ""})</span>
      <span class="tool-chip"><i></i> Circuit Breaker Ativo</span>
    </div>
  </div>
</div>

<div class="project-dual-grid">
  <div class="project-subpanel">
    <div class="project-subpanel-head">
      <div><span class="eyebrow">Inspecao em Disco</span><h4>Artefatos Nucleares de Governanca</h4></div>
      <span class="pill ok"><span aria-hidden="true">&#9679;</span> {e(art_ratio_str)} Presentes</span>
    </div>
    <div class="inv-list">{linhas_artefatos}</div>
  </div>

  <div class="project-subpanel">
    <div class="project-subpanel-head">
      <div><span class="eyebrow">Compatibilidade Multi-Agente</span><h4>Portas de Entrada Sincronizadas</h4></div>
      <span class="pill ok"><span aria-hidden="true">&#9679;</span> {e(portas_ratio_str)} Sincronizadas</span>
    </div>
    <div class="inv-list">{linhas_portas}</div>
  </div>
</div>
{bloco_adrs_html}"""

    botoes_quadro = {}
    for chave, (titulo, corpo) in AJUDA_QUADROS.items():
        if chave == "historico":
            continue
        botao, janela = ajuda(chave, titulo, corpo)
        botoes_quadro[f"ajuda_{chave}"] = botao
        janelas.append(janela)

    pendencias = prioridades(d)
    corpo_prioridades = ''.join(
        f'<li><a href="#{alvo}"><span class="priority-index">{i:02}</span><span><strong>{e(titulo)}</strong>'
        f'<span class="priority-detail">{e(detalhe)}</span></span><span class="priority-arrow" aria-hidden="true">↗</span></a></li>'
        for i, (titulo, detalhe, alvo) in enumerate(pendencias, 1)
    )
    corpo_prioridades = (f'<ol class="priority-list">{corpo_prioridades}</ol>' if pendencias else
                         '<p class="vazio">Nenhuma pendencia identificada nos sinais disponiveis. Confira tambem os controles inativos e os registros ausentes.</p>')
    if pendencias:
        resumo_status = f"{len(pendencias)} pontos precisam de revisao."
        resumo_detalhe = "Comece pelos controles reprovados, bloqueios e prazos."
        resumo_tipo = "attention"
        resumo_rotulo = "Revisao pendente"
    elif not guards_ativos:
        resumo_status = "Nenhum controle ativo para avaliar este projeto."
        resumo_detalhe = "Configure os artefatos e gere o painel novamente para verificar o estado."
        resumo_tipo = "neutral"
        resumo_rotulo = "Sem verificacao ativa"
    else:
        resumo_status = "Os controles ativos deste retrato estao conformes."
        resumo_detalhe = "Acompanhe o consumo e mantenha as evidencias atualizadas."
        resumo_tipo = "healthy"
        resumo_rotulo = "Verificacoes conformes"

    meses = ("jan", "fev", "mar", "abr", "mai", "jun",
             "jul", "ago", "set", "out", "nov", "dez")
    try:
        _d, _h = d.gerado_em.split()
        _a, _m, _dia = _d.split("-")
        gerado_legivel = f"{_dia} {meses[int(_m) - 1]} {_a} · {_h}"
    except (ValueError, IndexError):
        gerado_legivel = d.gerado_em

    pagina = TEMPLATE.format(
        arquitetura=diagrama_arquitetura("nf-preview-"),
        arquitetura_ampliada=diagrama_arquitetura("nf-modal-"),
        fundo_giyu=imagem_embutida("theme-giyu.jpg"),
        fundo_tanjiro=imagem_embutida("theme-tanjiro.jpg"),
        gerado_legivel=e(gerado_legivel),
        janelas="".join(janelas),
        **botoes_quadro,
        projeto=e(d.projeto),
        gerado=e(d.gerado_em),
        tiles=html_tiles,
        sprint=corpo_sprint,
        guards=corpo_guards,
        finops=corpo_fin,
        smoke=corpo_smoke,
        grafo=corpo_grafo,
        loop=corpo_loop,
        tokens=corpo_tokens,
        ritmo=corpo_ritmo,
        protocolos=corpo_prot,
        documentos_produto=corpo_documentos,
        atualizacoes=corpo_atualizacoes,
        skills_secao=corpo_skills,
        ficha_projeto=corpo_projeto,
        prioridades=corpo_prioridades,
        total_prioridades=len(pendencias),
        total_documentos=len(d.documentos_produto.get("documents", [])),
        historico=card_hist,
        resumo_status=resumo_status,
        resumo_detalhe=resumo_detalhe,
        resumo_tipo=resumo_tipo,
        resumo_rotulo=resumo_rotulo,
        idioma_controle=controle_idioma(),
    )
    return pagina.replace("</body>", script_idioma() + "\n" + script_interface() + "\n</body>")


TEMPLATE = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{projeto} — Neural-Flow</title>
<style>
/* Paletas selecionáveis — sem JavaScript, para manter o dashboard autocontido. */
:root {{
  color-scheme: light;
  --bg:#f3f6f8; --surface:#ffffff; --line:#dde5e9; --line-forte:#c3d0d7;
  --text:#17242c; --text-2:#52616a; --muted:#75838b; --muted-fill:#e8eef1;
  /* Identidade e teal; marcas de DADO usam a paleta validada por script.
     O teal em L~0,5 tem croma abaixo do piso (le como cinza) e fica a ΔE 11,2
     do verde para visao normal — abaixo do piso de 15, que rotulo nao desculpa. */
  --series-1:#2a78d6; --series-2:#eb6834; --series-3:#1baf7a;
  --st-good:#0ca30c; --st-warning:#fab219; --st-serious:#ec835a; --st-critical:#d03b3b;
  --ground:linear-gradient(125deg,#f5f8f9 0%,#edf2f4 100%);
  --marca:#146c84; --marca-t:#ffffff;
  --alerta-borda:#e8d2cb; --alerta-fundo:linear-gradient(90deg,#fff 55%,#fff8f5);
  --ok-borda:#cee5da; --ok-fundo:linear-gradient(90deg,#fff 55%,#f6fbf8);
  --alerta-texto:#9f3535; --acao-hover:#f2f8f9; --tile-ruim:#fffafa; --tile-ruim-b:#efd9d6;
  --radius:12px; --shadow:0 1px 2px rgba(25,43,52,.03),0 12px 32px rgba(25,43,52,.055);
  --character-image:none; --character-position:right -4rem top 4rem; --character-size:420px auto;
  --pattern-image:none; --pattern-position:0 0; --pattern-size:auto;
  --character-veil:linear-gradient(90deg,rgba(243,246,248,.98),rgba(243,246,248,.7)); --character-opacity:0;
  /* Rampa sequencial (perto de zero → maximo), azul da paleta validada */
  --ramp-1:#cde2fb; --ramp-2:#9ec5f4; --ramp-3:#6da7ec; --ramp-4:#3987e5;
  --ramp-5:#256abf; --ramp-6:#184f95; --ramp-7:#0d366b;
}}
body:has(#theme-dark:checked) {{
  color-scheme: dark;
  --bg:#0f1114; --surface:#171a1f; --line:#272c33; --line-forte:#39404a;
  --text:#ffffff; --text-2:#b9c1cc; --muted:#7f8a98; --muted-fill:#2b3138;
  --series-1:#3987e5; --series-2:#d95926; --series-3:#199e70;
  --st-good:#0ca30c; --st-warning:#fab219; --st-serious:#ec835a; --st-critical:#d03b3b;
  --ground:linear-gradient(125deg,#101317 0%,#0d1013 100%);
  --marca:#5fb3c9; --marca-t:#0f1114;
  --alerta-borda:#4a2f2f; --alerta-fundo:linear-gradient(90deg,#171a1f 55%,#1f1718);
  --ok-borda:#24443a; --ok-fundo:linear-gradient(90deg,#171a1f 55%,#151f1b);
  --alerta-texto:#e58a8a; --acao-hover:#1d2229; --tile-ruim:#1c1618; --tile-ruim-b:#3d2b2d;
  --shadow:0 1px 2px rgba(0,0,0,.4), 0 12px 32px rgba(0,0,0,.3);
  /* No escuro a rampa sobe em luminosidade: mais valor, mais claro */
  --ramp-1:#184f95; --ramp-2:#256abf; --ramp-3:#2a78d6; --ramp-4:#3987e5;
  --ramp-5:#5598e7; --ramp-6:#6da7ec; --ramp-7:#9ec5f4;
}}
/* Giyu: azul-neblina, vinho e o padrão verde/laranja do haori. */
body:has(#theme-giyu:checked) {{
  color-scheme: light;
  --bg:#e8eef0; --surface:#f8faf9; --line:#c7d2d6; --line-forte:#a6b7bd;
  --text:#172532; --text-2:#40545d; --muted:#667a83; --muted-fill:#d9e2e4;
  --series-1:#327fa2; --series-2:#c66b43; --series-3:#356b5a;
  --st-good:#28734d; --st-warning:#b87822; --st-serious:#bd6947; --st-critical:#a14556;
  --ground:linear-gradient(128deg,#edf3f4 0%,#d9e3e6 56%,#e9dce1 100%);
  --marca:#6f3549; --marca-t:#ffffff;
  --alerta-borda:#dbc1c9; --alerta-fundo:linear-gradient(90deg,#f8faf9 52%,#f5e9ed);
  --ok-borda:#bdd5c8; --ok-fundo:linear-gradient(90deg,#f8faf9 52%,#e9f2ed);
  --alerta-texto:#893c4d; --acao-hover:#e4eef0; --tile-ruim:#f9f2f3; --tile-ruim-b:#e3cfd4;
  --shadow:0 1px 2px rgba(28,49,59,.04),0 14px 34px rgba(52,78,89,.09);
  --ramp-1:#d7e8ed; --ramp-2:#b3d2dc; --ramp-3:#82b6c7; --ramp-4:#5d9db4;
  --ramp-5:#397c99; --ramp-6:#295d77; --ramp-7:#1c4058;
  --character-image:url("{fundo_giyu}"); --character-position:right -1rem top 3rem; --character-size:360px auto;
  --pattern-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='180' height='156' viewBox='0 0 180 156'%3E%3Crect width='180' height='156' fill='%23172f2a'/%3E%3Cg stroke='%23edd27a' stroke-width='2'%3E%3Cpath d='M90 4 150 38 90 72 30 38Z' fill='%23e0bd60'/%3E%3Cpath d='M30 38 90 72 90 140 30 106Z' fill='%231f5647'/%3E%3Cpath d='M150 38 90 72 90 140 150 106Z' fill='%230f352d'/%3E%3Cpath d='M0 106 30 123 30 156 0 139Z' fill='%23743a4c'/%3E%3Cpath d='M180 106 150 123 150 156 180 139Z' fill='%23743a4c'/%3E%3C/g%3E%3Cpath d='M90 72V140M30 38l60 34 60-34' stroke='%23112824' stroke-width='3' fill='none'/%3E%3C/svg%3E"); --pattern-position:0 0; --pattern-size:180px 156px;
  --character-veil:linear-gradient(90deg,rgba(232,238,240,.98) 0%,rgba(232,238,240,.88) 48%,rgba(232,238,240,.28) 100%); --character-opacity:.78;
}}
/* Tanjiro: água noturna, ciano e verde do haori, com vinho de apoio. */
body:has(#theme-tanjiro:checked) {{
  color-scheme: dark;
  --bg:#08192b; --surface:#10273b; --line:#244259; --line-forte:#41617a;
  --text:#f4fbff; --text-2:#b8d2df; --muted:#83a8ba; --muted-fill:#1c3950;
  --series-1:#43c9e8; --series-2:#d87e8f; --series-3:#43bf91;
  --st-good:#57c98e; --st-warning:#f0b94e; --st-serious:#e38b60; --st-critical:#ec7186;
  --ground:radial-gradient(circle at 92% -8%,#155d8b 0%,transparent 31%),linear-gradient(130deg,#071629 0%,#0b2740 100%);
  --marca:#4fd3b4; --marca-t:#071a2b;
  --alerta-borda:#714151; --alerta-fundo:linear-gradient(90deg,#10273b 50%,#2d1a2b);
  --ok-borda:#2c6758; --ok-fundo:linear-gradient(90deg,#10273b 50%,#10352f);
  --alerta-texto:#f2a1ae; --acao-hover:#18364d; --tile-ruim:#261b2a; --tile-ruim-b:#623a4c;
  --shadow:0 1px 2px rgba(0,8,16,.42),0 15px 38px rgba(0,8,16,.36);
  --ramp-1:#17405e; --ramp-2:#1c6289; --ramp-3:#278bac; --ramp-4:#35b6d3;
  --ramp-5:#62d4e8; --ramp-6:#9ce8f1; --ramp-7:#d4f7f7;
  --character-image:url("{fundo_tanjiro}"); --character-position:right -8rem top 1rem; --character-size:620px auto;
  --character-veil:linear-gradient(90deg,rgba(8,25,43,.98) 0%,rgba(8,25,43,.84) 45%,rgba(8,25,43,.24) 100%); --character-opacity:.62;
}}
*,*::before,*::after{{box-sizing:border-box}}
body{{position:relative;isolation:isolate;margin:0;background:var(--bg);color:var(--text);
  font:15px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif;
  -webkit-font-smoothing:antialiased}}
body::before{{content:"";position:fixed;inset:0;z-index:0;pointer-events:none;opacity:var(--character-opacity);background-image:var(--character-veil),var(--character-image),var(--pattern-image);background-position:center,var(--character-position),var(--pattern-position);background-repeat:no-repeat,no-repeat,repeat;background-size:cover,var(--character-size),var(--pattern-size);transition:opacity .35s ease}}
.wrap{{position:relative;z-index:1;max-width:1180px;margin:0 auto;padding:40px 24px 72px}}
header{{display:flex;flex-wrap:wrap;gap:16px;align-items:baseline;
  justify-content:space-between;margin-bottom:28px}}
h1{{font-size:26px;font-weight:640;letter-spacing:-.02em;margin:0}}
h1 span{{color:var(--muted);font-weight:450}}
.meta{{color:var(--muted);font-size:13px}}
h2{{font-size:11.5px;font-weight:660;letter-spacing:.1em;text-transform:uppercase;
  color:var(--text-2);margin:0 0 3px;display:flex;align-items:center}}
.card>h2::after{{content:"";flex:1;height:1px;margin-left:12px;background:var(--line)}}
.sub{{color:var(--muted);font-size:13px;margin:0 0 12px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:18px;
  align-items:start}}
.card{{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);
  padding:20px 22px;box-shadow:var(--shadow)}}
.card.wide{{grid-column:1/-1}}
/* Tiles */
.tiles{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
  gap:14px;margin-bottom:22px}}
.tile{{position:relative;background:var(--surface);border:1px solid var(--line);
  border-radius:var(--radius);padding:18px;display:flex;flex-direction:column;gap:3px;
  box-shadow:var(--shadow);overflow:hidden}}
.tile::before{{content:"";position:absolute;inset:0 0 auto;height:2px;
  background:var(--muted-fill)}}
.tile.ok::before{{background:var(--st-good)}}
.tile.bad::before{{background:var(--st-critical)}}
.tile.warn::before{{background:var(--st-warning)}}
.tile-k{{font-size:11px;letter-spacing:.07em;text-transform:uppercase;color:var(--muted)}}
.tile-v{{font-size:28px;font-weight:660;letter-spacing:-.025em;line-height:1.15;
  font-variant-numeric:tabular-nums}}
.tile-s{{font-size:12.5px;color:var(--text-2)}}
/* Hero + linhas */
.row{{display:flex;gap:22px;align-items:flex-start;flex-wrap:wrap}}
.grow{{flex:1;min-width:230px}}
.hero{{display:flex;flex-direction:column;min-width:112px}}
.hero-n{{font-size:42px;font-weight:680;letter-spacing:-.035em;line-height:1}}
.num{{font-variant-numeric:tabular-nums;font-feature-settings:"tnum" 1}}
.hero-u{{font-size:20px;color:var(--muted);margin-left:2px}}
.hero-l{{font-size:12.5px;color:var(--muted);margin-top:4px}}
/* Barra: extremidade arredondada 4px, ancorada na base */
.track{{background:var(--muted-fill);border-radius:999px;overflow:hidden;margin:10px 0}}
.fill{{height:100%;border-radius:0 4px 4px 0;transition:width .3s}}
/* Chave/valor */
.kv{{margin:14px 0 0;display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
  gap:10px 18px}}
.kv div{{display:flex;flex-direction:column;gap:1px}}
.kv dt{{font-size:11px;letter-spacing:.05em;text-transform:uppercase;color:var(--muted)}}
.kv dd{{margin:0;font-size:14px;font-weight:520;font-variant-numeric:tabular-nums}}
.kv .span{{grid-column:1/-1}}
/* Guards */
.guards{{display:grid;gap:10px}}
.guard{{position:relative;border:1px solid var(--line);border-radius:10px;
  padding:12px 14px 12px 16px;display:flex;flex-direction:column;gap:4px;
  background:var(--bg)}}
.guard::before{{content:"";position:absolute;left:0;top:12px;bottom:12px;width:2px;
  border-radius:2px;background:var(--muted-fill)}}
.guard.pass::before{{background:var(--st-good)}}
.guard.fail::before{{background:var(--st-critical)}}
.guard-h{{display:flex;justify-content:space-between;align-items:center;gap:10px}}
.guard-n{{font-weight:580;font-size:14.5px}}
.guard-d{{font-size:12.5px;color:var(--text-2)}}
.guard-c{{font-size:11.5px;color:var(--muted)}}
.achados{{margin:6px 0 0;padding-left:18px;font-size:12.5px;color:var(--text-2)}}
.achados li{{margin:2px 0}}
/* Pill: icone + rotulo, nunca cor sozinha */
.pill{{display:inline-flex;align-items:center;gap:5px;font-size:11.5px;font-weight:580;
  padding:2px 9px;border-radius:999px;border:1px solid var(--line);white-space:nowrap}}
.pill.ok{{color:var(--st-good)}} .pill.bad{{color:var(--st-critical)}}
.pill.idle{{color:var(--muted)}}
/* Base documental */
.doc-list{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,310px),1fr));gap:12px}}
.doc-card{{display:flex;flex-direction:column;align-items:flex-start;gap:10px;min-width:0;
  padding:15px;border:1px solid var(--line);border-radius:10px;background:var(--bg)}}
.doc-card-head{{display:flex;align-items:flex-start;justify-content:space-between;gap:10px;width:100%}}
.doc-card-head h3{{margin:0;font-size:15px;font-weight:630}}
.doc-card-head p{{margin:3px 0 0;color:var(--muted);font-size:12.5px}}
.doc-path{{display:flex;flex-direction:column;gap:3px;font-size:11.5px;color:var(--muted);max-width:100%}}
.doc-path code{{overflow-wrap:anywhere}}
.doc-gaps{{margin:0;padding-left:18px;color:var(--text-2);font-size:12px}}
.doc-gaps li+li{{margin-top:3px}}
.doc-next{{margin:0;color:var(--text-2);font-size:12px}}
.doc-example-trigger{{margin-top:auto;border:1px solid var(--line-forte);border-radius:7px;
  background:var(--surface);color:var(--text);padding:7px 11px;font:inherit;font-size:12px;
  font-weight:600;cursor:pointer}}
.doc-example-trigger:hover{{border-color:var(--series-1);color:var(--series-1)}}
.doc-example-trigger:focus-visible{{outline:2px solid var(--series-1);outline-offset:2px}}
.doc-pop{{width:min(920px,calc(100vw - 28px));max-width:unset;max-height:88vh;
  border:1px solid var(--line);border-radius:var(--radius);padding:0;overflow:hidden;
  background:var(--surface);color:var(--text);box-shadow:var(--shadow)}}
@supports selector(:popover-open) {{.doc-pop::backdrop{{background:rgba(11,11,11,.52)}}}}
.doc-pop-head{{display:flex;align-items:center;justify-content:space-between;gap:16px;
  padding:15px 18px;border-bottom:1px solid var(--line)}}
.doc-pop-head h3{{margin:3px 0 0;font-size:18px}}
.doc-pop-body{{max-height:calc(88vh - 72px);overflow:auto;padding:16px 20px}}
.doc-example{{margin:0;white-space:pre-wrap;overflow-wrap:anywhere;color:var(--text-2);
  font:12.5px/1.65 ui-monospace,SFMono-Regular,Menlo,monospace}}
/* FinOps */
.fin{{display:grid;grid-template-columns:88px 1fr auto;align-items:center;gap:12px;
  margin:8px 0}}
.fin-l{{font-size:12.5px;color:var(--text-2)}}
.fin-v{{font-size:12.5px;font-variant-numeric:tabular-nums;color:var(--text-2)}}
.fin .track{{margin:0}}
/* Barras horizontais */
.hbar{{display:grid;grid-template-columns:minmax(90px,150px) 1fr 42px;align-items:center;
  gap:12px;margin:7px 0}}
.hbar-label{{font-size:12.5px;color:var(--text-2);overflow:hidden;text-overflow:ellipsis;
  white-space:nowrap}}
.hbar-track{{background:var(--muted-fill);border-radius:999px;height:8px;overflow:hidden}}
.hbar-fill{{height:100%;border-radius:0 4px 4px 0}}
.hbar-val{{font-size:12.5px;text-align:right;font-variant-numeric:tabular-nums;
  color:var(--text-2)}}
/* Acesso aos artefatos do grafo */
.btns{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;
  margin:4px 0 18px}}
.btn{{display:flex;flex-direction:column;gap:2px;padding:10px 12px;text-decoration:none;
  border:1px solid var(--line);border-radius:10px;background:var(--bg);
  transition:border-color .15s,transform .15s}}
.btn:hover{{border-color:var(--series-1);transform:translateY(-1px)}}
.btn:focus-visible{{outline:2px solid var(--series-1);outline-offset:2px}}
.btn-t{{font-size:13.5px;font-weight:580;color:var(--marca)}}
.btn-d{{font-size:11.5px;color:var(--muted)}}
@media (prefers-reduced-motion:reduce){{.btn{{transition:none}}.btn:hover{{transform:none}}}}
/* Stats */
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(88px,1fr));gap:14px;
  margin-bottom:18px}}
.stats div{{display:flex;flex-direction:column}}
.s-v{{font-size:24px;font-weight:640;letter-spacing:-.02em;font-variant-numeric:tabular-nums}}
.s-k{{font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}}
/* Severidade */
.sev{{display:flex;gap:14px;flex-wrap:wrap;margin:12px 0}}
.sev-i{{display:inline-flex;align-items:center;gap:5px;font-size:12.5px;font-weight:540}}
.sev-i.critical{{color:var(--st-critical)}} .sev-i.warning{{color:var(--st-warning)}}
.sev-i.info{{color:var(--series-1)}}
/* Tabela */
.tbl{{width:100%;border-collapse:collapse;font-size:13px}}
.tbl th{{text-align:left;font-size:11px;letter-spacing:.06em;text-transform:uppercase;
  color:var(--muted);font-weight:600;padding:0 10px 8px 0;border-bottom:1px solid var(--line)}}
.tbl td{{padding:9px 10px 9px 0;border-bottom:1px solid var(--line);vertical-align:top}}
.tbl td:first-child{{white-space:nowrap;font-weight:520}}
.tbl td.mono{{white-space:nowrap;font-size:11.5px}}
.tbl tr:last-child td{{border-bottom:none}}
.tbl-scroll{{overflow-x:auto;margin:0 -2px}}
.prots{{display:grid;gap:2px}}
.prot{{display:grid;grid-template-columns:1fr auto;align-items:center;gap:4px 10px;
  padding:9px 0;border-bottom:1px solid var(--line)}}
.prot:last-child{{border-bottom:none}}
.prot-n{{font-size:14px;font-weight:520;min-width:0;overflow:hidden;text-overflow:ellipsis;
  white-space:nowrap}}
.prot-g{{grid-column:1;font-size:11.5px;color:var(--muted);background:none;padding:0;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.prot .pill{{grid-column:2;grid-row:1/3;justify-self:end}}
.tbl td:nth-child(2){{max-width:150px;overflow:hidden;text-overflow:ellipsis}}
.tbl td:last-child,.tbl th:last-child{{text-align:right;white-space:nowrap;padding-right:0}}
/* Serie temporal */
.svg-area{{width:100%;height:76px;display:block;margin:2px 0 0;overflow:visible}}
.eixo{{display:flex;justify-content:space-between;font-size:11px;color:var(--muted);
  font-variant-numeric:tabular-nums;margin-top:2px}}
/* Anel de proporcao */
.topo-t{{display:flex;align-items:center;justify-content:space-between;gap:18px;
  flex-wrap:wrap}}
.anel{{display:flex;align-items:center;gap:11px}}
.anel svg{{width:60px;height:60px;flex:none}}
.anel-t{{display:flex;flex-direction:column;line-height:1.2}}
.anel-v{{font-size:21px;font-weight:660;letter-spacing:-.02em;font-variant-numeric:tabular-nums}}
.anel-l{{font-size:11.5px;color:var(--muted)}}
.kv-4{{grid-template-columns:repeat(auto-fit,minmax(96px,1fr))}}
/* Mapa de ritmo */
.ritmo{{display:grid;gap:3px;margin:2px 0 10px}}
.ritmo-l{{display:grid;grid-template-columns:38px 1fr;align-items:center;gap:8px}}
.ritmo-d{{font-size:10.5px;color:var(--muted);font-variant-numeric:tabular-nums}}
.ritmo-c{{display:grid;grid-template-columns:repeat(24,1fr);gap:2px}}
.cel{{display:block;aspect-ratio:1;border-radius:2px;min-height:9px}}
.ritmo-h{{display:flex;justify-content:space-between;font-size:10px;color:var(--muted)}}
.escala{{display:flex;align-items:center;gap:3px;font-size:10.5px;color:var(--muted);
  margin-top:8px;flex-wrap:wrap}}
.escala .cel{{width:11px;height:11px;min-height:0;aspect-ratio:auto}}
.escala-p{{margin-left:auto;font-variant-numeric:tabular-nums}}
/* Sessoes */
.sess{{display:grid;gap:1px}}
.ses{{display:grid;grid-template-columns:1fr auto auto;align-items:baseline;gap:10px;
  padding:7px 0;border-bottom:1px solid var(--line)}}
.ses:last-child{{border-bottom:none}}
.ses-n{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px;
  color:var(--text-2)}}
.ses-d{{font-size:11.5px;color:var(--muted);font-variant-numeric:tabular-nums}}
.ses-v{{font-size:12.5px;font-weight:560;text-align:right;min-width:52px}}
/* Ajuda contextual — popover nativo, sem JavaScript */
.help{{all:unset;display:inline-flex;align-items:center;justify-content:center;
  width:17px;height:17px;margin-left:7px;border:1px solid var(--line);border-radius:50%;
  font-size:11px;font-weight:700;color:var(--muted);cursor:pointer;vertical-align:middle;
  transition:color .15s,border-color .15s,background .15s}}
.help:hover,.help:focus-visible{{color:var(--series-1);border-color:var(--series-1);
  background:var(--bg)}}
.help:focus-visible{{outline:2px solid var(--series-1);outline-offset:2px}}
.help-sm{{width:15px;height:15px;font-size:10px;margin-left:5px}}
/* Sem suporte a popover, o conteudo aparece embutido no fim do card: a
   explicacao continua legivel, so nao flutua. */
.pop{{border:1px solid var(--line);border-radius:var(--radius);background:var(--surface);
  color:var(--text);padding:0;max-width:min(560px,92vw);box-shadow:var(--shadow)}}
@supports selector(:popover-open) {{
  .pop{{margin:auto}}
  .pop::backdrop{{background:rgba(11,11,11,.45)}}
}}
.pop-h{{display:flex;align-items:center;justify-content:space-between;gap:12px;
  padding:16px 18px 10px;border-bottom:1px solid var(--line)}}
.pop-h h3{{margin:0;font-size:15.5px;font-weight:620;letter-spacing:-.01em}}
.pop-x{{all:unset;cursor:pointer;font-size:22px;line-height:1;color:var(--muted);
  padding:0 4px;border-radius:6px}}
.pop-x:hover{{color:var(--text)}}
.pop-x:focus-visible{{outline:2px solid var(--series-1);outline-offset:2px}}
.pop-b{{padding:14px 18px 18px;font-size:13.5px;line-height:1.62;color:var(--text-2);
  max-height:min(66vh,560px);overflow-y:auto}}
.pop-b p{{margin:0 0 11px}} .pop-b p:last-child{{margin-bottom:0}}
.pop-b strong{{color:var(--text)}}
@media (prefers-reduced-motion:reduce){{.help{{transition:none}}}}
/* Utilitarios */
.mono{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px}}
.muted{{color:var(--muted)}}
.small{{font-size:12px;font-weight:400}}
.ok-t{{color:var(--st-good)}} .warn-t{{color:var(--st-warning)}}
.bad-t{{color:var(--st-critical)}} .idle-t{{color:var(--muted)}}
.nota{{font-size:12px;color:var(--muted);margin:14px 0 0;line-height:1.5}}
.vazio{{font-size:13.5px;color:var(--muted);margin:6px 0 0;line-height:1.6}}
.sep{{height:1px;background:var(--line);margin:18px 0}}
code{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.9em;
  background:var(--muted-fill);padding:1px 5px;border-radius:4px}}
.guard-c,.achados code{{background:none;padding:0}}
footer{{margin-top:32px;color:var(--muted);font-size:12px;text-align:center}}
@media (max-width:640px){{
  .wrap{{padding:24px 14px 48px}} .hero-n{{font-size:34px}}
  .fin{{grid-template-columns:1fr}} .fin .track{{margin:4px 0}}
}}

body{{background:var(--ground);min-height:100dvh;
  font-family:ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}}
.wrap{{max-width:1480px;padding:26px 34px 64px}}
header{{margin-bottom:20px;padding-bottom:19px;border-bottom:1px solid var(--line);align-items:center}}
.brand-lockup{{display:flex;align-items:center;gap:12px}}.brand-mark{{display:grid;place-items:center;width:34px;height:34px;border-radius:9px;background:var(--marca);color:var(--marca-t);font-size:10px;font-weight:760;letter-spacing:.08em}}.brand-lockup h1{{font-size:20px;font-weight:720;letter-spacing:-.035em;line-height:1.05}}.brand-lockup h1 span{{font-weight:500}}.brand-lockup p{{margin:4px 0 0;font-size:12px;color:var(--muted)}}
.header-meta{{display:flex;align-items:center;gap:7px;font-size:12px;color:var(--muted);font-variant-numeric:tabular-nums}}.live-dot{{width:7px;height:7px;border-radius:50%;background:var(--st-good);box-shadow:0 0 0 3px color-mix(in srgb, var(--st-good) 18%, transparent)}}
.header-tools{{display:flex;align-items:center;gap:10px;flex-wrap:wrap;justify-content:flex-end}}.view-tabs,.theme-picker,.language-picker{{display:flex;align-items:center;gap:4px;padding:3px;border:1px solid var(--line);border-radius:9px;background:var(--surface);box-shadow:0 1px 0 rgba(255,255,255,.16) inset}}.view-tabs legend,.view-tabs input,.theme-picker legend,.theme-picker input,.language-picker legend,.language-picker input{{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}}.view-tab,.theme-option{{position:relative;display:grid;place-items:center;border-radius:6px;cursor:pointer;transition:background .18s,transform .18s}}.view-tab{{min-height:27px;padding:0 9px;font-size:11px;font-weight:650;color:var(--text-2)}}.theme-option{{width:29px;height:27px}}.view-tab:hover,.theme-option:hover{{background:var(--acao-hover)}}.view-tab:active,.theme-option:active{{transform:scale(.96)}}.view-tabs input:focus-visible + .view-tab,.theme-picker input:focus-visible + .theme-option,.language-picker input:focus-visible + .view-tab{{outline:2px solid var(--series-1);outline-offset:2px}}.view-tabs input:checked + .view-tab,.theme-picker input:checked + .theme-option,.language-picker input:checked + .view-tab{{background:var(--muted-fill);color:var(--text)}}.theme-swatch{{display:block;width:15px;height:15px;border-radius:50%;border:1px solid rgba(255,255,255,.46);box-shadow:0 0 0 1px rgba(18,35,45,.18)}}.theme-swatch.light{{background:linear-gradient(135deg,#f7fafb 0 50%,#146c84 50%)}}.theme-swatch.dark{{background:linear-gradient(135deg,#171a1f 0 50%,#5fb3c9 50%)}}.theme-swatch.giyu{{background:conic-gradient(#6f3549 0 25%,#d08350 0 50%,#356b5a 0 75%,#dbe8eb 0)}}.theme-swatch.tanjiro{{background:conic-gradient(#43c9e8 0 25%,#43bf91 0 50%,#08192b 0 75%,#d87e8f 0)}}
.about-view{{display:none}}body:has(#view-about:checked) .dashboard-view{{display:none}}body:has(#view-about:checked) .about-view{{display:block}}.about-hero{{display:grid;grid-template-columns:minmax(0,1.08fr) minmax(320px,.92fr);gap:14px;align-items:stretch;margin-top:4px}}.about-copy,.architecture-figure,.about-block{{background:var(--surface);border:1px solid var(--line);border-radius:12px;box-shadow:var(--shadow)}}.about-copy{{padding:30px}}.about-kicker{{margin:0 0 9px;color:var(--marca);font-size:10px;font-weight:720;letter-spacing:.13em;text-transform:uppercase}}.about-copy h2{{display:block;margin:0 0 12px;font-size:27px;line-height:1.1;letter-spacing:-.035em;text-transform:none;color:var(--text)}}.about-copy h2::after{{display:none}}.about-copy p{{max-width:62ch;margin:0;color:var(--text-2);font-size:14px;line-height:1.72}}.about-copy p+p{{margin-top:12px}}.architecture-figure{{margin:0;padding:14px;display:flex;flex-direction:column;justify-content:center;overflow:hidden}}.architecture-trigger{{all:unset;position:relative;display:block;cursor:zoom-in;border-radius:8px;overflow:hidden}}.architecture-trigger:focus-visible{{outline:2px solid var(--series-1);outline-offset:3px}}.architecture-trigger svg{{display:block;width:100%;height:auto;border-radius:8px;transition:transform .35s cubic-bezier(.16,1,.3,1)}}.architecture-trigger:hover svg{{transform:scale(1.018)}}.architecture-trigger svg line,.architecture-trigger svg path[stroke],.diagram-modal-body svg line,.diagram-modal-body svg path[stroke]{{stroke-dasharray:10 14;stroke-dashoffset:0;animation:diagram-flow 1.6s linear infinite}}.architecture-trigger svg line:nth-of-type(2n),.architecture-trigger svg path[stroke]:nth-of-type(2n),.diagram-modal-body svg line:nth-of-type(2n),.diagram-modal-body svg path[stroke]:nth-of-type(2n){{animation-delay:.24s}}.architecture-hint{{position:absolute;right:10px;bottom:10px;padding:4px 7px;border:1px solid rgba(255,255,255,.45);border-radius:5px;background:rgba(18,36,48,.78);color:#fff;font-size:10px;font-weight:680;opacity:0;transform:translateY(4px);transition:opacity .18s,transform .18s}}.architecture-trigger:hover .architecture-hint,.architecture-trigger:focus-visible .architecture-hint{{opacity:1;transform:translateY(0)}}.architecture-figure figcaption{{padding:10px 4px 0;color:var(--muted);font-size:11px;line-height:1.45}}.diagram-modal{{width:min(1240px,94vw);max-height:92dvh;margin:auto;padding:0;border:1px solid var(--line);border-radius:12px;background:var(--surface);color:var(--text);box-shadow:var(--shadow)}}.diagram-modal:popover-open{{display:flex;flex-direction:column;animation:diagram-pop .28s cubic-bezier(.16,1,.3,1)}}.diagram-modal::backdrop{{background:rgba(9,18,25,.62);backdrop-filter:blur(3px)}}.diagram-modal-head{{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px 18px;border-bottom:1px solid var(--line)}}.diagram-modal-head strong{{font-size:14px}}.diagram-close{{all:unset;cursor:pointer;padding:5px 8px;border:1px solid var(--line);border-radius:6px;color:var(--text-2);font-size:12px;font-weight:650}}.diagram-close:hover{{background:var(--acao-hover);color:var(--text)}}.diagram-close:focus-visible{{outline:2px solid var(--series-1);outline-offset:2px}}.diagram-modal-body{{padding:14px;overflow:auto}}.diagram-modal-body svg{{display:block;width:100%;height:auto;min-width:760px;border-radius:8px}}@keyframes diagram-flow{{to{{stroke-dashoffset:-96}}}}@keyframes diagram-pop{{from{{opacity:0;transform:scale(.96) translateY(8px)}}to{{opacity:1;transform:scale(1) translateY(0)}}}}.about-grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:14px}}.about-block{{padding:22px}}.about-block h3{{margin:0 0 8px;font-size:14px;letter-spacing:-.01em}}.about-block p{{margin:0;color:var(--text-2);font-size:13px;line-height:1.65}}.about-principles{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 18px;margin:14px 0 0;padding:0;list-style:none;border-top:1px solid var(--line)}}.about-principles li{{padding:13px 0;border-bottom:1px solid var(--line);font-size:12.5px;color:var(--text-2);line-height:1.5}}.about-principles strong{{display:block;margin-bottom:2px;color:var(--text);font-size:12.5px}}.about-cycle{{margin-top:14px;padding:24px 26px;background:var(--surface);border:1px solid var(--line);border-radius:12px;box-shadow:var(--shadow)}}.about-cycle h3{{margin:0 0 13px;font-size:14px}}.cycle-steps{{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px;margin:0;padding:0;list-style:none;counter-reset:cycle}}.cycle-steps li{{position:relative;padding:12px 10px 12px 32px;border-top:2px solid var(--series-1);color:var(--text-2);font-size:12px;line-height:1.45;counter-increment:cycle}}.cycle-steps li::before{{content:counter(cycle,decimal-leading-zero);position:absolute;left:0;top:10px;color:var(--marca);font-size:10px;font-weight:740;letter-spacing:.06em}}
.command-bar{{display:flex;justify-content:space-between;gap:24px;align-items:center;padding:17px 20px 17px 22px;margin-bottom:14px;border:1px solid var(--alerta-borda);border-left:3px solid var(--st-critical);border-radius:10px;background:var(--alerta-fundo);box-shadow:var(--shadow)}}.command-bar.healthy{{border-color:var(--ok-borda);border-left-color:var(--st-good);background:var(--ok-fundo)}}
.command-copy{{display:grid;gap:2px}}.eyebrow,.tile-k{{font-size:10px;letter-spacing:.1em;font-weight:700;text-transform:uppercase}}.eyebrow{{color:var(--st-critical)}}.command-bar.healthy .eyebrow{{color:var(--st-good)}}.command-copy strong{{font-size:14px;letter-spacing:-.01em}}.command-copy>span:last-child{{font-size:12px;color:var(--text-2)}}.command-actions{{display:flex;gap:14px;align-items:center;white-space:nowrap}}.risk-badge{{display:inline-flex;align-items:center;gap:6px;color:var(--alerta-texto);font-size:12px;font-weight:650}}.risk-badge i{{width:7px;height:7px;border-radius:50%;background:var(--st-critical)}}.risk-badge.healthy{{color:var(--st-good)}}.risk-badge.healthy i{{background:var(--st-good)}}.action-link{{border:1px solid var(--line-forte);border-radius:7px;padding:7px 10px;color:var(--marca);text-decoration:none;font-size:12px;font-weight:650;transition:background .18s,transform .18s}}.action-link:hover{{background:var(--acao-hover);transform:translateY(-1px)}}
.tiles{{grid-template-columns:1.35fr 1fr 1fr 1fr;gap:12px;margin-bottom:16px}}.tile{{min-height:110px;padding:16px 18px;border-radius:10px;box-shadow:none;justify-content:center}}.tile::before{{height:3px}}.tile-v{{font-size:31px;color:var(--text)}}.tile-s{{font-size:12px}}.tile.bad{{background:var(--tile-ruim);border-color:var(--tile-ruim-b)}}
.grid{{grid-template-columns:repeat(12,minmax(0,1fr));gap:14px;align-items:stretch}}.card{{padding:18px 20px;border-radius:11px;box-shadow:var(--shadow)}}.card.wide{{grid-column:span 12}}.card:nth-of-type(2){{grid-column:span 5}}.card:nth-of-type(3){{grid-column:span 4}}.card:nth-of-type(4){{grid-column:span 3}}.card:nth-of-type(5){{grid-column:span 5}}.card:nth-of-type(6){{grid-column:span 3}}.card:nth-of-type(7){{grid-column:span 4}}.card:nth-of-type(8),.card:nth-of-type(9){{grid-column:span 6}}
h2{{font-size:10px;margin-bottom:7px;letter-spacing:.12em}}.sub{{font-size:12px;margin-bottom:12px}}.hero-n{{font-size:46px}}.hero-u{{font-size:18px}}.hero-l{{font-size:11px}}.kv{{margin-top:12px;gap:9px 16px}}.kv dt{{font-size:10px}}.kv dd{{font-size:13px}}.sep{{margin:15px 0}}.nota{{font-size:11px;margin-top:12px}}.guards{{gap:7px}}.guard{{padding:9px 12px 9px 14px;border-radius:8px}}.guard-n{{font-size:13px}}.guard-d,.guard-c,.achados{{font-size:11px}}.fin{{grid-template-columns:74px 1fr auto;margin:9px 0}}.fin-l,.fin-v{{font-size:11px}}.stats{{gap:10px;margin-bottom:14px}}.s-v{{font-size:25px}}.s-k{{font-size:9.5px}}.btns{{grid-template-columns:1fr;gap:6px;margin-bottom:14px}}.btn{{padding:8px 10px}}.btn-t{{font-size:12px}}.btn-d{{font-size:10.5px}}.hbar{{grid-template-columns:minmax(72px,118px) 1fr 36px;gap:8px;margin:6px 0}}.hbar-label,.hbar-val{{font-size:11px}}.svg-area{{height:128px;margin-top:8px}}.eixo{{font-size:10px}}.ritmo{{max-width:400px;margin-top:7px}}.cel{{min-height:7px}}.ses{{padding:6px 0}}.tbl{{font-size:12px}}
@media (max-width:960px){{.wrap{{padding:22px 20px 48px}}.grid{{grid-template-columns:repeat(2,minmax(0,1fr))}}.card.wide,.card:nth-of-type(n){{grid-column:span 1}}.card.wide{{grid-column:1/-1}}.tiles{{grid-template-columns:repeat(2,1fr)}}.card:nth-of-type(2),.card:nth-of-type(5),.card:nth-of-type(9){{grid-column:1/-1}}}}
@media (max-width:960px){{.about-hero{{grid-template-columns:1fr}}.architecture-figure{{max-width:780px}}.cycle-steps{{grid-template-columns:repeat(3,1fr)}}}}
@media (prefers-reduced-motion:reduce){{.architecture-trigger svg,.architecture-trigger svg line,.architecture-trigger svg path[stroke],.diagram-modal:popover-open{{animation:none;transition:none}}}}
@media (max-width:640px){{body:has(#theme-giyu:checked){{--character-position:right -7rem top 6rem;--character-size:330px auto;--character-opacity:.48}}body:has(#theme-tanjiro:checked){{--character-position:center top 10rem;--character-size:470px auto;--character-opacity:.38}}.wrap{{padding:16px 14px 38px}}header{{align-items:flex-start}}.header-meta{{font-size:10.5px}}.header-tools{{width:100%;justify-content:space-between}}.view-tab{{padding:0 7px;font-size:10.5px}}.command-bar{{align-items:flex-start;flex-direction:column;gap:10px;padding:14px}}.command-actions{{width:100%;justify-content:space-between}}.tiles,.grid,.about-grid,.about-principles{{grid-template-columns:1fr}}.card.wide,.card:nth-of-type(n){{grid-column:1}}.tile{{min-height:96px}}.brand-lockup p{{font-size:10.5px}}.about-copy,.about-block,.about-cycle{{padding:19px}}.about-copy h2{{font-size:23px}}.cycle-steps{{grid-template-columns:1fr 1fr}}}}
/* Leitura e navegacao: dimensoes seguem o conteudo, sem depender da ordem dos cards. */
html{{scroll-behavior:smooth;scroll-padding-top:96px}}
.wrap{{max-width:1320px;padding:32px 28px 64px}}
h1{{font-size:clamp(20px,2.4vw,28px);overflow-wrap:anywhere}}
h2{{font-size:16px;font-weight:650;letter-spacing:-.02em;text-transform:none;margin-bottom:10px;color:var(--text)}}
.card>h2::after{{display:none}}
.card{{min-width:0;padding:24px;border-radius:12px}}
.grid>.card{{grid-column:span 6;align-self:start}}
.grid>.wide{{grid-column:1/-1}}
.grid>.layout-sprint{{grid-column:span 7}}
.grid>.layout-guards{{grid-column:span 5}}
.tiles{{grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}}
.tile{{min-width:0;padding:20px;min-height:126px}}
.tile-k{{text-transform:none;letter-spacing:0;font-size:12px;color:var(--text-2)}}
.tile-s{{font-size:12px;line-height:1.5;overflow-wrap:anywhere}}
.tile-v,.hero-n{{font-variant-numeric:tabular-nums}}
.sub,.nota,.snapshot-note{{color:var(--text-2);line-height:1.6}}
.header-meta .live-dot{{background:var(--muted);box-shadow:none}}
.sub{{font-size:13px;margin-bottom:16px}}
.snapshot-note{{font-size:12px;margin:12px 2px 20px;max-width:75ch}}
.section-nav{{position:sticky;top:12px;z-index:3;display:flex;flex-wrap:wrap;gap:4px;padding:6px;border:1px solid var(--line);border-radius:10px;background:var(--surface);box-shadow:var(--shadow)}}
.section-nav a{{display:inline-flex;gap:7px;align-items:center;justify-content:center;min-height:40px;padding:8px 12px;border-radius:6px;font-size:12px;font-weight:600;color:var(--text-2);text-decoration:none;transition:background .18s,color .18s}}
.section-nav a:hover,.section-nav a[aria-current]{{background:var(--acao-hover);color:var(--marca)}}
.section-nav a span,.section-count{{font-size:11px;font-weight:600;font-variant-numeric:tabular-nums;background:var(--muted-fill);color:var(--text-2);border-radius:4px;padding:1px 6px}}
.section-count{{margin-left:10px}}
.priority-list{{display:grid;grid-template-columns:1fr 1fr;gap:0 24px;list-style:none;margin:0;padding:0}}
.priority-list li{{border-top:1px solid var(--line)}}
.priority-list a{{display:grid;grid-template-columns:24px minmax(0,1fr) 16px;gap:12px;padding:16px 2px;color:var(--text);text-decoration:none;border-radius:4px;transition:background .18s}}
.priority-list a:hover{{background:var(--acao-hover)}}
.priority-list strong{{display:block;font-size:13px;font-weight:650;overflow-wrap:anywhere}}
.priority-index{{font:11px/1.8 ui-monospace,monospace;color:var(--marca)}}
.priority-detail{{display:block;font-size:12px;line-height:1.55;color:var(--text-2);margin-top:3px;overflow-wrap:anywhere}}
.priority-arrow{{color:var(--marca);font-size:16px}}
.command-copy strong{{font-size:20px;line-height:1.35}}
.command-copy>span:last-child{{max-width:64ch;margin-top:4px;font-size:13px}}
.command-bar.neutral{{border-color:var(--line);border-left-color:var(--marca);background:var(--surface)}}
.command-bar.neutral .eyebrow,.risk-badge.neutral{{color:var(--text-2)}}
.risk-badge.neutral i{{background:var(--muted)}}
.sprint-title{{font-size:19px;font-weight:600;line-height:1.4;letter-spacing:-.02em;margin:0 0 22px}}
.next-step{{margin-top:22px;padding-top:16px;border-top:1px solid var(--line)}}
.next-step>span{{font-size:12px;color:var(--text-2)}}
.next-step p{{margin:4px 0 0;font-size:14px;overflow-wrap:anywhere}}
.section-details summary{{cursor:pointer;min-height:44px;padding:10px 0;color:var(--marca);font-size:13px;font-weight:600}}
.section-details[open] summary{{margin-bottom:12px}}
.doc-card-head{{flex-wrap:wrap}}
.kv dd,.guard-c,.achados,.vazio,.mono{{overflow-wrap:anywhere}}
.grow{{min-width:min(230px,100%)}}
.tbl-scroll{{max-width:100%}}
.tbl td:nth-child(2){{min-width:180px;max-width:36ch;white-space:normal;overflow-wrap:anywhere}}
.help{{position:relative;width:24px;height:24px;font-size:12px;flex:none}}
.help::after{{content:"";position:absolute;inset:-5px}}
.help-sm{{width:22px;height:22px}}
.update-banner{{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:16px 20px;border-radius:10px;border:1px solid var(--line);background:var(--surface);margin-bottom:16px}}
.update-banner.ok{{border-color:var(--ok-borda);border-left:3px solid var(--st-good);background:var(--ok-fundo)}}
.update-banner.alerta{{border-color:var(--alerta-borda);border-left:3px solid var(--st-warning);background:var(--alerta-fundo)}}
.update-banner h3{{margin:4px 0 2px;font-size:16px;font-weight:650;color:var(--text)}}
.update-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin-bottom:16px}}
.update-item{{padding:14px;border:1px solid var(--line);border-radius:9px;background:var(--surface)}}
.update-item-head{{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}}
.update-item-head strong{{font-size:13px;color:var(--text)}}
.update-badge{{font-size:10.5px;font-weight:700;padding:2px 7px;border-radius:4px;text-transform:uppercase;letter-spacing:.04em}}
.update-badge.ok{{background:color-mix(in srgb,var(--st-good) 15%,transparent);color:var(--st-good)}}
.update-badge.pendente{{background:color-mix(in srgb,var(--st-warning) 20%,transparent);color:var(--st-serious)}}
.update-badge.ausente{{background:var(--muted-fill);color:var(--muted)}}
.update-item p{{margin:0;font-size:12px;color:var(--text-2);line-height:1.5}}
.update-box{{padding:18px 20px;border:1px solid var(--line);border-radius:10px;background:var(--surface);margin-top:14px}}
.update-box-head{{margin-bottom:8px}}
.update-box-head strong{{font-size:14px;color:var(--text)}}
.update-steps{{display:grid;gap:12px;margin:12px 0 0;padding:0;list-style:none}}
.update-steps li{{display:grid;grid-template-columns:28px minmax(0,1fr);gap:12px;align-items:start}}
.update-step-num{{display:grid;place-items:center;width:24px;height:24px;border-radius:50%;background:var(--marca);color:var(--marca-t);font-size:11px;font-weight:700}}
.update-step-body strong{{display:block;font-size:13px;color:var(--text);margin-bottom:2px}}
.update-step-body p{{margin:0 0 6px;font-size:12px;color:var(--text-2);line-height:1.5}}
.update-step-body code{{display:inline-block;padding:3px 8px;font-size:12px;background:var(--muted-fill);color:var(--text);border-radius:5px}}
.update-pendencias{{padding:14px 18px;border:1px solid var(--alerta-borda);border-radius:9px;background:var(--alerta-fundo);margin-bottom:14px}}
.update-pendencias strong{{font-size:13px;color:var(--text)}}
.update-pendencias-list{{margin:8px 0 0;padding-left:18px;font-size:12.5px;color:var(--text-2);line-height:1.6}}
/* Skills Operacionais (mattpocock/skills) */
.skills-flow-map{{display:grid;grid-template-columns:1.25fr 1fr 1fr;gap:14px;margin-bottom:18px}}
.flow-col{{border:1px solid var(--line);border-radius:11px;padding:18px;background:color-mix(in srgb,var(--surface) 94%,var(--bg));display:flex;flex-direction:column;gap:12px}}
.flow-col-main{{border-top:3px solid var(--marca);background:var(--surface)}}
.flow-col-head .eyebrow{{font-size:10px;letter-spacing:.08em;font-weight:740;text-transform:uppercase;color:var(--marca)}}
.flow-col-head h4{{margin:2px 0 4px;font-size:15px;font-weight:680;color:var(--text)}}
.flow-col-head p{{margin:0;font-size:12px;color:var(--text-2);line-height:1.5}}
.flow-pipeline{{list-style:none;margin:0;padding:0;display:grid;gap:8px}}
.flow-pipeline li{{display:grid;grid-template-columns:28px minmax(0,1fr);gap:10px;align-items:start;padding:8px 10px;border:1px solid var(--line);border-radius:8px;background:color-mix(in srgb,var(--bg) 60%,var(--surface))}}
.flow-num{{display:grid;place-items:center;width:24px;height:24px;border-radius:6px;background:var(--marca);color:var(--marca-t);font:700 10.5px/1 ui-monospace,monospace}}
.flow-pipeline strong{{display:block;font-size:12.5px;color:var(--text);margin-bottom:2px}}
.flow-pipeline p{{margin:0;font-size:11.5px;color:var(--text-2);line-height:1.45}}
.flow-cards-stack{{display:grid;gap:9px}}
.flow-mini-card{{padding:10px 12px;border:1px solid var(--line);border-radius:8px;background:var(--surface)}}
.flow-mini-card.highlight{{border-left:3px solid var(--series-1)}}
.flow-mini-top{{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:4px;flex-wrap:wrap}}
.flow-mini-top strong{{font-size:12.5px;color:var(--text)}}
.flow-mini-card p{{margin:0;font-size:11.5px;color:var(--text-2);line-height:1.45}}
.flow-boundary-box{{padding:12px;border:1px dashed var(--line-forte);border-radius:8px;background:color-mix(in srgb,var(--muted-fill) 45%,var(--surface))}}
.flow-boundary-box>strong{{display:block;font-size:12.5px;color:var(--text);margin-bottom:3px}}
.flow-boundary-box>p{{margin:0 0 8px;font-size:11.5px;color:var(--text-2);line-height:1.45}}
.boundary-pills{{display:flex;flex-wrap:wrap;gap:5px}}
.boundary-pill{{font-size:11px;padding:3px 8px;border-radius:5px;border:1px solid var(--line);background:var(--surface);color:var(--text-2)}}
.boundary-pill strong{{color:var(--marca)}}
.skills-nav-filter{{display:flex;flex-wrap:wrap;gap:6px;margin:14px 0 18px;padding:0;border:none;align-items:center}}
.skills-nav-filter input{{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}}
.skills-filter-tab{{display:inline-flex;align-items:center;gap:6px;padding:7px 14px;border:1px solid var(--line);border-radius:20px;font-size:12px;font-weight:620;color:var(--text-2);cursor:pointer;background:var(--surface);transition:background .18s,color .18s,border-color .18s}}
.skills-filter-tab:hover{{background:var(--acao-hover);color:var(--text)}}
.skills-nav-filter input:checked + .skills-filter-tab{{background:var(--marca);color:var(--marca-t);border-color:var(--marca)}}
.skills-nav-filter input:focus-visible + .skills-filter-tab{{outline:2px solid var(--series-1);outline-offset:2px}}
.skills-groups{{display:grid;gap:20px}}
.skill-group{{background:var(--surface);border:1px solid var(--line);border-radius:11px;padding:20px;box-shadow:var(--shadow)}}
.skill-group-head{{display:flex;justify-content:space-between;align-items:flex-start;gap:14px;flex-wrap:wrap;margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid var(--line)}}
.skill-group-title{{display:flex;align-items:center;gap:10px}}
.skill-group-badge{{display:grid;place-items:center;width:28px;height:28px;border-radius:50%;background:var(--marca);color:var(--marca-t);font-size:12px;font-weight:750}}
.skill-group-head h3{{margin:0;font-size:16px;font-weight:680;color:var(--text);letter-spacing:-.015em}}
.skill-group-desc{{margin:4px 0 0;font-size:12.5px;color:var(--text-2)}}
.skills-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px}}
.skill-card{{border:1px solid var(--line);border-radius:10px;padding:15px;background:color-mix(in srgb,var(--surface) 92%,var(--bg));display:flex;flex-direction:column;justify-content:space-between;gap:12px;transition:border-color .18s,transform .18s,box-shadow .18s}}
.skill-card.sc-main-flow{{border-top:2px solid var(--marca)}}
.skill-card:hover{{border-color:var(--line-forte);transform:translateY(-1px);box-shadow:var(--shadow)}}
.skill-card-top{{display:grid;gap:8px}}
.skill-card-head{{display:flex;justify-content:space-between;align-items:flex-start;gap:8px}}
.skill-title-row{{display:flex;align-items:center;gap:6px;flex-wrap:wrap}}
.skill-card-head strong{{font-size:14px;color:var(--text);font-weight:670}}
.skill-guide-count{{font-size:10px;font-weight:650;padding:1px 6px;border-radius:999px;background:var(--muted-fill);color:var(--text-2)}}
.skill-badges-row{{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-top:4px}}
.skill-cmd{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px;padding:2px 6px;border-radius:4px;background:var(--muted-fill);color:var(--marca);font-weight:650}}
.skill-role-badge{{font-size:10px;font-weight:680;padding:2px 7px;border-radius:4px;border:1px solid var(--line);color:var(--text-2);background:var(--surface)}}
.skill-role-badge.main{{border-color:color-mix(in srgb,var(--marca) 40%,var(--line));color:var(--marca);background:color-mix(in srgb,var(--marca) 10%,var(--surface))}}
.skill-desc{{margin:0;font-size:12px;line-height:1.55;color:var(--text-2)}}
.skill-meta{{display:grid;gap:8px;font-size:11.5px;padding-top:10px;border-top:1px dashed var(--line);color:var(--muted);line-height:1.45}}
.skill-row strong{{color:var(--text-2);font-weight:620}}
.skill-io-grid{{display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:7px 9px;border-radius:7px;background:var(--surface);border:1px solid var(--line)}}
.skill-io-cell{{display:flex;flex-direction:column;gap:2px;min-width:0}}
.skill-io-cell span{{font-size:9.5px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);font-weight:700}}
.skill-io-cell strong{{font-size:11px;color:var(--text);font-weight:560;line-height:1.35;overflow-wrap:anywhere}}
.skill-soberania{{color:var(--marca);font-size:11px;line-height:1.42}}
.skill-card-foot{{display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;padding-top:4px}}
.skill-chip-row{{display:flex;flex-wrap:wrap;gap:4px}}
.skill-chip{{font-size:10.5px;padding:2px 6px;border-radius:4px;background:var(--muted-fill);color:var(--text-2)}}
.skill-chip.guide{{color:var(--marca)}}
.skill-detail-btn{{all:unset;cursor:pointer;font-size:11.5px;font-weight:660;color:var(--marca);padding:4px 9px;border:1px solid var(--line-forte);border-radius:6px;background:var(--surface);transition:background .15s,border-color .15s}}
.skill-detail-btn:hover{{background:var(--acao-hover);border-color:var(--marca)}}
.skill-detail-btn:focus-visible{{outline:2px solid var(--series-1);outline-offset:2px}}
.skill-pop-body{{display:grid;gap:16px}}
.skill-pop-top{{display:flex;flex-wrap:wrap;gap:8px;align-items:center}}
.skill-path-tag code{{font-size:11px;color:var(--text-2)}}
.skill-pop-desc{{margin:0;font-size:13.5px;line-height:1.6;color:var(--text)}}
.skill-pop-io{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px}}
.skill-io-box{{padding:12px;border:1px solid var(--line);border-radius:8px;background:var(--bg)}}
.skill-io-box .eyebrow{{color:var(--marca);display:block;margin-bottom:4px}}
.skill-io-box p{{margin:0;font-size:12.5px;color:var(--text-2);line-height:1.5}}
.skill-pop-section h4{{margin:0 0 8px;font-size:13px;font-weight:670;color:var(--text)}}
.skill-steps-list{{list-style:none;margin:0;padding:0;display:grid;gap:8px}}
.skill-steps-list li{{display:grid;grid-template-columns:26px minmax(0,1fr);gap:10px;align-items:start;padding:10px 12px;border:1px solid var(--line);border-radius:8px;background:var(--bg);font-size:12.5px;color:var(--text-2);line-height:1.5}}
.skill-step-idx{{display:grid;place-items:center;width:22px;height:22px;border-radius:50%;background:var(--marca);color:var(--marca-t);font-size:11px;font-weight:700}}
.skill-pop-dual{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
.skill-pop-sovereignty{{padding:12px 14px;border-left:3px solid var(--marca);border-radius:6px;background:color-mix(in srgb,var(--marca) 8%,var(--surface));font-size:12.5px;color:var(--text);line-height:1.5}}
body:has(#sf-fluxo:checked) .skill-card:not(.sc-main-flow){{display:none}}
body:has(#sf-descoberta:checked) .skill-group:not(.sg-descoberta){{display:none}}
body:has(#sf-modelagem:checked) .skill-group:not(.sg-modelagem){{display:none}}
body:has(#sf-implementacao:checked) .skill-group:not(.sg-implementacao){{display:none}}
body:has(#sf-revisao:checked) .skill-group:not(.sg-revisao){{display:none}}
/* Raio-X do Projeto */
.project-stats-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px;margin-bottom:16px}}
.project-stat-box{{padding:18px;border:1px solid var(--line);border-radius:10px;background:var(--surface);display:flex;flex-direction:column;gap:6px}}
.project-stat-box .eyebrow{{font-size:10px;letter-spacing:.08em;font-weight:720;text-transform:uppercase;color:var(--marca)}}
.project-stat-box h4{{margin:0;font-size:15px;font-weight:660;color:var(--text)}}
.project-stat-box p{{margin:0;font-size:12px;color:var(--text-2);line-height:1.55}}
.project-tools-list{{display:flex;flex-wrap:wrap;gap:6px;margin-top:auto;padding-top:8px}}
.tool-chip{{display:inline-flex;align-items:center;gap:5px;padding:3px 9px;border:1px solid var(--line);border-radius:6px;background:var(--muted-fill);font-size:11px;font-weight:600;color:var(--text)}}
.tool-chip i{{width:6px;height:6px;border-radius:50%;background:var(--st-good)}}
.project-dual-grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
.project-subpanel{{border:1px solid var(--line);border-radius:10px;padding:18px;background:var(--surface)}}
.project-subpanel-head{{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap;padding-bottom:12px;margin-bottom:10px;border-bottom:1px solid var(--line)}}
.project-subpanel-head .eyebrow{{font-size:10px;letter-spacing:.08em;font-weight:720;text-transform:uppercase;color:var(--marca)}}
.project-subpanel-head h4{{margin:2px 0 0;font-size:14.5px;font-weight:670;color:var(--text)}}
.inv-list{{display:grid;gap:6px}}
.inv-row{{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:8px 10px;border:1px solid var(--line);border-radius:8px;background:color-mix(in srgb,var(--bg) 55%,var(--surface));flex-wrap:wrap}}
.inv-main{{display:flex;align-items:center;gap:8px;flex-wrap:wrap;min-width:0}}
.inv-main strong{{font-size:12.5px;color:var(--text)}}
.inv-main code{{font-size:11px;color:var(--marca)}}
.inv-role{{font-size:11.5px;color:var(--text-2)}}
.inv-side{{display:flex;align-items:center;gap:8px;margin-left:auto}}
.inv-guard{{font:11px/1.3 ui-monospace,monospace;color:var(--muted)}}
.adr-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:10px}}
.adr-card{{padding:12px;border:1px solid var(--line);border-radius:8px;background:color-mix(in srgb,var(--bg) 55%,var(--surface));display:flex;flex-direction:column;gap:5px}}
.adr-card-top{{display:flex;justify-content:space-between;align-items:center;gap:8px}}
.adr-num{{font-weight:700;color:var(--marca);font-size:11px}}
.adr-card strong{{font-size:12.5px;color:var(--text);line-height:1.4}}
.adr-meta{{font-size:11px;color:var(--muted)}}
.section-nav{{backdrop-filter:blur(10px);background:color-mix(in srgb,var(--surface) 90%,transparent)}}
.view-tab,.theme-option,.action-link,.doc-example-trigger,.pop-x,.diagram-close{{min-height:40px}}
.theme-option{{width:40px}}
.pop-x{{display:inline-flex;align-items:center;justify-content:center;min-width:40px}}
.skip-link{{position:absolute;left:16px;top:12px;z-index:5;transform:translateY(-180%);background:var(--surface);color:var(--marca);padding:12px 16px;border:1px solid var(--marca);border-radius:6px}}
.skip-link:focus{{transform:none}}
a:focus-visible,button:focus-visible,summary:focus-visible,[tabindex]:focus-visible{{outline:2px solid var(--marca);outline-offset:4px}}
@media(max-width:960px){{.wrap{{padding:24px 20px 48px}}.grid{{grid-template-columns:repeat(2,minmax(0,1fr))}}.grid>.card{{grid-column:span 1}}.grid>.wide,.grid>.layout-sprint,.grid>.layout-guards{{grid-column:1/-1}}.tiles{{grid-template-columns:repeat(2,minmax(0,1fr))}}.skills-flow-map,.project-dual-grid,.skill-pop-dual{{grid-template-columns:1fr}}}}
@media(max-width:640px){{html{{scroll-padding-top:24px}}.wrap{{padding:18px 12px 40px}}header{{gap:16px}}.header-tools{{gap:10px;justify-content:flex-start;flex-wrap:wrap}}.header-meta{{width:100%}}.section-nav{{position:static;flex-wrap:nowrap;overflow-x:auto;max-width:100%;scrollbar-width:thin}}.section-nav a{{flex:none;min-height:44px}}.grid{{grid-template-columns:minmax(0,1fr);gap:16px}}.grid>.card,.grid>.wide{{grid-column:1/-1}}.card{{padding:20px 16px}}.priority-list{{grid-template-columns:1fr}}.tiles{{gap:10px}}.tile{{padding:16px 12px;min-height:120px}}.tile-v{{font-size:28px}}.tile-s{{font-size:11px}}.command-copy strong{{font-size:18px}}.command-actions{{flex-wrap:wrap;gap:10px;white-space:normal}}.fin{{grid-template-columns:70px minmax(0,1fr)}}.fin-v{{grid-column:1/-1;text-align:right}}.kv{{grid-template-columns:repeat(2,minmax(0,1fr))}}.view-tab,.theme-option,.action-link,.doc-example-trigger,.diagram-close{{min-height:44px}}.row{{gap:20px}}.ses{{grid-template-columns:minmax(0,1fr) auto}}.ses-v{{grid-column:2}}.ses-n{{overflow-wrap:anywhere}}.skill-io-grid{{grid-template-columns:1fr}}}}
@media(max-width:360px){{.tiles{{grid-template-columns:1fr}}.kv{{grid-template-columns:1fr}}}}
@media(max-width:640px){{.theme-option{{width:44px}}.help::after{{inset:-10px}}}}
@media(prefers-reduced-motion:reduce){{html{{scroll-behavior:auto}}*,*::before,*::after{{animation:none!important;transition:none!important}}}}
</style>
</head>
<body>
<a class="skip-link" href="#painel">Ir para o painel</a>
<div class="wrap">
<header>
  <div class="brand-lockup"><span class="brand-mark" aria-hidden="true">NF</span><div><h1>{projeto} <span>· Neural-Flow</span></h1><p>Visão de execução, risco e governança do projeto</p></div></div>
  <div class="header-tools"><fieldset class="view-tabs"><legend>Seção do dashboard</legend><input type="radio" name="view" id="view-dashboard" checked><label class="view-tab" for="view-dashboard">Painel</label><input type="radio" name="view" id="view-about"><label class="view-tab" for="view-about">O Neural-Flow</label></fieldset>{idioma_controle}<fieldset class="theme-picker"><legend>Escolha a paleta do dashboard</legend><input type="radio" name="theme" id="theme-light" checked><label class="theme-option" for="theme-light" aria-label="Tema claro"><span class="theme-swatch light" aria-hidden="true"></span></label><input type="radio" name="theme" id="theme-dark"><label class="theme-option" for="theme-dark" aria-label="Tema escuro"><span class="theme-swatch dark" aria-hidden="true"></span></label><input type="radio" name="theme" id="theme-giyu"><label class="theme-option" for="theme-giyu" aria-label="Tema Giyu: vinho, verde e azul-neblina"><span class="theme-swatch giyu" aria-hidden="true"></span></label><input type="radio" name="theme" id="theme-tanjiro"><label class="theme-option" for="theme-tanjiro" aria-label="Tema Tanjiro: água, verde e azul-noturno"><span class="theme-swatch tanjiro" aria-hidden="true"></span></label></fieldset><div class="header-meta"><span class="live-dot" aria-hidden="true"></span><span>Atualizado em {gerado_legivel}</span></div></div>
</header>

<main class="dashboard-view" id="painel" tabindex="-1">
<section class="command-bar {resumo_tipo}" id="resumo" aria-label="Resumo executivo">
  <div class="command-copy"><span class="eyebrow">Resumo executivo</span><strong>{resumo_status}</strong><span>{resumo_detalhe}</span></div>
  <div class="command-actions"><span class="risk-badge {resumo_tipo}"><i aria-hidden="true"></i> {resumo_rotulo}</span><a href="#prioridades" class="action-link">Ver pendencias <span aria-hidden="true">→</span></a></div>
</section>

<div class="tiles">{tiles}</div>

<nav class="section-nav" aria-label="Navegacao do painel">
  <a href="#resumo">Resumo</a><a href="#prioridades">Pendencias <span>{total_prioridades}</span></a><a href="#sprint">Sprint</a><a href="#guards">Controles</a><a href="#skills">Skills <span>27</span></a><a href="#ficha-projeto">Projeto</a><a href="#atualizacoes">Atualizacoes</a><a href="#documentos-produto">Documentos</a><a href="#finops">Tokens</a><a href="#grafo">Conhecimento</a><a href="#historico">Historico</a>
</nav>
<p class="snapshot-note">Retrato local gerado em {gerado_legivel}. Os dados mudam quando o painel e gerado novamente.</p>

<div class="grid">
  <section class="card wide priority-card" id="prioridades"><h2>O que precisa de atencao <span class="section-count">{total_prioridades}</span></h2>
    <p class="sub">Sinais dos artefatos para orientar a proxima revisao</p>{prioridades}</section>
  <section class="card layout-sprint" id="sprint"><h2>Sprint ativa{ajuda_sprint}</h2>{sprint}</section>
  <section class="card layout-guards" id="guards"><h2>Guards{ajuda_guards}</h2>
    <p class="sub">Verificados ao gerar este retrato, sobre a arvore de trabalho</p>{guards}</section>
  <section class="card wide" id="skills"><h2>Arsenal de Skills Operacionais (27){ajuda_skills}</h2>
    <p class="sub">Metodos taticos de engenharia (mattpocock/skills) integrados e prontos para invocacao autonoma em 4 fases</p>{skills_secao}</section>
  <section class="card wide" id="ficha-projeto"><h2>Raio-X e Governanca do Projeto{ajuda_projeto}</h2>
    <p class="sub">Arquitetura de supervisao, matriz de autonomia e integridade dos artefatos</p>{ficha_projeto}</section>
  <section class="card wide" id="atualizacoes"><h2>Atualizacoes e Versao{ajuda_atualizacoes}</h2>
    <p class="sub">Integridade das capacidades instaladas e instrucoes de atualizacao</p>{atualizacoes}</section>
  <section class="card wide" id="documentos-produto"><h2>Documentos do projeto</h2>
    <p class="sub">Diagnostico, lacunas e modelos de referencia para a versao do produto</p>
    <details class="section-details"><summary>Ver documentos e modelos <span class="section-count">{total_documentos}</span></summary>{documentos_produto}</details></section>
  <section class="card" id="finops"><h2>FinOps de tokens{ajuda_finops}</h2>
    <p class="sub">Orcamento declarado x consumo observado</p>{finops}</section>
  <section class="card" id="tokens"><h2>Consumo real de tokens{ajuda_tokens}</h2>
    <p class="sub">Medido nos transcripts locais, nao declarado</p>{tokens}</section>
  <section class="card" id="ritmo"><h2>Ritmo e ferramentas{ajuda_ritmo}</h2>
    <p class="sub">Como o trabalho se distribuiu</p>{ritmo}</section>
  <section class="card" id="smoke"><h2>smoke-gate{ajuda_smoke}</h2>
    <p class="sub">Gate de evidencia sobre codigo e schema</p>{smoke}</section>
  <section class="card" id="grafo"><h2>Indice de conhecimento{ajuda_grafo}</h2>
    <p class="sub">Grafo construido sobre a documentacao</p>{grafo}</section>
  <section class="card" id="loop"><h2>Loop autonomo{ajuda_loop}</h2>
    <p class="sub">Estado em disco, nao na conversa</p>{loop}</section>
  <section class="card wide" id="protocolos"><h2>Protocolos{ajuda_protocolos}</h2>
    <p class="sub">O que trava e o que se audita</p>{protocolos}</section>
{historico}
</div>
</main>

<main class="about-view" aria-label="Sobre o Neural-Flow Framework">
  <section class="about-hero"><div class="about-copy"><p class="about-kicker">Método de engenharia assistida por IA</p><h2>Transformar intenção em mudança verificável.</h2><p>Neural-Flow é um framework de governança para trabalho técnico executado por pessoas e agentes. Ele organiza a execução em artefatos legíveis, regras verificáveis e evidências reproduzíveis, para que velocidade não dependa de confiança cega.</p><p>O objetivo é simples: cada mudança deve ter escopo, contexto, decisão e prova. Assim, o projeto permanece compreensível quando a conversa acaba, o agente muda ou a equipe cresce.</p></div><figure class="architecture-figure"><button type="button" class="architecture-trigger" popovertarget="diagrama-arquitetura" aria-label="Ampliar diagrama de arquitetura"><span class="architecture-hint" aria-hidden="true">Clique para ampliar</span>{arquitetura}</button><figcaption>Arquitetura do fluxo: os artefatos registram a intenção, os guards bloqueiam desvios e o CI confirma a autoridade do processo.</figcaption></figure></section>
  <section class="about-grid"><article class="about-block"><h3>O que o framework resolve</h3><p>Projetos guiados por IA frequentemente perdem contexto, misturam hipótese com fato e deixam decisões importantes só no chat. Neural-Flow torna o estado do trabalho explícito em disco, reduzindo retrabalho e tornando a retomada confiável.</p><ul class="about-principles"><li><strong>Estado persistente</strong>Plano, diário, divergências e sprint registram o que foi feito e o que falta.</li><li><strong>Decisão rastreável</strong>ADRs preservam o porquê de mudanças arquiteturais sem reescrever o histórico.</li></ul></article><article class="about-block"><h3>Como ele preserva autonomia</h3><p>Autonomia não significa ausência de limites. O framework define até onde um agente pode avançar e quais decisões exigem revisão humana, especialmente em escopos sensíveis ou irreversíveis.</p><ul class="about-principles"><li><strong>Guards executáveis</strong>Regras críticas deixam de ser recomendação e passam a bloquear o commit quando violadas.</li><li><strong>Evidência antes de conclusão</strong>Um item só está pronto quando a verificação foi executada e registrada.</li></ul></article></section>
  <section class="about-cycle"><h3>O ciclo operacional</h3><ol class="cycle-steps"><li>Defina a sprint, o escopo, a autonomia e o orçamento.</li><li>Consulte o índice e registre fontes que sustentam a decisão.</li><li>Implemente uma mudança pequena e deixe o estado no plano.</li><li>Execute os guards; se reprovar, corrija o artefato ou a mudança.</li><li>Registre evidência, faça o commit e deixe o CI validar novamente.</li></ol></section>
</main>

<div popover id="diagrama-arquitetura" class="diagram-modal" role="dialog" aria-label="Diagrama de arquitetura ampliado"><div class="diagram-modal-head"><strong>Como uma mudança vira commit</strong><button type="button" class="diagram-close" popovertarget="diagrama-arquitetura" popovertargetaction="hide">Fechar</button></div><div class="diagram-modal-body">{arquitetura_ampliada}</div></div>

{janelas}
<footer>Neural-Flow Framework — gerado por <code>scripts/nf_dashboard.py</code></footer>
</div>
</body>
</html>
"""


# ── CLI ────────────────────────────────────────────────────────────────────────


def main() -> int:
    ap = argparse.ArgumentParser(description="Dashboard do Neural-Flow (HTML estatico).")
    ap.add_argument("--root", default=".", help="raiz do projeto")
    ap.add_argument("--out", help="arquivo de saida (default: .neural-flow/dashboard.html)")
    ap.add_argument("--name", help="nome do projeto")
    ap.add_argument("--open", action="store_true", help="abre no navegador")
    ap.add_argument("--sem-tema", action="store_true",
                    help="nao embute imagens de tema (saida reproduzivel)")
    ap.add_argument("--dias", type=int, default=30,
                    help="janela da telemetria de tokens (default: 30)")
    ap.add_argument(
        "--transcripts",
        help="diretorio de transcripts a ler (default: o do projeto em ~/.claude). "
             "Usado para gerar saida reproduzivel.",
    )
    ap.add_argument(
        "--gerado-em",
        help="carimbo de geracao fixo (ex: 2026-08-08 12:00). Torna a saida "
             "reproduzivel — usado para versionar a pagina de demonstracao.",
    )
    args = ap.parse_args()

    global SEM_TEMA
    SEM_TEMA = args.sem_tema

    raiz = Path(args.root).resolve()
    destino = Path(args.out).resolve() if args.out else raiz / ".neural-flow" / "dashboard.html"

    dados = coletar(raiz, args.name, args.gerado_em,
                    Path(args.transcripts).resolve() if args.transcripts else None,
                    args.dias)
    destino.parent.mkdir(parents=True, exist_ok=True)
    # Os links apontam para os artefatos reais, entao dependem de onde a pagina
    # e gravada: `.neural-flow/dashboard.html` alcanca `../graphify-out/`.
    #
    # So vale calcular o caminho relativo quando a saida esta DENTRO do projeto
    # analisado. Fora dele, `relpath` sobe ate a raiz do sistema e grava algo
    # como `../../../../Users/<voce>/...` — sem sentido para quem abrir a pagina
    # e carregando o layout da maquina de quem gerou.
    import os as _os

    try:
        destino.parent.relative_to(raiz)
        rel = _os.path.relpath(raiz / "graphify-out", destino.parent)
        rel = rel.replace(_os.sep, "/") + "/"
    except ValueError:
        rel = "graphify-out/"
    destino.write_text(render(dados, rel), encoding="utf-8")

    tam = destino.stat().st_size / 1024
    print(f"dashboard: {destino}  ({tam:.0f} KB)")
    print(f"  sprints: {len(dados.sprints)}  |  ADRs: {dados.adrs['total']}  |  "
          f"guards conforme: {sum(1 for g in dados.guards if g['estado'] == 'pass')}"
          f"/{sum(1 for g in dados.guards if g['estado'] in ('pass', 'fail'))}")
    if args.open:
        import webbrowser
        webbrowser.open(destino.as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())
