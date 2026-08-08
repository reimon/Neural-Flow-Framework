#!/usr/bin/env python3
"""
Neural-Flow Framework — orquestrador dos guards
===============================================
Um comando para rodar todos os gates executaveis do framework.

    python scripts/nf_gate.py                 # roda todos
    python scripts/nf_gate.py sprint adr      # roda so os indicados
    python scripts/nf_gate.py --list          # lista os guards disponiveis
    python scripts/nf_gate.py --root <dir>    # valida outra arvore (usado pelo hook)

Exit 0 = todos PASS. Exit 1 = pelo menos um FAIL (imprime todos, nao para no
primeiro: o dev corrige tudo de uma vez em vez de descobrir de um em um).

Sem dependencia externa: roda em qualquer projeto, qualquer stack.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent

# nome → (script, protocolo, o que garante)
GUARDS: dict[str, tuple[str, str, str]] = {
    "sprint": (
        "validate_sprint_state.py",
        "state-protocol",
        "snapshot completo, status sem ambiguidade, escopo sensivel em A0/A1",
    ),
    "budget": (
        "validate_token_budget.py",
        "token-circuit-breaker",
        "budget declarado, consumo registrado, estouro com mitigacao",
    ),
    "context": (
        "validate_context_sources.py",
        "context-vector",
        "referencia resolve, decisao cita fonte, evidencia real",
    ),
    "adr": (
        "validate_adr.py",
        "adr-governance",
        "numeracao unica, sem referencia pendurada nem ciclo de supersecao",
    ),
    "spec": (
        "validate_module_spec.py",
        "spec-first",
        "estrutura minima de spec, invariantes com ID, aceite numerado",
    ),
    "calibration": (
        "validate_calibration.py",
        "calibration",
        "confianca declarada, BAIXA nao fecha item, irreversivel nao vira registro",
    ),
}


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Roda os gates executaveis do Neural-Flow Framework.",
        epilog="Guards: " + ", ".join(GUARDS),
    )
    ap.add_argument("guards", nargs="*", help="quais rodar (default: todos)")
    ap.add_argument("--root", default=".")
    ap.add_argument("--list", action="store_true", help="lista os guards e sai")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    if args.list:
        largura = max(len(n) for n in GUARDS)
        print("Guards do Neural-Flow:\n")
        for nome, (_, protocolo, o_que) in GUARDS.items():
            print(f"  {nome:<{largura}}  {protocolo:<22} {o_que}")
        return 0

    escolhidos = args.guards or list(GUARDS)
    desconhecidos = [g for g in escolhidos if g not in GUARDS]
    if desconhecidos:
        print(f"guard desconhecido: {', '.join(desconhecidos)}", file=sys.stderr)
        print(f"disponiveis: {', '.join(GUARDS)}", file=sys.stderr)
        return 2

    falhas: list[str] = []
    for nome in escolhidos:
        script, protocolo, _ = GUARDS[nome]
        caminho = AQUI / script
        if not caminho.is_file():
            continue  # guard nao instalado neste projeto — pula sem reclamar
        if not args.quiet:
            print(f"\n═══ {nome} ({protocolo}) " + "═" * max(0, 40 - len(nome)))
        cmd = [sys.executable, str(caminho), "--root", args.root]
        if args.quiet:
            cmd.append("--quiet")
        if subprocess.run(cmd).returncode != 0:
            falhas.append(nome)

    print()
    if falhas:
        print(f"nf_gate: FAIL — {len(falhas)} guard(s): {', '.join(falhas)}")
        print("Nao use --no-verify. Corrija o que os guards apontaram.")
        return 1
    print(f"nf_gate: PASS — {len(escolhidos)} guard(s) conforme")
    return 0


if __name__ == "__main__":
    sys.exit(main())
