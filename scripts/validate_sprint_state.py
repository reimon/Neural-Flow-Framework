#!/usr/bin/env python3
"""
Guard do State Protocol — `docs/protocols/state-protocol.md`
===========================================================
Nenhuma execucao tecnica comeca sem estado de sprint validado. Este guard torna
isso verificavel em vez de declaratorio.

  S1  Snapshot operacional com todos os campos obrigatorios preenchidos.
  S2  Status pertence ao conjunto permitido (status ambiguo e FAIL).
  S3  Nivel de autonomia declarado e valido (A0-A3).
  S4  Escopo sensivel (auth, segredo, infra, billing, dados pessoais, producao)
      exige A0/A1 — regra de seguranca do manifesto. A2/A3 so com excecao formal.
  S5  "Escopo incluido" e "Fora do escopo" preenchidos (escopo sem fronteira
      explicita e escopo que o agente amplia sozinho).
  S6  Checklist de acoes numerado existe; sprint concluida nao tem item aberto.

Uso:
  python scripts/validate_sprint_state.py
  python scripts/validate_sprint_state.py --root <dir> --glob 'docs/sprints/*.md'
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nf_guards import (  # noqa: E402
    Resultado, arquivos, campos, chave, eh_placeholder, eh_template, ler,
    relatar, secao, sem_acento,
)

PROTOCOLO = "docs/protocols/state-protocol.md"

CAMPOS_SNAPSHOT = {
    "app/escopo": "App/Escopo",
    "status": "Status",
    "data de inicio": "Data de inicio",
    "data planejada de conclusao": "Data planejada de conclusao",
    "ultima atualizacao": "Ultima atualizacao",
    "nivel de autonomia": "Nivel de autonomia",
    "blocker principal": "Blocker principal",
    "proxima acao": "Proxima acao",
}

STATUS_VALIDOS = {"planejada", "em andamento", "bloqueada", "concluida", "cancelada"}

# Valores que significam "campo presente, mas sem conteudo real".
NEGATIVOS = {"nao", "nao se aplica", "nenhuma", "nenhum", "n/a", "-"}

# Escopo que o manifesto obriga a operar em A0/A1.
TERMOS_SENSIVEIS = (
    "auth", "autenticacao", "login", "sso", "oauth", "jwt",
    "segredo", "secret", "credencial", "chave de api", "key vault",
    "infra", "terraform", "kubernetes", "deploy em producao", "producao",
    "billing", "cobranca", "pagamento", "faturamento",
    "dado pessoal", "dados pessoais", "lgpd", "pii",
    "integracao externa",
)

RE_ITEM_CHECKLIST = re.compile(r"^\s*[-*]\s*\[(?P<marca>[ xX])\]\s*(?P<num>\d+(\.\d+)*)\s")


def validar(caminho: Path, res: Resultado) -> None:
    linhas = ler(caminho)
    if linhas is None or eh_template(linhas):
        return
    res.verificado(caminho)

    faixa = secao(linhas, "Snapshot Operacional")
    if faixa is None:
        res.erro(caminho, 1, "S1", "sprint sem secao 'Snapshot Operacional'")
        return
    snap = campos(linhas, *faixa)

    # S1 — campos obrigatorios preenchidos
    for k, rotulo in CAMPOS_SNAPSHOT.items():
        valor = snap.get(k)
        if valor is None:
            res.erro(caminho, faixa[0], "S1", f"snapshot sem o campo '{rotulo}'")
        elif eh_placeholder(valor):
            res.erro(caminho, faixa[0], "S1", f"campo '{rotulo}' nao preenchido ({valor!r})")

    # S2 — status sem ambiguidade
    status = chave(snap.get("status", "").strip("`"))
    if status and not eh_placeholder(status):
        if status not in STATUS_VALIDOS:
            res.erro(
                caminho, faixa[0], "S2",
                f"status '{status}' fora do conjunto permitido "
                f"({', '.join(sorted(STATUS_VALIDOS))})",
            )

    # S3 — nivel de autonomia valido
    bruto_aut = snap.get("nivel de autonomia", "")
    m_aut = re.search(r"\bA([0-3])\b", sem_acento(bruto_aut).upper())
    nivel = int(m_aut.group(1)) if m_aut else None
    if bruto_aut and not eh_placeholder(bruto_aut) and nivel is None:
        res.erro(
            caminho, faixa[0], "S3",
            f"nivel de autonomia '{bruto_aut}' invalido — use A0, A1, A2 ou A3",
        )

    # S4 — escopo sensivel exige A0/A1
    corpo = sem_acento("\n".join(linhas)).lower()
    achados = sorted({t for t in TERMOS_SENSIVEIS if t in corpo})

    # A excecao precisa ser um CAMPO preenchido, nunca a mencao da palavra no
    # texto. Procurar a substring em qualquer lugar do documento fazia com que a
    # propria nota explicativa do template ("...so com Excecao formal registrada")
    # desligasse o guard — o template desativava a regra que ele descreve.
    todos = campos(linhas)
    excecao = todos.get("excecao formal") or todos.get("excecao")
    tem_excecao = (
        excecao is not None
        and not eh_placeholder(excecao)
        and chave(excecao.strip("`*")) not in NEGATIVOS
    )
    if achados and nivel is not None and nivel >= 2 and not tem_excecao:
        res.erro(
            caminho, faixa[0], "S4",
            f"escopo sensivel ({', '.join(achados[:3])}) operando em A{nivel} — "
            "manifesto exige A0/A1, salvo excecao formal registrada",
        )

    # S5 — fronteira de escopo explicita
    for titulo in ("Escopo incluido", "Fora do escopo"):
        faixa_sec = secao(linhas, titulo)
        if faixa_sec is None:
            res.erro(caminho, None, "S5", f"sprint sem secao '{titulo}'")
            continue
        conteudo = [
            l for l in linhas[faixa_sec[0]:faixa_sec[1]]
            if l.strip() and not eh_placeholder(l.strip().lstrip("-* "))
            and l.strip().lstrip("-* ").lower() not in {"item 1", "item 2"}
        ]
        if not conteudo:
            res.erro(caminho, faixa_sec[0], "S5", f"secao '{titulo}' vazia ou so com exemplo")

    # S6 — checklist numerado; concluida nao pode ter item aberto
    itens = [
        (n, m) for n, l in enumerate(linhas, 1)
        if (m := RE_ITEM_CHECKLIST.match(l))
    ]
    if not itens:
        res.erro(caminho, None, "S6", "sprint sem checklist de acoes numerado")
    elif status == "concluida":
        abertos = [f"{m.group('num')}" for _, m in itens if m.group("marca").strip() == ""]
        if abertos:
            res.erro(
                caminho, None, "S6",
                f"sprint marcada 'concluida' com {len(abertos)} item(ns) aberto(s): "
                f"{', '.join(abertos[:5])}",
            )


def main() -> int:
    ap = argparse.ArgumentParser(description="Guard do State Protocol (Neural-Flow).")
    ap.add_argument("--root", default=".")
    ap.add_argument(
        "--glob", action="append",
        help="glob dos arquivos de sprint (repetivel). Default: locais usuais.",
    )
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    raiz = Path(args.root).resolve()
    padroes = args.glob or [
        "docs/sprints/*.md", "sprints/*.md",
        "apps/*/sprints/*.md", "docs/sessoes/sprints/*.md",
    ]

    res = Resultado()
    for caminho in arquivos(raiz, *padroes):
        validar(caminho, res)
    return relatar("state-protocol", res, PROTOCOLO, args.quiet)


if __name__ == "__main__":
    sys.exit(main())
