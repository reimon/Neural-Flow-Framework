#!/usr/bin/env python3
"""
Guard das portas de entrada de agente — `docs/protocols/agent-entrypoints.md`
=============================================================================
"Documentacao orienta, guard obriga" vale tambem para a propria governanca. De
nada adianta `AGENTS.md` ser a fonte de verdade se o Gemini, o Copilot, o Cursor
e o Cline nunca sao mandados ate la: cada ferramenta le um arquivo diferente, e
o que nao tem porta de entrada opera sem diretriz nenhuma.

  P1  Toda porta de entrada conhecida existe.
  P2  A porta carrega o corpo canonico da versao corrente (nao divergiu nem
      envelheceu em relacao a `nf_agentes.py`).
  P3  Os arquivos que o corpo cita existem — porta que aponta para arquivo
      inexistente e pior que porta nenhuma.
  P4  As ancoras (`CLAUDE.md`) apontam para a fonte de verdade.
  P5  O indice de regras existe e esta em dia com as fontes.

Ausencia de `AGENTS.md` = projeto sem governanca instalada = nada a validar
(exit 0), como nos demais guards do framework.

Uso:
  python scripts/validate_agent_entrypoints.py
  python scripts/validate_agent_entrypoints.py --root <dir> --quiet
"""

from __future__ import annotations

# Assinatura de origem. O `nf_gate` so executa arquivo que a carrega — projeto
# brownfield pode ter um script homonimo com outra interface, e chama-lo com os
# nossos argumentos produz erro de uso confuso em vez de diagnostico.
NF_GUARD_ASSINATURA = "neural-flow-framework"

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nf_agentes import (  # noqa: E402
    ANCORAS, INDICE_MD, MARCA, PORTAS, REFERENCIAS, REGERAR, VERSAO, corpo,
)
from nf_guards import Resultado, eh_template, ler, relatar  # noqa: E402

PROTOCOLO = "docs/protocols/agent-entrypoints.md"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Guard das portas de entrada de agente (Neural-Flow)."
    )
    ap.add_argument("--root", default=".")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    raiz = Path(args.root).resolve()
    res = Resultado()

    fonte = raiz / "AGENTS.md"
    linhas_fonte = ler(fonte)
    if linhas_fonte is None or eh_template(linhas_fonte):
        # Sem fonte de verdade nao ha o que apontar. Nao e violacao: e projeto
        # que ainda nao instalou a governanca (ou o proprio repositorio do
        # framework, onde `AGENTS.md` vive como template).
        return relatar("agent-entrypoints", res, PROTOCOLO, args.quiet)

    esperado = corpo()

    # P1 + P2
    for porta in PORTAS:
        caminho = raiz / porta.caminho
        res.verificado(porta.caminho)
        linhas = ler(caminho)
        if linhas is None:
            res.erro(
                porta.caminho, None, "P1",
                f"porta de entrada ausente — {porta.ferramenta} roda sem diretriz "
                f"neste projeto. Regere com `{REGERAR}`",
            )
            continue
        texto = "\n".join(linhas)
        if esperado.strip() not in texto:
            if MARCA in texto:
                motivo = "conteudo divergente do corpo canonico"
            elif "neural-flow:entrypoint" in texto:
                motivo = f"corpo de versao anterior — a corrente e v{VERSAO}"
            else:
                motivo = "arquivo nao carrega o corpo canonico do Neural-Flow"
            res.erro(
                porta.caminho, 1, "P2",
                f"{motivo}. Nao edite a porta: edite `AGENTS.md` e regere com "
                f"`{REGERAR}`",
            )

    # P3 — o corpo so serve se os destinos existirem
    for referencia in REFERENCIAS:
        if not (raiz / referencia).is_file():
            res.erro(
                referencia, None, "P3",
                "as portas de entrada mandam o agente para este arquivo, que nao existe",
            )

    # P4 — ancora nao repete o corpo, mas nao pode ser ilha
    for ancora in ANCORAS:
        linhas = ler(raiz / ancora)
        if linhas is None:
            continue
        res.verificado(ancora)
        if "AGENTS.md" not in "\n".join(linhas):
            res.erro(
                ancora, 1, "P4",
                "nao aponta para `AGENTS.md` — a fonte de verdade fica invisivel "
                "para quem entra por aqui",
            )

    # P5 — indice de regras
    try:
        from nf_indice_regras import desatualizado
    except ImportError:
        desatualizado = None  # type: ignore[assignment]
    if desatualizado is not None:
        motivo = desatualizado(raiz)
        if motivo:
            res.erro(
                INDICE_MD, None, "P5",
                f"{motivo} — regere com `python3 scripts/nf_indice_regras.py`",
            )
        else:
            res.verificado(INDICE_MD)

    return relatar("agent-entrypoints", res, PROTOCOLO, args.quiet)


if __name__ == "__main__":
    sys.exit(main())
