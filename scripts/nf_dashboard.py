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


def diagrama_arquitetura() -> str:
    """Incorpora o diagrama para que a pagina explicativa tambem abra offline."""
    try:
        return (ASSETS / "arquitetura.svg").read_text(encoding="utf-8")
    except OSError:
        return '<p class="vazio">Diagrama de arquitetura não encontrado.</p>'

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
    tokens: object = None
    janela_dias: int = 30

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
        tokens=coletar_tokens(raiz, dias=dias, diretorio=transcripts),
        janela_dias=dias,
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
<p><strong>O que e.</strong> Os dez protocolos do framework e o estado de cada um neste
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


def render(d: Dados, rel_grafo: str = "graphify-out/") -> str:
    ativa = d.ativa
    tel = d.tokens          # usado tanto no FinOps quanto no quadro de consumo
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
            try:
                referencia = date.fromisoformat(d.gerado_em.split()[0])
            except (ValueError, IndexError):
                referencia = date.today()
            faltam = (date.fromisoformat(ativa.prazo) - referencia).days
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

    if tel is not None and getattr(tel, "disponivel", False) and com_budget:
        ativa_b = next((s for s in com_budget if s.status == "em andamento"), com_budget[-1])
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
            '<p class="nota">O medido vem dos transcripts locais e cobre 30 dias do projeto '
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
        botao_h, janela_h = ajuda(*(("historico",) + AJUDA_QUADROS["historico"]))
        janelas.append(janela_h)
        card_hist = (f'<section class="card wide"><h2>Historico de sprints{botao_h}</h2>'
                     f'{corpo_hist}</section>')
    else:
        card_hist = ""

    botoes_quadro = {}
    for chave, (titulo, corpo) in AJUDA_QUADROS.items():
        botao, janela = ajuda(chave, titulo, corpo)
        botoes_quadro[f"ajuda_{chave}"] = botao
        janelas.append(janela)

    if guards_fail:
        plural = "s" if guards_fail != 1 else ""
        verbo = "exigem" if guards_fail != 1 else "exige"
        resumo_status = (f"Execução em andamento, com {guards_fail} controle{plural} "
                         f"que {verbo} ação antes do próximo commit.")
        resumo_detalhe = "Prioridade: regularize os guards reprovados e registre a evidência pendente."
        resumo_tipo = "attention"
        resumo_rotulo = "Atenção necessária"
    else:
        resumo_status = "Todos os controles ativos estão conformes para o próximo commit."
        resumo_detalhe = "Acompanhe o consumo e mantenha o registro de evidências atualizado."
        resumo_tipo = "healthy"
        resumo_rotulo = "Controles conformes"

    meses = ("jan", "fev", "mar", "abr", "mai", "jun",
             "jul", "ago", "set", "out", "nov", "dez")
    try:
        _d, _h = d.gerado_em.split()
        _a, _m, _dia = _d.split("-")
        gerado_legivel = f"{_dia} {meses[int(_m) - 1]} {_a} · {_h}"
    except (ValueError, IndexError):
        gerado_legivel = d.gerado_em

    return TEMPLATE.format(
        arquitetura=diagrama_arquitetura(),
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
        historico=card_hist,
        resumo_status=resumo_status,
        resumo_detalhe=resumo_detalhe,
        resumo_tipo=resumo_tipo,
        resumo_rotulo=resumo_rotulo,
    )


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
.header-tools{{display:flex;align-items:center;gap:10px;flex-wrap:wrap;justify-content:flex-end}}.view-tabs,.theme-picker{{display:flex;align-items:center;gap:4px;padding:3px;border:1px solid var(--line);border-radius:9px;background:var(--surface);box-shadow:0 1px 0 rgba(255,255,255,.16) inset}}.view-tabs legend,.view-tabs input,.theme-picker legend,.theme-picker input{{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}}.view-tab,.theme-option{{position:relative;display:grid;place-items:center;border-radius:6px;cursor:pointer;transition:background .18s,transform .18s}}.view-tab{{min-height:27px;padding:0 9px;font-size:11px;font-weight:650;color:var(--text-2)}}.theme-option{{width:29px;height:27px}}.view-tab:hover,.theme-option:hover{{background:var(--acao-hover)}}.view-tab:active,.theme-option:active{{transform:scale(.96)}}.view-tabs input:focus-visible + .view-tab,.theme-picker input:focus-visible + .theme-option{{outline:2px solid var(--series-1);outline-offset:2px}}.view-tabs input:checked + .view-tab,.theme-picker input:checked + .theme-option{{background:var(--muted-fill);color:var(--text)}}.theme-swatch{{display:block;width:15px;height:15px;border-radius:50%;border:1px solid rgba(255,255,255,.46);box-shadow:0 0 0 1px rgba(18,35,45,.18)}}.theme-swatch.light{{background:linear-gradient(135deg,#f7fafb 0 50%,#146c84 50%)}}.theme-swatch.dark{{background:linear-gradient(135deg,#171a1f 0 50%,#5fb3c9 50%)}}.theme-swatch.giyu{{background:conic-gradient(#6f3549 0 25%,#d08350 0 50%,#356b5a 0 75%,#dbe8eb 0)}}.theme-swatch.tanjiro{{background:conic-gradient(#43c9e8 0 25%,#43bf91 0 50%,#08192b 0 75%,#d87e8f 0)}}
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
</style>
</head>
<body>
<div class="wrap">
<header>
  <div class="brand-lockup"><span class="brand-mark" aria-hidden="true">NF</span><div><h1>{projeto} <span>· Neural-Flow</span></h1><p>Visão de execução, risco e governança do projeto</p></div></div>
  <div class="header-tools"><fieldset class="view-tabs"><legend>Seção do dashboard</legend><input type="radio" name="view" id="view-dashboard" checked><label class="view-tab" for="view-dashboard">Painel</label><input type="radio" name="view" id="view-about"><label class="view-tab" for="view-about">O Neural-Flow</label></fieldset><fieldset class="theme-picker"><legend>Escolha a paleta do dashboard</legend><input type="radio" name="theme" id="theme-light" checked><label class="theme-option" for="theme-light" aria-label="Tema claro"><span class="theme-swatch light" aria-hidden="true"></span></label><input type="radio" name="theme" id="theme-dark"><label class="theme-option" for="theme-dark" aria-label="Tema escuro"><span class="theme-swatch dark" aria-hidden="true"></span></label><input type="radio" name="theme" id="theme-giyu"><label class="theme-option" for="theme-giyu" aria-label="Tema Giyu: vinho, verde e azul-neblina"><span class="theme-swatch giyu" aria-hidden="true"></span></label><input type="radio" name="theme" id="theme-tanjiro"><label class="theme-option" for="theme-tanjiro" aria-label="Tema Tanjiro: água, verde e azul-noturno"><span class="theme-swatch tanjiro" aria-hidden="true"></span></label></fieldset><div class="header-meta"><span class="live-dot" aria-hidden="true"></span><span>Atualizado em {gerado_legivel}</span></div></div>
</header>

<main class="dashboard-view">
<section class="command-bar {resumo_tipo}" aria-label="Resumo executivo">
  <div class="command-copy"><span class="eyebrow">Resumo executivo</span><strong>{resumo_status}</strong><span>{resumo_detalhe}</span></div>
  <div class="command-actions"><span class="risk-badge {resumo_tipo}"><i aria-hidden="true"></i> {resumo_rotulo}</span><a href="#guards" class="action-link">Ver controles <span aria-hidden="true">→</span></a></div>
</section>

<div class="tiles">{tiles}</div>

<div class="grid">
  <section class="card wide"><h2>Sprint ativa{ajuda_sprint}</h2>{sprint}</section>
  <section class="card" id="guards"><h2>Guards{ajuda_guards}</h2>
    <p class="sub">Executados agora, sobre a arvore de trabalho</p>{guards}</section>
  <section class="card"><h2>FinOps de tokens{ajuda_finops}</h2>
    <p class="sub">Orcamento declarado x consumo observado</p>{finops}</section>
  <section class="card"><h2>smoke-gate{ajuda_smoke}</h2>
    <p class="sub">Gate de evidencia sobre codigo e schema</p>{smoke}</section>
  <section class="card"><h2>Indice de conhecimento{ajuda_grafo}</h2>
    <p class="sub">Grafo construido sobre a documentacao</p>{grafo}</section>
  <section class="card"><h2>Loop autonomo{ajuda_loop}</h2>
    <p class="sub">Estado em disco, nao na conversa</p>{loop}</section>
  <section class="card"><h2>Consumo real de tokens{ajuda_tokens}</h2>
    <p class="sub">Medido nos transcripts locais, nao declarado</p>{tokens}</section>
  <section class="card"><h2>Ritmo e ferramentas{ajuda_ritmo}</h2>
    <p class="sub">Como o trabalho se distribuiu</p>{ritmo}</section>
  <section class="card"><h2>Protocolos{ajuda_protocolos}</h2>
    <p class="sub">O que trava e o que se audita</p>{protocolos}</section>
{historico}
</div>
</main>

<main class="about-view" aria-label="Sobre o Neural-Flow Framework">
  <section class="about-hero"><div class="about-copy"><p class="about-kicker">Método de engenharia assistida por IA</p><h2>Transformar intenção em mudança verificável.</h2><p>Neural-Flow é um framework de governança para trabalho técnico executado por pessoas e agentes. Ele organiza a execução em artefatos legíveis, regras verificáveis e evidências reproduzíveis, para que velocidade não dependa de confiança cega.</p><p>O objetivo é simples: cada mudança deve ter escopo, contexto, decisão e prova. Assim, o projeto permanece compreensível quando a conversa acaba, o agente muda ou a equipe cresce.</p></div><figure class="architecture-figure"><button type="button" class="architecture-trigger" popovertarget="diagrama-arquitetura" aria-label="Ampliar diagrama de arquitetura"><span class="architecture-hint" aria-hidden="true">Clique para ampliar</span>{arquitetura}</button><figcaption>Arquitetura do fluxo: os artefatos registram a intenção, os guards bloqueiam desvios e o CI confirma a autoridade do processo.</figcaption></figure></section>
  <section class="about-grid"><article class="about-block"><h3>O que o framework resolve</h3><p>Projetos guiados por IA frequentemente perdem contexto, misturam hipótese com fato e deixam decisões importantes só no chat. Neural-Flow torna o estado do trabalho explícito em disco, reduzindo retrabalho e tornando a retomada confiável.</p><ul class="about-principles"><li><strong>Estado persistente</strong>Plano, diário, divergências e sprint registram o que foi feito e o que falta.</li><li><strong>Decisão rastreável</strong>ADRs preservam o porquê de mudanças arquiteturais sem reescrever o histórico.</li></ul></article><article class="about-block"><h3>Como ele preserva autonomia</h3><p>Autonomia não significa ausência de limites. O framework define até onde um agente pode avançar e quais decisões exigem revisão humana, especialmente em escopos sensíveis ou irreversíveis.</p><ul class="about-principles"><li><strong>Guards executáveis</strong>Regras críticas deixam de ser recomendação e passam a bloquear o commit quando violadas.</li><li><strong>Evidência antes de conclusão</strong>Um item só está pronto quando a verificação foi executada e registrada.</li></ul></article></section>
  <section class="about-cycle"><h3>O ciclo operacional</h3><ol class="cycle-steps"><li>Defina a sprint, o escopo, a autonomia e o orçamento.</li><li>Consulte o índice e registre fontes que sustentam a decisão.</li><li>Implemente uma mudança pequena e deixe o estado no plano.</li><li>Execute os guards; se reprovar, corrija o artefato ou a mudança.</li><li>Registre evidência, faça o commit e deixe o CI validar novamente.</li></ol></section>
</main>

<div popover id="diagrama-arquitetura" class="diagram-modal" role="dialog" aria-label="Diagrama de arquitetura ampliado"><div class="diagram-modal-head"><strong>Como uma mudança vira commit</strong><button type="button" class="diagram-close" popovertarget="diagrama-arquitetura" popovertargetaction="hide">Fechar</button></div><div class="diagram-modal-body">{arquitetura}</div></div>

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
