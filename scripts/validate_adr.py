#!/usr/bin/env python3
"""
Guard do Protocolo ADR — `docs/protocols/adr-governance.md`
==========================================================
ADR aceito e imutavel; mudanca de rumo gera novo ADR que o supera. Sem guard,
nada impede numeracao duplicada, referencia pendurada ou ciclo de supersecao.

  A1  Numeracao unica — dois ADRs nao compartilham o mesmo numero.
  A2  Status pertence ao conjunto permitido.
  A3  'Superado por ADR-NNN' aponta para ADR existente (sem referencia pendurada).
  A4  Sem ciclo de supersecao (A supera B que supera A).
  A5  ADR aceito referencia a sprint de origem (rastreabilidade Neural-Flow).
  A6  ADR aceito declara guard associado — executavel ou explicitamente
      aspiracional. "Guard aspiracional deve ser declarado como tal."

Uso:
  python scripts/validate_adr.py
  python scripts/validate_adr.py --root <dir> --glob 'docs/decisions/*.md'
"""

from __future__ import annotations

import argparse
import re
import sys
from graphlib import CycleError, TopologicalSorter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nf_guards import (  # noqa: E402
    Resultado, arquivos, campos, chave, eh_placeholder, eh_template, ler,
    numero_do_adr, relatar, sem_acento, status_do_adr, superacoes_adr, Superacao,
)

# Assinatura de origem. O `nf_gate` so executa arquivo que a carrega — projeto
# brownfield pode ter um script homonimo com outra interface, e chama-lo com os
# nossos argumentos produz erro de uso confuso em vez de diagnostico.
NF_GUARD_ASSINATURA = "neural-flow-framework"

PROTOCOLO = "docs/protocols/adr-governance.md"

STATUS_VALIDOS = ("proposto", "aceito", "superado por", "rejeitado")
RE_SPRINT = re.compile(r"\bsprint\s*[-#]?\s*\d+", re.IGNORECASE)


def main() -> int:
    ap = argparse.ArgumentParser(description="Guard do Protocolo ADR (Neural-Flow).")
    ap.add_argument("--root", default=".")
    ap.add_argument("--glob", action="append")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    raiz = Path(args.root).resolve()
    padroes = args.glob or ["docs/adr/*.md", "docs/adrs/*.md", "docs/decisions/*.md"]

    res = Resultado()
    por_numero: dict[int, Path] = {}
    relacoes: list[tuple[Superacao, Path]] = []

    for caminho in arquivos(raiz, *padroes):
        linhas = ler(caminho)
        if linhas is None or eh_template(linhas):
            continue
        if chave(caminho.stem) in {"readme", "index", "indice"}:
            continue
        res.verificado(caminho)

        num = numero_do_adr(caminho, linhas)
        if num is None:
            res.erro(caminho, 1, "A1", "ADR sem numero identificavel no nome nem no titulo")
            continue

        # A1 — numeracao unica
        if num in por_numero:
            res.erro(
                caminho, 1, "A1",
                f"numero ADR-{num:03d} duplicado (ja usado por {por_numero[num].name}) — "
                "numero nunca e reutilizado",
            )
        else:
            por_numero[num] = caminho

        # A2 — status valido
        status, linha_status = status_do_adr(linhas)
        if not status or eh_placeholder(status):
            res.erro(caminho, linha_status, "A2", "ADR sem status declarado")
            continue
        if not any(status.startswith(v) for v in STATUS_VALIDOS):
            res.erro(
                caminho, linha_status, "A2",
                f"status '{status}' fora do conjunto permitido "
                f"({', '.join(STATUS_VALIDOS)})",
            )

        try:
            arestas = superacoes_adr(num, linhas)
        except ValueError as exc:
            res.erro(caminho, linha_status, "A3", str(exc))
            arestas = []
        if status.startswith("superado por") and not arestas:
            res.erro(caminho, linha_status, "A3", "status 'Superado por' sem numero do sucessor")
        relacoes.extend((aresta, caminho) for aresta in arestas)

        # A5 / A6 — so para ADR aceito
        if status.startswith("aceito"):
            corpo = sem_acento("\n".join(linhas)).lower()
            if not RE_SPRINT.search(corpo):
                res.erro(
                    caminho, linha_status, "A5",
                    "ADR aceito sem referencia a sprint de origem (rastreabilidade)",
                )
            dados = campos(linhas)
            guard = dados.get("guard associado") or dados.get("guard")
            declara_guard = (guard is not None and not eh_placeholder(guard)) or (
                "guard" in corpo and ("aspiracional" in corpo or "nao aplicavel" in corpo)
            )
            if not declara_guard:
                res.erro(
                    caminho, linha_status, "A6",
                    "ADR aceito sem guard declarado — informe o guard executavel ou "
                    "declare explicitamente 'aspiracional'/'nao aplicavel'",
                )

    sucessores: dict[int, set[int]] = {}
    for aresta, caminho in relacoes:
        for ref in (aresta.anterior, aresta.sucessor):
            if ref not in por_numero:
                res.erro(caminho, aresta.linha, "A3", f"ADR-{ref:03d} nao existe")
        if aresta.anterior in por_numero and aresta.sucessor in por_numero:
            sucessores.setdefault(aresta.anterior, set()).add(aresta.sucessor)

    # graphlib percorre o grafo iterativamente, inclusive em cadeias longas.
    # A API recebe dependencias: aqui cada anterior depende de seus sucessores.
    while True:
        try:
            TopologicalSorter(sucessores).prepare()
            break
        except CycleError as exc:
            ciclo = exc.args[1]
            descricao = " -> ".join(f"ADR-{n:03d}" for n in reversed(ciclo))
            res.erro(por_numero[ciclo[0]], 1, "A4", f"ciclo de supersecao detectado: {descricao}")
            sucessores[ciclo[1]].remove(ciclo[0])

    return relatar("adr-governance", res, PROTOCOLO, args.quiet)


if __name__ == "__main__":
    sys.exit(main())
