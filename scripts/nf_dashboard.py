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

import argparse
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

AQUI = Path(__file__).resolve().parent

GUARDS = [
    ("sprint", "State Protocol", "Sprint validada antes de executar"),
    ("budget", "Circuit Breaker", "Orcamento de tokens declarado"),
    ("context", "Vetor de Contexto", "Decisao ancorada em fonte que existe"),
    ("adr", "ADR Governance", "Decisao numerada, sem ciclo nem pendura"),
    ("spec", "Spec-First", "Spec completa antes do codigo"),
    ("calibration", "Calibracao", "Confianca declarada e derivada de evidencia"),
]

PROTOCOLOS = [
    ("State Protocol", "sprint"), ("Circuit Breaker", "budget"),
    ("Vetor de Contexto", "context"), ("Evidencia Sintetica", "smoke"),
    ("Aegis", None), ("Neural-Memory", None), ("ADR Governance", "adr"),
    ("Spec-First", "spec"), ("Loop Autonomo", None), ("Calibracao", "calibration"),
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

    @property
    def ativa(self) -> Sprint | None:
        for s in self.sprints:
            if s.status == "em andamento":
                return s
        return self.sprints[-1] if self.sprints else None


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
        ))
    saida.sort(key=lambda s: (s.numero.zfill(4), s.arquivo))
    return saida


