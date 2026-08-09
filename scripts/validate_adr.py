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

# Assinatura de origem. O `nf_gate` so executa arquivo que a carrega — projeto
# brownfield pode ter um script homonimo com outra interface, e chama-lo com os
# nossos argumentos produz erro de uso confuso em vez de diagnostico.
NF_GUARD_ASSINATURA = "neural-flow-framework"

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nf_guards import (  # noqa: E402
    Resultado, arquivos, campos, chave, eh_placeholder, eh_template, ler,
    relatar, secao, sem_acento,
)

PROTOCOLO = "docs/protocols/adr-governance.md"

STATUS_VALIDOS = ("proposto", "aceito", "superado por", "rejeitado")
RE_NUMERO = re.compile(r"ADR[-_ ]?(?:[A-Z]+[-_])?(\d{1,4})", re.IGNORECASE)
RE_SUPERADO = re.compile(r"superado\s+por\s+ADR[-_ ]?(?:[A-Z]+[-_])?(\d{1,4})", re.IGNORECASE)
RE_SPRINT = re.compile(r"\bsprint\s*[-#]?\s*\d+", re.IGNORECASE)


def numero_do_adr(caminho: Path, linhas: list[str]) -> int | None:
    m = RE_NUMERO.search(caminho.name)
    if m:
        return int(m.group(1))
    for linha in linhas[:5]:
        m = RE_NUMERO.search(linha)
        if m:
            return int(m.group(1))
    return None


def status_do_adr(linhas: list[str]) -> tuple[str, int]:
    faixa = secao(linhas, "Status")
    if faixa is None:
        return "", 1
    for n in range(faixa[0], faixa[1]):
        texto = linhas[n].strip().lstrip("-* ").strip()
        if texto and not texto.startswith("#"):
            return sem_acento(texto).lower(), n + 1
    return "", faixa[0]


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
    supera: dict[int, tuple[int, Path, int]] = {}

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

        if status.startswith("superado por"):
            m = RE_SUPERADO.search(status)
            if not m:
                res.erro(
                    caminho, linha_status, "A3",
                    "status 'Superado por' sem numero de ADR que o supera",
                )
            else:
                supera[num] = (int(m.group(1)), caminho, linha_status)

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

    # A3 — referencia pendurada
    for origem, (destino, caminho, linha) in supera.items():
        if destino not in por_numero:
            res.erro(
                caminho, linha, "A3",
                f"ADR-{origem:03d} diz ser superado por ADR-{destino:03d}, que nao existe",
            )

    # A4 — ciclo de supersecao
    for inicio in supera:
        visto, atual = set(), inicio
        while atual in supera:
            if atual in visto:
                caminho, linha = supera[inicio][1], supera[inicio][2]
                ciclo = " → ".join(f"ADR-{n:03d}" for n in sorted(visto))
                res.erro(caminho, linha, "A4", f"ciclo de supersecao detectado: {ciclo}")
                break
            visto.add(atual)
            atual = supera[atual][0]

    return relatar("adr-governance", res, PROTOCOLO, args.quiet)


if __name__ == "__main__":
    sys.exit(main())
