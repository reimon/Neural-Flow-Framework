#!/usr/bin/env python3
"""
Neural-Flow Framework — indice de regras
========================================
Extrai, de todos os documentos de governanca do projeto, **uma linha por regra**
com a fonte (arquivo:linha) e o guard que a trava. Gera dois artefatos:

    .neural-flow/indice-regras.md     legivel por humano e por agente
    .neural-flow/indice-regras.json   estruturado, e corpus para o graphify

Por que existe: o protocolo Vetor de Contexto manda consultar o indice antes de
ler qualquer arquivo, mas o grafo do `graphify` depende de LLM e de rede. Este
indice e deterministico e roda em stdlib pura (ADR-002) — existe desde o minuto
zero da instalacao e continua valendo quando o grafo nao subiu. Quando o grafo
sobe, este arquivo entra nele como corpus: as regras viram nos com fonte.

Uso:
    python3 scripts/nf_indice_regras.py                # gera na raiz atual
    python3 scripts/nf_indice_regras.py --root <dir>
    python3 scripts/nf_indice_regras.py --check        # exit 1 se desatualizado
"""

from __future__ import annotations

# Assinatura de origem. O `nf_gate` so executa arquivo que a carrega — projeto
# brownfield pode ter um script homonimo com outra interface, e chama-lo com os
# nossos argumentos produz erro de uso confuso em vez de diagnostico.
NF_GUARD_ASSINATURA = "neural-flow-framework"

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
from nf_agentes import INDICE_JSON, INDICE_MD  # noqa: E402
from nf_guards import arquivos, eh_placeholder, eh_template, ler, sem_acento  # noqa: E402

# Uma regra e uma frase imperativa. Estes sao os marcadores que a denunciam —
# deliberadamente conservadores: melhor deixar de indexar uma frase morna do que
# encher o indice de prosa e faze-lo custar tanto quanto ler os arquivos.
RE_IMPERATIVO = re.compile(
    r"\b(nunca|sempre|proibid[oa]|obrigatori[oa]|nao\s+(?:use|faca|edite|commit|reimplemente|"
    r"crie|altere|rode|escreva|pergunte)|deve(?:m|r[aá])?\s|so\s+(?:via|apos|depois)|"
    r"pare\s+e\s+pergunte|exige|todo|toda)\b",
    re.IGNORECASE,
)
RE_GUARD = re.compile(r"guard\s*:\s*`?([^`\n.;]+)", re.IGNORECASE)
RE_ITEM = re.compile(r"^\s*(?:[-*+]|\d{1,3}[.)])\s+(?P<texto>.+?)\s*$")
RE_MARKUP = re.compile(r"[`*_]")

# (glob, prefixo do id, categoria). Ordem = ordem no indice: seguranca primeiro,
# porque prevalece sobre o resto.
FONTES: tuple[tuple[str, str, str], ...] = (
    (".github/AI_SAFETY.md", "SEG", "seguranca"),
    ("AGENTS.md", "ARQ", "arquitetura"),
    ("CLAUDE.md", "EXE", "execucao"),
    ("docs/protocols/*.md", "PRO", "protocolo"),
    ("docs/adr/*.md", "ADR", "decisao"),
    ("MEMORY.md", "MEM", "memoria"),
)

# Cabecalhos que sao prosa de contexto, nao regra.
SECOES_IGNORADAS = {
    "contexto", "referencias", "documentos de referencia", "historico",
    "consequencias", "alternativas consideradas", "sumario", "indice",
}


def limpar(texto: str) -> str:
    texto = RE_MARKUP.sub("", texto)
    texto = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", texto)  # link markdown → rotulo
    return re.sub(r"\s+", " ", texto).strip()


def secao_corrente(linhas: list[str], ate: int) -> str:
    for n in range(ate, -1, -1):
        m = re.match(r"^#{1,6}\s+(.*)$", linhas[n])
        if m:
            return limpar(m.group(1))
    return ""


