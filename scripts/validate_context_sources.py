#!/usr/bin/env python3
"""
Guard do Vetor de Contexto — `docs/protocols/context-vector.md`
==============================================================
"Toda decisao tecnica relevante deve estar ancorada em pelo menos uma fonte de
contexto verificavel." Verificavel quer dizer: a fonte existe. Este guard checa
justamente isso — referencia pendurada e a forma mais comum de decisao sem base
documental sobreviver a revisao.

  V1  Toda referencia a arquivo do repositorio aponta para arquivo existente.
  V2  Decisao registrada (ADR / secao 'Decisoes') cita ao menos uma fonte.
  V3  Sprint concluida registra evidencias apontando para artefatos reais.

Referencias externas (http, mailto) e placeholders de template sao ignorados —
o guard so cobra o que ele pode verificar.

Uso:
  python scripts/validate_context_sources.py
  python scripts/validate_context_sources.py --root <dir>
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
    Resultado, arquivos, chave, eh_placeholder, eh_template, ler, relatar,
    secao, sem_acento,
)

PROTOCOLO = "docs/protocols/context-vector.md"

# `caminho/arquivo.md` ou `dir/**` em backticks, e links markdown [x](caminho)
RE_CRASE = re.compile(r"`([^`\n]+?)`")
RE_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+?)\)")

# Parece caminho de arquivo do repo (tem barra ou extensao conhecida)
RE_PARECE_CAMINHO = re.compile(
    r"^[\w./@-]+(?:/[\w./@-]+)*\.(md|py|ts|tsx|js|jsx|sql|ya?ml|json|tf|sh|toml|txt)$"
)

IGNORAR_PREFIXO = ("http://", "https://", "mailto:", "#", "$", "npm ", "python ", "git ")


def candidatos(linha: str) -> list[str]:
    achados = RE_CRASE.findall(linha) + RE_LINK.findall(linha)
    saida = []
    for bruto in achados:
        alvo = bruto.strip().split("#")[0].strip()
        if not alvo or alvo.startswith(IGNORAR_PREFIXO):
            continue
        if any(c in alvo for c in " |<>*"):
            continue
        if eh_placeholder(alvo) or not RE_PARECE_CAMINHO.match(alvo):
            continue
        saida.append(alvo)
    return saida


def resolve(raiz: Path, origem: Path, alvo: str) -> bool:
    for base in (origem.parent, raiz):
        try:
            if (base / alvo).resolve().is_file():
                return True
        except (OSError, ValueError):
            continue
    # glob relativo ao repo (ex: docs/protocols/*.md)
    if any(c in alvo for c in "*?"):
        return bool(list(raiz.glob(alvo)))
    return False


def eh_prospectivo(raiz: Path, origem: Path, alvo: str) -> bool:
    """
    Caminho ilustrativo — o que o projeto ADOTANTE tera, nao o que este repo tem.

    Regra: so cobramos referencia cujo diretorio-pai existe. Se nem a pasta existe
    aqui (`build/PLANO.md` num repo sem `build/`), a mencao e prospectiva e nao ha
    o que verificar. Nome solto sem diretorio (`MEMORY.md`) tambem e generico.
    """
    if "/" not in alvo:
        return True
    for base in (origem.parent, raiz):
        try:
            if (base / alvo).parent.resolve().is_dir():
                return False
        except (OSError, ValueError):
            continue
    return True


def validar(raiz: Path, caminho: Path, res: Resultado) -> None:
    linhas = ler(caminho)
    if linhas is None or eh_template(linhas):
        return
    res.verificado(caminho)

    # V1 — referencias resolvem
    dentro_de_bloco = False
    for n, linha in enumerate(linhas, 1):
        if linha.lstrip().startswith("```"):
            dentro_de_bloco = not dentro_de_bloco
            continue
        # Bloco de codigo e exemplo; linha de tabela costuma mapear
        # template → destino no projeto adotante. Nem um nem outro e afirmacao
        # sobre este repositorio.
        if dentro_de_bloco or linha.lstrip().startswith("|"):
            continue
        for alvo in candidatos(linha):
            if eh_prospectivo(raiz, caminho, alvo):
                continue
            if not resolve(raiz, caminho, alvo):
                res.erro(
                    caminho, n, "V1",
                    f"referencia pendurada: `{alvo}` nao existe no repositorio",
                )

    corpo = sem_acento("\n".join(linhas)).lower()

    # V2 — documento que registra decisao cita ao menos uma fonte.
    # A ancoragem se avalia no DOCUMENTO, nao dentro da secao "Decisao": num ADR
    # as fontes vivem em Contexto/Evidencia, e exigi-las dentro da decisao gera
    # falso positivo sem tornar decisao nenhuma mais ancorada.
    faixa = secao(linhas, "Decisao") or secao(linhas, "Decisoes")
    if faixa is not None:
        trecho = "\n".join(linhas[faixa[0]:faixa[1]])
        tem_fonte = (
            bool(RE_CRASE.search(corpo_bruto := "\n".join(linhas)))
            or bool(RE_LINK.search(corpo_bruto))
            or "fonte:" in corpo
            or re.search(r"\badr[-_ ]?\d", corpo) is not None
            or re.search(r"\bsprint\s*\d", corpo) is not None
        )
        if not tem_fonte and len(trecho.strip()) > 40:
            res.erro(
                caminho, faixa[0], "V2",
                "documento registra decisao sem citar nenhuma fonte de contexto "
                "(arquivo, ADR, sprint ou 'Fonte:')",
            )

    # V3 — sprint concluida com evidencias reais
    if "status" in corpo and re.search(r"status\s*:\s*`?\s*concluida", corpo):
        faixa_ev = secao(linhas, "Evidencias")
        if faixa_ev is None:
            res.erro(caminho, None, "V3", "sprint concluida sem secao de evidencias")
        else:
            uteis = [
                l for l in linhas[faixa_ev[0]:faixa_ev[1]]
                if l.strip().lstrip("-* ")
                and not eh_placeholder(l.strip().lstrip("-* "))
            ]
            if not uteis:
                res.erro(
                    caminho, faixa_ev[0], "V3",
                    "sprint concluida com secao de evidencias vazia ou so com placeholder",
                )


def main() -> int:
    ap = argparse.ArgumentParser(description="Guard do Vetor de Contexto (Neural-Flow).")
    ap.add_argument("--root", default=".")
    ap.add_argument("--glob", action="append")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    raiz = Path(args.root).resolve()
    padroes = args.glob or [
        "docs/**/*.md", "*.md", "sprints/*.md", "apps/*/sprints/*.md",
    ]

    res = Resultado()
    vistos: set[Path] = set()
    for caminho in arquivos(raiz, *padroes):
        if caminho in vistos or "templates/" in str(caminho.relative_to(raiz)):
            continue
        vistos.add(caminho)
        validar(raiz, caminho, res)
    return relatar("vetor-de-contexto", res, PROTOCOLO, args.quiet)


if __name__ == "__main__":
    sys.exit(main())