def coletar_guards(raiz: Path) -> list[dict]:
    arquivo_de = {
        "sprint": "sprint_state", "budget": "token_budget",
        "context": "context_sources", "adr": "adr",
        "spec": "module_spec", "calibration": "calibration",
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


def coletar(raiz: Path, projeto: str | None, gerado_em: str | None = None) -> Dados:
    return Dados(
        projeto=projeto or raiz.name,
        gerado_em=gerado_em or datetime.now().strftime("%Y-%m-%d %H:%M"),
        sprints=coletar_sprints(raiz),
        guards=coletar_guards(raiz),
        adrs=coletar_adrs(raiz),
        grafo=coletar_grafo(raiz),
        smoke=coletar_smoke(raiz),
        loop=coletar_loop(raiz),
    )


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


def barras_horizontais(itens: list[tuple[str, int]], cor: str) -> str:
    """Magnitude por categoria — uma serie, sem legenda (o titulo ja a nomeia)."""
    if not itens:
        return '<p class="vazio">sem dados</p>'
    maior = max(v for _, v in itens) or 1
    linhas = []
    for rotulo, valor in itens:
        pct = valor / maior * 100
        linhas.append(
            f'<div class="hbar"><span class="hbar-label" title="{e(rotulo)}">{e(rotulo)}</span>'
            f'<div class="hbar-track"><div class="hbar-fill" style="width:{pct:.1f}%;'
            f'background:{cor}"></div></div>'
            f'<span class="hbar-val">{valor}</span></div>'
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


def render(d: Dados, rel_grafo: str = "graphify-out/") -> str:
    ativa = d.ativa
    guards_pass = sum(1 for g in d.guards if g["estado"] == "pass")
    guards_fail = sum(1 for g in d.guards if g["estado"] == "fail")
    guards_ativos = sum(1 for g in d.guards if g["estado"] in ("pass", "fail"))

    # ── Tiles de topo ──
    saude = "ok" if guards_fail == 0 else "bad"
    saude_txt = "guards conforme" if guards_fail == 0 else f"{guards_fail} reprovando — corrija antes do commit"
    tiles = [
        ("Governanca", f"{guards_pass}/{guards_ativos}", saude_txt, saude),
        ("Sprint ativa",
         f"#{ativa.numero}" if ativa else "—",
         (ativa.titulo[:46] if ativa else "nenhuma sprint encontrada"),
         "ok" if ativa and ativa.status == "em andamento" else "idle"),
        ("Divergencias",
         str(d.loop.get("divergencias", 0)) if d.loop.get("ativo") else "—",
         "decisoes aguardando revisao humana" if d.loop.get("ativo") else "loop nao iniciado",
         "warn" if d.loop.get("divergencias") else "idle"),
        ("ADRs", str(d.adrs["total"]) if d.adrs["total"] else "—",
         " · ".join(f"{v} {k}" for k, v in sorted(d.adrs["por_status"].items())) or "nenhum registrado",
         "ok" if d.adrs["total"] else "idle"),
    ]
    html_tiles = "".join(
        f'<div class="tile {cls}"><span class="tile-k">{e(k)}</span>'
        f'<span class="tile-v">{e(v)}</span><span class="tile-s">{e(s)}</span></div>'
        for k, v, s, cls in tiles
    )

    # ── Sprint ativa ──
    if ativa:
        restante = ""
        try:
            faltam = (date.fromisoformat(ativa.prazo) - date.today()).days
            restante = f"{faltam} dias restantes" if faltam >= 0 else f"{-faltam} dias em atraso"
        except (ValueError, TypeError):
            restante = "prazo nao definido"
        aut_alerta = ativa.autonomia.upper() in ("A2", "A3")
        corpo_sprint = f"""
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
        </div>"""
    else:
        corpo_sprint = ('<p class="vazio">Nenhuma sprint encontrada em <code>docs/sprints/</code>. '
                        'O State Protocol exige uma sprint validada antes de qualquer execucao.</p>')

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
        linhas_p.append(
            f'<div class="prot"><span class="prot-n">{e(nome)}</span>'
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
    if len(d.sprints) > 1:
        linhas_s = "".join(
            f'<tr><td>{e(s.numero)}</td><td>{e(s.titulo[:52])}</td>'
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
        card_hist = card("Historico de sprints", corpo_hist, extra="wide")
    else:
        card_hist = ""

    return TEMPLATE.format(
        projeto=e(d.projeto),
        gerado=e(d.gerado_em),
        tiles=html_tiles,
        sprint=corpo_sprint,
        guards=corpo_guards,
        finops=corpo_fin,
        smoke=corpo_smoke,
        grafo=corpo_grafo,
        loop=corpo_loop,
        protocolos=corpo_prot,
        historico=card_hist,
    )


TEMPLATE = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{projeto} — Neural-Flow</title>
<style>
/* Paleta validada (dataviz): categoricos em ordem fixa, status reservado.
   Claro e escuro sao dois conjuntos escolhidos, nao um flip automatico. */
:root {{
  color-scheme: light;
  --bg:#f6f6f4; --surface:#fcfcfb; --line:#e4e3df;
  --text:#0b0b0b; --text-2:#52514e; --muted:#87857f; --muted-fill:#d9d8d3;
  --series-1:#2a78d6; --series-2:#eb6834; --series-3:#1baf7a;
  --st-good:#0ca30c; --st-warning:#fab219; --st-serious:#ec835a; --st-critical:#d03b3b;
  --radius:14px; --shadow:0 1px 2px rgba(11,11,11,.05), 0 8px 24px rgba(11,11,11,.05);
}}
@media (prefers-color-scheme: dark) {{
  :root:where(:not([data-theme="light"])) {{
    color-scheme: dark;
    --bg:#121211; --surface:#1a1a19; --line:#302f2d;
    --text:#ffffff; --text-2:#c3c2b7; --muted:#8d8b83; --muted-fill:#383835;
    --series-1:#3987e5; --series-2:#d95926; --series-3:#199e70;
    --shadow:0 1px 2px rgba(0,0,0,.3), 0 8px 24px rgba(0,0,0,.25);
  }}
}}
:root[data-theme="dark"] {{
  color-scheme: dark;
  --bg:#121211; --surface:#1a1a19; --line:#302f2d;
  --text:#ffffff; --text-2:#c3c2b7; --muted:#8d8b83; --muted-fill:#383835;
  --series-1:#3987e5; --series-2:#d95926; --series-3:#199e70;
  --shadow:0 1px 2px rgba(0,0,0,.3), 0 8px 24px rgba(0,0,0,.25);
}}
*,*::before,*::after{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--text);
  font:15px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Inter,Roboto,sans-serif;
  -webkit-font-smoothing:antialiased}}
.wrap{{max-width:1180px;margin:0 auto;padding:40px 24px 72px}}
header{{display:flex;flex-wrap:wrap;gap:16px;align-items:baseline;
  justify-content:space-between;margin-bottom:28px}}
h1{{font-size:26px;font-weight:640;letter-spacing:-.02em;margin:0}}
h1 span{{color:var(--muted);font-weight:450}}
.meta{{color:var(--muted);font-size:13px}}
h2{{font-size:13px;font-weight:620;letter-spacing:.06em;text-transform:uppercase;
  color:var(--text-2);margin:0 0 4px}}
.sub{{color:var(--muted);font-size:13px;margin:0 0 12px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:18px;
  align-items:start}}
.card{{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);
  padding:20px 22px;box-shadow:var(--shadow)}}
.card.wide{{grid-column:1/-1}}
/* Tiles */
.tiles{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
  gap:14px;margin-bottom:22px}}