def regras_de(caminho: Path, rel: str, prefixo: str, categoria: str,
              inicio: int = 0) -> list[dict]:
    linhas = ler(caminho)
    if linhas is None or eh_template(linhas):
        return []

    achadas: list[dict] = []
    em_codigo = False
    for n, linha in enumerate(linhas):
        if linha.lstrip().startswith("```"):
            em_codigo = not em_codigo
            continue
        if em_codigo:
            continue
        # Proibicao costuma ser titulo, nao bullet ("### 1. NUNCA rodar apply").
        # Indexar so listas deixaria de fora exatamente as regras mais fortes do
        # `AI_SAFETY.md`, que e o documento que prevalece sobre todos os outros.
        cab = re.match(r"^(#{3,6})\s+(?P<texto>.+?)\s*$", linha)
        if cab:
            titulo = limpar(cab.group("texto"))
            if 10 <= len(titulo) <= 240 and RE_IMPERATIVO.search(sem_acento(titulo)):
                achadas.append({
                    "id": f"{prefixo}-{inicio + len(achadas) + 1:03d}",
                    "categoria": categoria,
                    "regra": titulo,
                    "fonte": f"{rel}:{n + 1}",
                    "secao": limpar(secao_corrente(linhas, max(n - 1, 0))),
                    "guard": None,
                })
            continue

        m = RE_ITEM.match(linha)
        if not m:
            continue
        # Item de lista quebrado em varias linhas e a forma normal de escrever
        # markdown. Ler so a primeira linha corta a regra no meio da frase — e
        # meia regra e pior que nenhuma, porque parece completa.
        partes = [m.group("texto")]
        for seguinte in linhas[n + 1:]:
            if not seguinte.strip() or not seguinte.startswith((" ", "\t")):
                break
            if RE_ITEM.match(seguinte) or seguinte.lstrip().startswith("```"):
                break
            partes.append(seguinte.strip())
        texto = limpar(" ".join(partes))
        # Item de tamanho fora da faixa nao e regra: curto demais e rotulo de
        # lista, longo demais e paragrafo disfarcado de bullet.
        if not (20 <= len(texto) <= 240):
            continue
        # Placeholder de template ainda nao preenchido nao e regra: indexa-lo
        # daria ao agente uma instrucao literalmente vazia.
        vazio = sum(len(p) for p in re.findall(r"<[^<>]{2,80}>", texto))
        if eh_placeholder(texto) or vazio > len(texto) / 2:
            continue
        secao = sem_acento(secao_corrente(linhas, n)).lower()
        if any(ign in secao for ign in SECOES_IGNORADAS):
            continue
        if not RE_IMPERATIVO.search(sem_acento(texto)):
            continue
        guard = RE_GUARD.search(texto)
        achadas.append({
            "id": f"{prefixo}-{inicio + len(achadas) + 1:03d}",
            "categoria": categoria,
            "regra": texto,
            "fonte": f"{rel}:{n + 1}",
            "secao": limpar(secao_corrente(linhas, n)),
            "guard": limpar(guard.group(1)) if guard else None,
        })
    return achadas


def guards_disponiveis(raiz: Path) -> list[dict]:
    """Le o registro de guards do `nf_gate` — o que, de fato, trava alguma coisa.

    Carrega o arquivo **por caminho e so se ele carregar a assinatura**, nunca por
    `import_module`. Duas razoes, ambas concretas:

    - projeto brownfield pode ter um `scripts/nf_gate.py` proprio (o framework
      trata essa colisao em varios outros pontos). Importar pelo nome executaria
      o modulo do projeto — codigo de terceiro rodando dentro de um guard, no
      pre-commit — e leria um `GUARDS` com outra forma;
    - `import_module` devolve o que ja estiver no cache, entao o resultado
      dependeria da ordem de import e nao da arvore que estamos indexando.
    """
    import importlib.util

    candidatos = [raiz / "scripts" / "nf_gate.py", AQUI / "nf_gate.py"]
    for caminho in candidatos:
        try:
            if not caminho.is_file():
                continue
            if "NF_GUARD_ASSINATURA" not in caminho.read_text(
                encoding="utf-8", errors="replace"
            ):
                continue  # homonimo do projeto: nao e o nosso registro de guards
            spec = importlib.util.spec_from_file_location("_nf_gate_indice", caminho)
            if spec is None or spec.loader is None:
                continue
            gate = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(gate)
            return [
                {"guard": nome, "protocolo": proto, "trava": trava}
                for nome, (_script, proto, trava) in gate.GUARDS.items()
            ]
        except Exception:
            continue
    # Indice sem a lista de guards ainda e util; indice que nao gera, nao.
    return []


def coletar(raiz: Path) -> tuple[list[dict], list[str]]:
    regras: list[dict] = []
    fontes_lidas: list[str] = []
    # Numeracao por prefixo, nao global: `ARQ-001` deve ser a primeira regra de
    # arquitetura, e nao a quarta regra do indice por acaso.
    contador: dict[str, int] = {}
    for padrao, prefixo, categoria in FONTES:
        for caminho in arquivos(raiz, padrao):
            rel = str(caminho.relative_to(raiz))
            achadas = regras_de(caminho, rel, prefixo, categoria, contador.get(prefixo, 0))
            contador[prefixo] = contador.get(prefixo, 0) + len(achadas)
            regras.extend(achadas)
            fontes_lidas.append(rel)
    return regras, sorted(set(fontes_lidas))


