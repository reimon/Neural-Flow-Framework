#!/usr/bin/env python3
"""
Guard do Protocolo Spec-First — `docs/protocols/spec-first.md`
=============================================================
Verifica o que e verificavel por maquina numa especificacao de modulo.

Dois detalhes que o protocolo exige e que estao aqui:

  * **Descobre os modulos pelo diretorio**, nunca por lista fixa — modulo novo
    nao nasce sem gate por esquecimento de alguem.
  * Rodado pelo hook, valida **o que esta em stage** (o hook materializa o
    indice numa arvore temporaria e chama este script com --root apontando la).

Checagens
---------
Sempre ativas (funcionam sem configuracao nenhuma):

  P1  Toda secao obrigatoria presente.
  P2  Nenhuma secao obrigatoria vazia ou so com placeholder.
  P3  Invariantes seguem o padrao de identificador (`<PREFIXO>-INV-NNN`).
  P4  Criterios de aceite existem e sao numerados.
  P5  Rastreabilidade de IDs: identificador definido e citado ao menos uma vez
      fora da definicao (sem orfao), e identificador citado existe em algum
      lugar do corpus (sem referencia pendurada).
  P6  Link markdown interno resolve.
  P7  Todo bloco ```json parseia.

Ativas quando configuradas em `.neural-flow.json` (a lista e de dominio, o
mecanismo e generico):

  P8  Fonte de dados citada existe e carrega `last_verified`.
  P9  Linguagem proibida — a menos que a linha a negue ou proiba.
  P10 Estrutura multiarquivo do modulo, e README indexando todos os arquivos.

Configuracao
------------
    {
      "spec_sections":  ["Proposito", "Dominio de dados", ...],
      "spec_globs":     ["docs/modulos/*/spec.md"],
      "spec_fontes":    ["docs/dados-de-referencia"],
      "spec_linguagem_proibida": ["garantido", "sera aprovado"],
      "spec_estrutura": {"arquivos": 10, "readme": true}
    }

Uso:
  python3 scripts/validate_module_spec.py
  python3 scripts/validate_module_spec.py --root <dir> --glob 'docs/modulos/**/*.md'
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nf_guards import (  # noqa: E402
    Resultado, arquivos, eh_placeholder, eh_template, ler, relatar, secao,
    sem_acento,
)

PROTOCOLO = "docs/protocols/spec-first.md"

SECOES_PADRAO = [
    "Proposito e fronteira",
    "Dominio de dados",
    "Invariantes",
    "Fonte de verdade",
    "Contratos e eventos",
    "Modos de falha",
    "Linguagem segura",
    "Dependencias",
    "Criterios de aceite",
    "Fora de escopo",
]

GLOBS_PADRAO = ["docs/modulos/**/*.md", "docs/modules/**/*.md", "specs/**/*.md"]

RE_INVARIANTE = re.compile(r"\b[A-Z]{2,6}-INV-\d{2,4}\b")
RE_NUMERADO = re.compile(r"^\s*(?:[-*]\s*)?\d+[.)]\s+\S")

# Identificador rastreavel: PREFIXO-FAMILIA-NUMERO. Cobre `CAT-INV-001`,
# `RULE-CAT-001`, `TC-CAT-014` e `ADR-07-001` (familia numerica).
RE_ID = re.compile(r"\b([A-Z]{2,6}-(?:[A-Z]{2,4}|\d{2})-\d{2,4})\b")

# Um ID esta sendo DEFINIDO quando aparece em titulo, em negrito, ou abrindo
# item de lista ou linha de tabela. Em qualquer outro lugar, e citacao.
RE_DEFINE = (
    re.compile(r"^#{1,6}\s+.*?`?([A-Z]{2,6}-(?:[A-Z]{2,4}|\d{2})-\d{2,4})`?"),
    re.compile(r"\*\*`?([A-Z]{2,6}-(?:[A-Z]{2,4}|\d{2})-\d{2,4})`?"),
    re.compile(r"^\s*[-*|]\s*`?([A-Z]{2,6}-(?:[A-Z]{2,4}|\d{2})-\d{2,4})`?\s*[—\-:|]"),
)

RE_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
RE_BLOCO_JSON = re.compile(r"```json\s*\n(.*?)```", re.S)

# Palavras que invertem o sentido da linha. "nunca prometa aprovacao garantida"
# nao pode ser flagrado como promessa.
NEGACOES = ("nao ", "nunca", "jamais", "proibi", "evite", "sem ", "nenhum",
            "veta", "impede", "recusa")

IGNORAR_LINK = ("http://", "https://", "mailto:", "#")


def config(raiz: Path) -> dict:
    caminho = raiz / ".neural-flow.json"
    if caminho.is_file():
        try:
            return json.loads(caminho.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"aviso: .neural-flow.json invalido ({exc}) — usando defaults")
    return {}


def conteudo_util(linhas: list[str], faixa: tuple[int, int]) -> list[str]:
    saida = []
    for linha in linhas[faixa[0]:faixa[1]]:
        texto = linha.strip().lstrip("-*# ").strip()
        if not texto or texto.startswith("|") or eh_placeholder(texto):
            continue
        if texto.lower() in {"item 1", "item 2", "a preencher"}:
            continue
        saida.append(texto)
    return saida


def fora_de_bloco(linhas: list[str]):
    """Itera (numero, linha) pulando o conteudo de blocos de codigo."""
    dentro = False
    for n, linha in enumerate(linhas, 1):
        if linha.lstrip().startswith("```"):
            dentro = not dentro
            continue
        if not dentro:
            yield n, linha


# ── Checagens ──────────────────────────────────────────────────────────────────


def checar_secoes(caminho: Path, linhas: list[str], secoes: list[str],
                  res: Resultado) -> None:
    for titulo in secoes:
        faixa = secao(linhas, titulo)
        if faixa is None:
            res.erro(caminho, None, "P1", f"spec sem a secao obrigatoria '{titulo}'")
            continue
        if not conteudo_util(linhas, faixa):
            res.erro(caminho, faixa[0], "P2",
                     f"secao '{titulo}' vazia ou so com placeholder/exemplo")


def checar_invariantes_e_aceite(caminho: Path, linhas: list[str],
                                res: Resultado) -> None:
    faixa_inv = secao(linhas, "Invariantes")
    if faixa_inv and conteudo_util(linhas, faixa_inv):
        trecho = "\n".join(linhas[faixa_inv[0]:faixa_inv[1]])
        if not RE_INVARIANTE.search(trecho):
            res.erro(caminho, faixa_inv[0], "P3",
                     "invariantes sem identificador no padrao <PREFIXO>-INV-NNN — "
                     "sem ID nao ha como referenciar a invariante em teste ou ADR")

    faixa_ac = secao(linhas, "Criterios de aceite")
    if faixa_ac:
        itens = [
            l for l in linhas[faixa_ac[0]:faixa_ac[1]]
            if RE_NUMERADO.match(l) or re.match(r"^\s*[-*]\s*\[[ xX]\]", l)
        ]
        if not itens:
            res.erro(caminho, faixa_ac[0], "P4",
                     "criterios de aceite nao numerados — item de plano precisa poder "
                     "referenciar o criterio pelo numero")


def indexar_ids(caminho: Path, linhas: list[str], definidos: dict,
                citados: dict) -> None:
    """Separa definicao de citacao. Um ID definido e nunca citado e spec morta;
    um ID citado e nunca definido e referencia pendurada."""
    for n, linha in fora_de_bloco(linhas):
        vistos_como_definicao = set()
        for padrao in RE_DEFINE:
            m = padrao.search(linha)
            if m:
                ident = m.group(1)
                definidos.setdefault(ident, (caminho, n))
                vistos_como_definicao.add(ident)
        for ident in RE_ID.findall(linha):
            if ident in vistos_como_definicao:
                continue
            citados.setdefault(ident, []).append((caminho, n))


def checar_ids(definidos: dict, citados: dict, res: Resultado) -> None:
    for ident, (caminho, n) in sorted(definidos.items()):
        if ident not in citados:
            res.erro(caminho, n, "P5",
                     f"'{ident}' e definido mas nunca citado em outro lugar — "
                     "invariante ou regra que ninguem referencia e spec morta")
    for ident, ocorrencias in sorted(citados.items()):
        if ident not in definidos:
            caminho, n = ocorrencias[0]
            res.erro(caminho, n, "P5",
                     f"'{ident}' e citado mas nao esta definido em nenhuma spec — "
                     "referencia pendurada")


def checar_links(raiz: Path, caminho: Path, linhas: list[str],
                 res: Resultado) -> None:
    for n, linha in fora_de_bloco(linhas):
        for alvo in RE_LINK.findall(linha):
            alvo = alvo.split("#")[0].strip()
            if not alvo or alvo.startswith(IGNORAR_LINK):
                continue
            for base in (caminho.parent, raiz):
                try:
                    if (base / alvo).resolve().exists():
                        break
                except (OSError, ValueError):
                    continue
            else:
                res.erro(caminho, n, "P6", f"link interno nao resolve: {alvo}")


def checar_json(caminho: Path, texto: str, res: Resultado) -> None:
    for bloco in RE_BLOCO_JSON.findall(texto):
        try:
            json.loads(bloco)
        except json.JSONDecodeError as exc:
            linha = texto[:texto.find(bloco)].count("\n") + 1
            res.erro(caminho, linha, "P7",
                     f"bloco json nao parseia ({exc.msg} na linha {exc.lineno} do bloco)")


def checar_fontes(raiz: Path, caminho: Path, linhas: list[str],
                  fontes: list[str], res: Resultado) -> None:
    """Valor regulado sem fonte datada e o modo de falha mais caro do framework:
    o numero parece certo e ninguem sabe de quando e."""
    if not fontes:
        return
    padrao = re.compile(r"[`\(]((?:" + "|".join(re.escape(f) for f in fontes) + r")[\w./-]*)")
    for n, linha in fora_de_bloco(linhas):
        for alvo in padrao.findall(linha):
            destino = raiz / alvo
            if not destino.exists():
                res.erro(caminho, n, "P8", f"fonte citada nao existe: {alvo}")
                continue
            if destino.is_dir():
                continue
            try:
                conteudo = destino.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if "last_verified" not in conteudo:
                res.erro(caminho, n, "P8",
                         f"fonte '{alvo}' sem `last_verified` — valor sem data de "
                         "verificacao nao e fonte de verdade")


def checar_linguagem(caminho: Path, linhas: list[str], proibidas: list[str],
                     res: Resultado) -> None:
    if not proibidas:
        return
    for n, linha in fora_de_bloco(linhas):
        normal = sem_acento(linha).lower()
        if any(neg in normal for neg in NEGACOES):
            continue  # a linha esta proibindo, nao prometendo
        for termo in proibidas:
            if sem_acento(termo).lower() in normal:
                res.erro(caminho, n, "P9",
                         f"linguagem proibida: '{termo}' — a spec nao pode prometer "
                         "o que o sistema nao garante")
                break


def checar_estrutura(raiz: Path, modulos: dict, estrutura: dict,
                     res: Resultado) -> None:
    """Modulo com um arquivo so nao sustenta detalhamento; o padrao de N arquivos
    forca separar dominio, contratos, falhas e aceite em vez de amontoar."""
    if not estrutura:
        return
    minimo = int(estrutura.get("arquivos", 0) or 0)
    exige_readme = bool(estrutura.get("readme", False))
    for diretorio, caminhos in sorted(modulos.items()):
        nomes = {c.name for c in caminhos}
        readme = next((c for c in caminhos if c.stem.lower() == "readme"), None)
        conteudo = [c for c in caminhos if c.stem.lower() != "readme"]
        if minimo and len(conteudo) < minimo:
            res.erro(diretorio, None, "P10",
                     f"modulo com {len(conteudo)} arquivo(s); o padrao exige {minimo} "
                     "— um arquivo so nao sustenta o nivel de detalhe")
        if exige_readme and readme is None:
            res.erro(diretorio, None, "P10", "modulo sem README indexando os arquivos")
            continue
        if readme is None:
            continue
        indice = readme.read_text(encoding="utf-8", errors="replace")
        for c in conteudo:
            if c.name not in indice:
                res.erro(readme, None, "P10",
                         f"'{c.name}' nao esta linkado no README do modulo — "
                         "arquivo fora do indice fica invisivel para quem chega")


# ── Orquestracao ───────────────────────────────────────────────────────────────


def main() -> int:
    ap = argparse.ArgumentParser(description="Guard do Spec-First (Neural-Flow).")
    ap.add_argument("--root", default=".")
    ap.add_argument("--glob", action="append")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    raiz = Path(args.root).resolve()
    cfg = config(raiz)
    secoes = cfg.get("spec_sections", SECOES_PADRAO)
    padroes = args.glob or cfg.get("spec_globs", GLOBS_PADRAO)
    fontes = cfg.get("spec_fontes", [])
    proibidas = cfg.get("spec_linguagem_proibida", [])
    estrutura = cfg.get("spec_estrutura", {})

    res = Resultado()
    definidos: dict = {}
    citados: dict = {}
    modulos: dict = {}

    for caminho in arquivos(raiz, *padroes):
        linhas = ler(caminho)
        if linhas is None or eh_template(linhas):
            continue
        modulos.setdefault(caminho.parent, []).append(caminho)
        if caminho.stem.lower() in {"readme", "index", "indice"}:
            indexar_ids(caminho, linhas, definidos, citados)
            continue
        res.verificado(caminho)

        checar_secoes(caminho, linhas, secoes, res)
        checar_invariantes_e_aceite(caminho, linhas, res)
        indexar_ids(caminho, linhas, definidos, citados)
        checar_links(raiz, caminho, linhas, res)
        checar_json(caminho, "\n".join(linhas), res)
        checar_fontes(raiz, caminho, linhas, fontes, res)
        checar_linguagem(caminho, linhas, proibidas, res)

    if res.verificados:
        checar_ids(definidos, citados, res)
        checar_estrutura(raiz, modulos, estrutura, res)

    return relatar("spec-first", res, PROTOCOLO, args.quiet)


if __name__ == "__main__":
    sys.exit(main())