.tile{{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);
  padding:16px 18px;display:flex;flex-direction:column;gap:3px;box-shadow:var(--shadow);
  border-left:3px solid var(--muted-fill)}}
.tile.ok{{border-left-color:var(--st-good)}}
.tile.bad{{border-left-color:var(--st-critical)}}
.tile.warn{{border-left-color:var(--st-warning)}}
.tile-k{{font-size:11px;letter-spacing:.07em;text-transform:uppercase;color:var(--muted)}}
.tile-v{{font-size:27px;font-weight:660;letter-spacing:-.02em;line-height:1.15}}
.tile-s{{font-size:12.5px;color:var(--text-2)}}
/* Hero + linhas */
.row{{display:flex;gap:22px;align-items:flex-start;flex-wrap:wrap}}
.grow{{flex:1;min-width:230px}}
.hero{{display:flex;flex-direction:column;min-width:112px}}
.hero-n{{font-size:42px;font-weight:680;letter-spacing:-.03em;line-height:1}}
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
.kv dd{{margin:0;font-size:14px;font-weight:520}}
.kv .span{{grid-column:1/-1}}
/* Guards */
.guards{{display:grid;gap:10px}}
.guard{{border:1px solid var(--line);border-radius:10px;padding:12px 14px;
  display:flex;flex-direction:column;gap:4px;border-left:3px solid var(--muted-fill)}}
.guard.pass{{border-left-color:var(--st-good)}}
.guard.fail{{border-left-color:var(--st-critical)}}
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
.btn-t{{font-size:13.5px;font-weight:580;color:var(--series-1)}}
.btn-d{{font-size:11.5px;color:var(--muted)}}
@media (prefers-reduced-motion:reduce){{.btn{{transition:none}}.btn:hover{{transform:none}}}}
/* Stats */
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(88px,1fr));gap:14px;
  margin-bottom:18px}}
.stats div{{display:flex;flex-direction:column}}
.s-v{{font-size:24px;font-weight:640;letter-spacing:-.02em}}
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
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>{projeto} <span>· Neural-Flow</span></h1>
  <span class="meta">gerado em {gerado}</span>
</header>

<div class="tiles">{tiles}</div>

<div class="grid">
  <section class="card wide"><h2>Sprint ativa</h2>{sprint}</section>
  <section class="card"><h2>Guards</h2>
    <p class="sub">Executados agora, sobre a arvore de trabalho</p>{guards}</section>
  <section class="card"><h2>FinOps de tokens</h2>
    <p class="sub">Orcamento declarado x consumo observado</p>{finops}</section>
  <section class="card"><h2>smoke-gate</h2>
    <p class="sub">Gate de evidencia sobre codigo e schema</p>{smoke}</section>
  <section class="card"><h2>Indice de conhecimento</h2>
    <p class="sub">Grafo construido sobre a documentacao</p>{grafo}</section>
  <section class="card"><h2>Loop autonomo</h2>
    <p class="sub">Estado em disco, nao na conversa</p>{loop}</section>
  <section class="card"><h2>Protocolos</h2>
    <p class="sub">O que trava e o que se audita</p>{protocolos}</section>
  {historico}
</div>

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
    ap.add_argument(
        "--gerado-em",
        help="carimbo de geracao fixo (ex: 2026-08-08 12:00). Torna a saida "
             "reproduzivel — usado para versionar a pagina de demonstracao.",
    )
    args = ap.parse_args()

    raiz = Path(args.root).resolve()
    destino = Path(args.out).resolve() if args.out else raiz / ".neural-flow" / "dashboard.html"

    dados = coletar(raiz, args.name, args.gerado_em)
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
