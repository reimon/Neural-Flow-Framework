#!/usr/bin/env python3
"""
Neural-Flow Framework — Guard do Protocolo de Calibracao
========================================================
Torna executavel o protocolo `docs/protocols/calibration.md`. Sem este guard, a
declaracao de confianca depende de disciplina — e o proprio framework diz que
diretriz sem guard nao esta pronta.

Verifica, sobre os arquivos de estado do loop:

  C1  Toda entrada de DIARIO.md declara confianca (ALTA | MEDIA | BAIXA).
  C2  Nenhum item marcado [x] no PLANO.md tem confianca BAIXA no diario.
  C3  Todo item marcado [x] no PLANO.md tem entrada correspondente no diario.
  C4  Toda entrada de DIVERGENCIAS.md tem os campos obrigatorios do protocolo.
  C5  Divergencia irreversivel nao pode estar pendente: BAIXA + irreversivel
      deveria ter parado para pergunta humana, nao virado divergencia.
  C6  Divergencia registrada declara as consultas ao indice tentadas (escada de
      verificacao percorrida antes de desistir).

Uso:
  python scripts/validate_calibration.py                 # valida ./build
  python scripts/validate_calibration.py --root <dir>    # outro projeto
  python scripts/validate_calibration.py --build-dir doc/loop
  python scripts/validate_calibration.py --quiet         # so o resultado

Saida: 0 = PASS (ou nada a validar), 1 = FAIL.
Nao tem dependencia externa — roda em qualquer projeto, qualquer stack.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nf_guards import (  # noqa: E402
    Resultado, eh_placeholder, eh_template, ler, relatar, sem_acento,
)

PROTOCOLO = "docs/protocols/calibration.md"
NIVEIS = ("ALTA", "MEDIA", "BAIXA")

# Campos que o protocolo exige em cada entrada de DIVERGENCIAS.md.
CAMPOS_DIVERGENCIA = {
    "data": "Data",
    "confianca": "Confianca",
    "decisao tomada para seguir": "Decisao tomada para seguir",
    "reversivel": "Reversivel?",
}


# ── Parsing ────────────────────────────────────────────────────────────────────

# "- [x] **E1 — Scaffold do projeto.**"  →  id E1
RE_ITEM_PLANO = re.compile(
    r"^\s*[-*]\s*\[(?P<marca>[ xX])\]\s*\**\s*(?P<id>[A-Z]+[-_]?\d+)\b"
)
# "- E1 — fez X — verificar: verde — confianca: ALTA — proxima precisa de Y"
RE_ENTRADA_DIARIO = re.compile(r"^\s*[-*]\s+(?P<id>[A-Z]+[-_]?\d+)\b")
RE_CONFIANCA = re.compile(
    r"confianca\s*[:=]\s*\**\s*(?P<nivel>ALTA|MEDIA|BAIXA)\b", re.IGNORECASE
)
RE_TITULO_DIVERGENCIA = re.compile(r"^\s*##\s+(?P<titulo>.+?)\s*$")
RE_CAMPO = re.compile(r"^\s*[-*]\s*\*\*(?P<campo>[^:*]+?)\s*:?\*\*\s*:?\s*(?P<valor>.*)$")

# ── Verificacoes ───────────────────────────────────────────────────────────────


def itens_concluidos(plano: Path, res: Resultado) -> dict[str, int]:
    """IDs marcados [x] no PLANO.md → numero da linha."""
    linhas = ler(plano)
    if linhas is None or eh_template(linhas):
        return {}
    res.verificados.append(str(plano))
    concluidos: dict[str, int] = {}
    for n, linha in enumerate(linhas, 1):
        m = RE_ITEM_PLANO.match(linha)
        if m and m.group("marca").lower() == "x":
            concluidos[m.group("id").upper()] = n
    return concluidos


def checar_diario(diario: Path, concluidos: dict[str, int], res: Resultado) -> None:
    linhas = ler(diario)
    if linhas is None:
        if concluidos:
            res.erro(
                diario, None, "C3",
                f"{len(concluidos)} item(ns) concluido(s) no PLANO.md e nenhum DIARIO.md",
            )
        return
    if eh_template(linhas):
        return
    res.verificados.append(str(diario))

    vistos: dict[str, str] = {}
    for n, linha in enumerate(linhas, 1):
        m = RE_ENTRADA_DIARIO.match(linha)
        if not m:
            continue
        item_id = m.group("id").upper()
        normal = sem_acento(linha)
        conf = RE_CONFIANCA.search(normal)

        if not conf:
            # C1 — entrada sem confianca declarada. O protocolo manda tratar como BAIXA.
            res.erro(
                diario, n, "C1",
                f"entrada '{item_id}' sem confianca declarada "
                "(protocolo trata ausencia como BAIXA)",
            )
            vistos[item_id] = "BAIXA"
            continue

        nivel = conf.group("nivel").upper()
        vistos[item_id] = nivel

        # C2 — item concluido nunca fecha com BAIXA.
        if nivel == "BAIXA" and item_id in concluidos:
            res.erro(
                diario, n, "C2",
                f"item '{item_id}' marcado [x] no PLANO.md (linha "
                f"{concluidos[item_id]}) com confianca BAIXA — "
                "BAIXA nunca fecha item; registre divergencia ou suba a evidencia",
            )

    # C3 — concluido sem rastro no diario.
    for item_id, linha_plano in sorted(concluidos.items()):
        if item_id not in vistos:
            res.erro(
                diario, None, "C3",
                f"item '{item_id}' marcado [x] no PLANO.md (linha {linha_plano}) "
                "sem entrada correspondente no diario",
            )


def checar_divergencias(divergencias: Path, res: Resultado) -> None:
    linhas = ler(divergencias)
    if linhas is None or eh_template(linhas):
        return
    res.verificados.append(str(divergencias))

    atual: str | None = None
    linha_titulo = 0
    campos: dict[str, str] = {}

    def fechar() -> None:
        if atual is None:
            return
        # C4 — campos obrigatorios preenchidos.
        for chave, rotulo in CAMPOS_DIVERGENCIA.items():
            valor = campos.get(chave)
            if valor is None:
                res.erro(
                    divergencias, linha_titulo, "C4",
                    f"divergencia '{atual}' sem o campo obrigatorio '{rotulo}'",
                )
            elif eh_placeholder(valor):
                res.erro(
                    divergencias, linha_titulo, "C4",
                    f"divergencia '{atual}': campo '{rotulo}' nao preenchido",
                )

        # C5 — irreversivel nao vira divergencia: vira pergunta ao humano.
        reversivel = sem_acento(campos.get("reversivel", "")).lower()
        status = sem_acento(campos.get("status", "")).lower()
        if reversivel.startswith("nao"):
            if "confirmada" not in status:
                res.erro(
                    divergencias, linha_titulo, "C5",
                    f"divergencia '{atual}' e irreversivel e nao esta confirmada por "
                    "humano — decisao irreversivel sob incerteza exige aprovacao "
                    "explicita, nao registro autonomo",
                )

        # C6 — escada de verificacao percorrida antes de desistir.
        consultas = campos.get("consultas ao indice tentadas")
        if consultas is None or eh_placeholder(consultas):
            res.erro(
                divergencias, linha_titulo, "C6",
                f"divergencia '{atual}' sem 'Consultas ao indice tentadas' — "
                "registre as reformulacoes feitas antes de assumir a lacuna",
            )

    for n, linha in enumerate(linhas, 1):
        titulo = RE_TITULO_DIVERGENCIA.match(linha)
        if titulo:
            fechar()
            atual = titulo.group("titulo")
            linha_titulo = n
            campos = {}
            continue
        campo = RE_CAMPO.match(linha)
        if campo and atual is not None:
            chave = sem_acento(campo.group("campo")).strip().lower().rstrip("?:")
            campos[chave] = campo.group("valor").strip()
    fechar()


# ── CLI ────────────────────────────────────────────────────────────────────────


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Guard do Protocolo de Calibracao (Neural-Flow Framework)."
    )
    ap.add_argument("--root", default=".", help="raiz do projeto (default: .)")
    ap.add_argument(
        "--build-dir",
        default="build",
        help="diretorio de estado do loop (default: build)",
    )
    ap.add_argument("--quiet", action="store_true", help="imprime apenas o resultado")
    args = ap.parse_args()

    raiz = Path(args.root).resolve()
    build = raiz / args.build_dir

    res = Resultado()
    plano = build / "PLANO.md"
    concluidos = itens_concluidos(plano, res)
    checar_diario(build / "DIARIO.md", concluidos, res)
    checar_divergencias(build / "DIVERGENCIAS.md", res)

    if not res.verificados:
        if not args.quiet:
            print(
                f"calibracao: nada a validar em {build} "
                "(sem arquivos de loop preenchidos) — OK"
            )
        return 0

    if not args.quiet:
        for caminho in res.verificados:
            print(f"  verificado: {caminho}")

    if res.erros:
        print(f"\ncalibracao: FAIL — {len(res.erros)} violacao(oes)\n")
        for erro in res.erros:
            print(f"  {erro}")
        print("\nProtocolo: docs/protocols/calibration.md")
        return 1

    print(f"\ncalibracao: PASS — {len(concluidos)} item(ns) concluido(s) com evidencia")
    return 0


if __name__ == "__main__":
    sys.exit(main())
