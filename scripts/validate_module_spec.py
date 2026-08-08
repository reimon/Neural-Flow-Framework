#!/usr/bin/env python3
"""
Guard do Protocolo Spec-First — `docs/protocols/spec-first.md`
=============================================================
Verifica que toda spec de modulo tem a estrutura minima obrigatoria.

Dois detalhes de implementacao que o protocolo exige e que estao aqui:

  * **Descobre os modulos pelo diretorio**, nunca por lista fixa — modulo novo
    nao nasce sem gate por esquecimento de alguem.
  * Rodado pelo hook, valida **o que esta em stage** (o hook materializa o
    indice numa arvore temporaria e chama este script com --root apontando la).

  P1  Toda secao obrigatoria presente na spec.
  P2  Nenhuma secao obrigatoria vazia ou so com placeholder de template.
  P3  Invariantes seguem o padrao de identificador (`<PREFIXO>-INV-NNN`).
  P4  Criterios de aceite existem e sao numerados.

As secoes obrigatorias sao configuraveis por projeto em `.neural-flow.json`:

    { "spec_sections": ["Proposito e fronteira", "Dominio de dados", ...],
      "spec_globs": ["docs/modulos/*/spec.md"] }

Uso:
  python scripts/validate_module_spec.py
  python scripts/validate_module_spec.py --root <dir> --glob 'docs/modulos/**/*.md'
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

RE_INVARIANTE = re.compile(r"\b[A-Z]{2,6}-INV-\d{3}\b")
RE_NUMERADO = re.compile(r"^\s*(?:[-*]\s*)?\d+[.)]\s+\S")


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


def validar(caminho: Path, secoes: list[str], res: Resultado) -> None:
    linhas = ler(caminho)
    if linhas is None or eh_template(linhas):
        return
    if caminho.stem.lower() in {"readme", "index", "indice"}:
        return
    res.verificado(caminho)

    for titulo in secoes:
        faixa = secao(linhas, titulo)
        if faixa is None:
            res.erro(caminho, None, "P1", f"spec sem a secao obrigatoria '{titulo}'")
            continue
        if not conteudo_util(linhas, faixa):
            res.erro(
                caminho, faixa[0], "P2",
                f"secao '{titulo}' vazia ou so com placeholder/exemplo",
            )

    # P3 — invariantes identificados
    faixa_inv = secao(linhas, "Invariantes")
    if faixa_inv and conteudo_util(linhas, faixa_inv):
        trecho = "\n".join(linhas[faixa_inv[0]:faixa_inv[1]])
        if not RE_INVARIANTE.search(trecho):
            res.erro(
                caminho, faixa_inv[0], "P3",
                "invariantes sem identificador no padrao <PREFIXO>-INV-NNN — "
                "sem ID nao ha como referenciar a invariante em teste ou ADR",
            )

    # P4 — criterios de aceite numerados
    faixa_ac = secao(linhas, "Criterios de aceite")
    if faixa_ac:
        itens = [
            l for l in linhas[faixa_ac[0]:faixa_ac[1]]
            if RE_NUMERADO.match(l) or re.match(r"^\s*[-*]\s*\[[ xX]\]", l)
        ]
        if not itens:
            res.erro(
                caminho, faixa_ac[0], "P4",
                "criterios de aceite nao numerados — item de plano precisa poder "
                "referenciar o criterio pelo numero",
            )


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

    res = Resultado()
    for caminho in arquivos(raiz, *padroes):
        validar(caminho, secoes, res)
    return relatar("spec-first", res, PROTOCOLO, args.quiet)


if __name__ == "__main__":
    sys.exit(main())
