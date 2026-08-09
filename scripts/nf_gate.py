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

# Assinatura de origem. O `nf_gate` so executa arquivo que a carrega — projeto
# brownfield pode ter um script homonimo com outra interface, e chama-lo com os
# nossos argumentos produz erro de uso confuso em vez de diagnostico.
NF_GUARD_ASSINATURA = "neural-flow-framework"

import argparse
import json
import re
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


def config(raiz: Path) -> dict:
    caminho = raiz / ".neural-flow.json"
    if caminho.is_file():
        try:
            return json.loads(caminho.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"aviso: .neural-flow.json invalido ({exc})", file=sys.stderr)
    return {}


def eh_nosso(script: Path) -> bool:
    """Projeto brownfield pode ter script homonimo com outra interface.

    Chamar o validador do projeto com os nossos argumentos produz um erro de uso
    ("the following arguments are required: --module") que parece defeito do
    framework — quando na verdade sao duas ferramentas diferentes com o mesmo
    nome. A assinatura resolve isso antes de executar qualquer coisa.
    """
    try:
        return "NF_GUARD_ASSINATURA" in script.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False


def resolver(raiz: Path, script: str) -> tuple[Path | None, bool]:
    """Devolve (caminho, e_nosso). Procura o nome namespaced antes do simples:
    quando ha colisao, o instalador grava o nosso como `nf_<nome>`."""
    for nome in (f"nf_{script}", script):
        candidato = raiz / "scripts" / nome
        if candidato.is_file():
            return candidato, eh_nosso(candidato)
    proprio = AQUI / script
    if proprio.is_file():
        return proprio, True
    return None, False


def rodar_externo(raiz: Path, nome: str, cfg: dict, quiet: bool) -> int | None:
    """Executa o validador do proprio projeto, conforme configurado.

    `por_modulo` cobre o caso comum de validador que roda um modulo por vez:
    o gate descobre os diretorios e itera, em vez de exigir que o time troque a
    interface da ferramenta que ja tem.
    """
    spec = (cfg.get("guards") or {}).get(nome) or {}
    comando = spec.get("comando")
    if not comando:
        return None
    padrao = spec.get("por_modulo")
    alvos = []
    if padrao:
        for caminho in sorted(raiz.glob(padrao)):
            m = re.search(r"(\d{1,3})", caminho.name)
            if m:
                alvos.append(m.group(1))
        if not alvos:
            if not quiet:
                print(f"  nenhum modulo casou com {padrao}")
            return 0
    else:
        alvos = [None]

    falhou = 0
    for alvo in alvos:
        cmd = [str(raiz) if a == "{root}" else
               (alvo if a == "{modulo}" else a.replace("{root}", str(raiz)))
               for a in comando]
        proc = subprocess.run(cmd, cwd=raiz, capture_output=quiet, text=True)
        if proc.returncode != 0:
            falhou += 1
            if quiet and proc.stdout:
                print(proc.stdout.rstrip())
    if falhou and not quiet:
        print(f"  {falhou} modulo(s) reprovado(s)")
    return 1 if falhou else 0


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

    raiz = Path(args.root).resolve()
    cfg = config(raiz)

    falhas: list[str] = []
    externos: list[str] = []
    for nome in escolhidos:
        script, protocolo, _ = GUARDS[nome]
        caminho, nosso = resolver(raiz, script)
        if caminho is None:
            continue  # guard nao instalado neste projeto — pula sem reclamar
        if not args.quiet:
            print(f"\n═══ {nome} ({protocolo}) " + "═" * max(0, 40 - len(nome)))

        if not nosso:
            # Script do proprio projeto com o mesmo nome. So executamos se o time
            # disser COMO — a interface e dele, nao nossa.
            codigo = rodar_externo(raiz, nome, cfg, args.quiet)
            if codigo is None:
                externos.append(nome)
                print(f"  externo: '{caminho.name}' e do projeto, nao do framework "
                      f"(sem a assinatura de origem).")
                print(f"  O gate nao adivinha a interface dele. Configure em "
                      f".neural-flow.json:")
                print(f'    {{"guards": {{"{nome}": {{"comando": ["python3", '
                      f'"{caminho.relative_to(raiz) if caminho.is_relative_to(raiz) else caminho}", '
                      f'"--root", "{{root}}"]}}}}}}')
                print(f"  Use \"por_modulo\": \"docs/modulos/*\" e \"{{modulo}}\" "
                      f"se ele roda um modulo por vez.")
                continue
            if codigo != 0:
                falhas.append(nome)
            continue

        cmd = [sys.executable, str(caminho), "--root", args.root]
        if args.quiet:
            cmd.append("--quiet")
        if subprocess.run(cmd).returncode != 0:
            falhas.append(nome)

    print()
    if externos:
        print(f"nf_gate: {len(externos)} guard(s) com validador proprio do projeto, "
              f"nao executado(s): {', '.join(externos)}")
    if falhas:
        print(f"nf_gate: FAIL — {len(falhas)} guard(s): {', '.join(falhas)}")
        print("Nao use --no-verify. Corrija o que os guards apontaram.")
        return 1
    print(f"nf_gate: PASS — {len(escolhidos)} guard(s) conforme")
    return 0


if __name__ == "__main__":
    sys.exit(main())