def impressao_digital(raiz: Path, fontes: list[str]) -> str:
    """Hash do conteudo das fontes. Muda a fonte, o indice fica desatualizado."""
    h = hashlib.sha256()
    for rel in fontes:
        h.update(rel.encode("utf-8"))
        try:
            h.update((raiz / rel).read_bytes())
        except OSError:
            h.update(b"<ausente>")
    return h.hexdigest()[:16]


def render_md(regras: list[dict], guards: list[dict], digital: str) -> str:
    linhas = [
        "# Indice de regras",
        "",
        "> Gerado por `python3 scripts/nf_indice_regras.py`. **Nao edite a mao** —",
        "> edite a fonte de cada regra e regere. O guard `agentes` trava a divergencia.",
        "",
        "Consulte este indice **antes** de ler os arquivos. Cada linha traz a fonte",
        "(`arquivo:linha`) — leia so o que a resposta exigir.",
        "",
        f"- regras indexadas: **{len(regras)}**",
        f"- impressao digital das fontes: `{digital}`",
        "",
    ]
    if guards:
        linhas += [
            "## Guards executaveis",
            "",
            "Rode todos com `python3 scripts/nf_gate.py`. Nunca use `--no-verify`.",
            "",
            "| Guard | Protocolo | O que trava |",
            "| --- | --- | --- |",
        ]
        linhas += [f"| `{g['guard']}` | `{g['protocolo']}` | {g['trava']} |" for g in guards]
        linhas.append("")

    por_categoria: dict[str, list[dict]] = {}
    for r in regras:
        por_categoria.setdefault(r["categoria"], []).append(r)

    for categoria, itens in por_categoria.items():
        linhas += [f"## {categoria.capitalize()}", "", "| ID | Regra | Fonte | Guard |",
                   "| --- | --- | --- | --- |"]
        for r in itens:
            guard = f"`{r['guard']}`" if r["guard"] else "—"
            linhas.append(f"| `{r['id']}` | {r['regra']} | `{r['fonte']}` | {guard} |")
        linhas.append("")

    if not regras:
        linhas += [
            "## Nenhuma regra indexada",
            "",
            "As fontes de governanca ainda estao no estado de template ou vazias.",
            "Preencha `AGENTS.md` e `.github/AI_SAFETY.md` e regere o indice.",
            "",
        ]
    return "\n".join(linhas)


def gerar(raiz: Path) -> tuple[str, str, str]:
    """Devolve (markdown, json, impressao digital) sem escrever nada."""
    regras, fontes = coletar(raiz)
    guards = guards_disponiveis(raiz)
    digital = impressao_digital(raiz, fontes)
    dados = {
        "versao": 1,
        "impressao_digital": digital,
        "fontes": fontes,
        "guards": guards,
        "regras": regras,
    }
    return render_md(regras, guards, digital), json.dumps(dados, ensure_ascii=False, indent=2) + "\n", digital


def desatualizado(raiz: Path) -> str | None:
    """Motivo pelo qual o indice nao vale mais, ou None se estiver em dia.

    Compara a impressao digital gravada com a das fontes de agora. Nao compara o
    texto renderizado inteiro: se o gerador melhorar a formatacao, todo projeto
    instalado passaria a falhar no gate sem que nenhuma regra tenha mudado.
    """
    caminho = raiz / INDICE_JSON
    if not caminho.is_file():
        return f"{INDICE_JSON} nao existe"
    if not (raiz / INDICE_MD).is_file():
        return f"{INDICE_MD} nao existe"
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return f"{INDICE_JSON} ilegivel ({exc.__class__.__name__})"
    _, _, agora = gerar(raiz)
    if dados.get("impressao_digital") != agora:
        return "as fontes de governanca mudaram desde a ultima geracao do indice"
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Indice de regras (Neural-Flow).")
    ap.add_argument("--root", default=".")
    ap.add_argument("--check", action="store_true", help="nao escreve; exit 1 se desatualizado")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    raiz = Path(args.root).resolve()

    if args.check:
        motivo = desatualizado(raiz)
        if motivo:
            print(f"indice-regras: FAIL — {motivo}")
            print("  regere com: python3 scripts/nf_indice_regras.py")
            return 1
        if not args.quiet:
            print("indice-regras: em dia — OK")
        return 0

    md, js, digital = gerar(raiz)
    (raiz / INDICE_MD).parent.mkdir(parents=True, exist_ok=True)
    (raiz / INDICE_MD).write_text(md, encoding="utf-8")
    (raiz / INDICE_JSON).write_text(js, encoding="utf-8")
    if not args.quiet:
        n = len(json.loads(js)["regras"])
        print(f"indice-regras: {n} regra(s) — {INDICE_MD} ({digital})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
