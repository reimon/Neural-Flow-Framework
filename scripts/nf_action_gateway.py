#!/usr/bin/env python3
"""
Neural-Flow Framework — fronteira de execucao do agente
========================================================
Executa somente acoes declaradas na politica. Acoes sensiveis ou irreversiveis
param e pedem confirmacao TTY para o comando exato.
"""

from __future__ import annotations

NF_GUARD_ASSINATURA = "neural-flow-framework"

import argparse
import datetime as dt
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nf_action_policy import (  # noqa: E402
    action_by_id,
    command_hash,
    command_matches,
    file_hash,
    load_policy,
    normalizar_status,
    policy_path,
    sprint_fields,
)
from nf_sandbox import command_for  # noqa: E402

SAFE_STATUS = "em andamento"
EXIT_POLICY = 2
EXIT_APPROVAL = 3
EXIT_TIMEOUT = 124


def erro(msg: str, codigo: int = EXIT_POLICY) -> int:
    print(f"nf_action_gateway: BLOQUEADO — {msg}", file=sys.stderr)
    return codigo


def redacted_command(command: list[str]) -> str:
    palavras = ("password", "secret", "token", "api_key", "apikey", "credential")
    exibido: list[str] = []
    for token in command:
        minusculo = token.lower()
        exibido.append("<redacted>" if any(palavra in minusculo for palavra in palavras) else token)
    return shlex.join(exibido)


def validar_sprint(root: Path, sprint: str) -> tuple[int, str, int | None]:
    caminho = root / sprint
    if not caminho.is_file():
        return EXIT_POLICY, f"sprint nao existe: {sprint}", None
    script = root / "scripts" / "validate_sprint_state.py"
    if not script.is_file():
        return EXIT_POLICY, "validate_sprint_state.py ausente", None
    proc = subprocess.run(
        [sys.executable, str(script), "--root", str(root), "--glob", sprint, "--quiet"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        saida = (proc.stdout or proc.stderr).strip().replace("\n", " ")
        return EXIT_POLICY, f"sprint reprovada pelo State Protocol: {saida}", None
    fields, _ = sprint_fields(caminho)
    status = normalizar_status(fields.get("status", ""))
    if status != SAFE_STATUS:
        return EXIT_POLICY, f"sprint nao esta em andamento: {status or 'ausente'}", None
    bruto = fields.get("nivel de autonomia", "").upper()
    encontrado = re.search(r"\bA([0-3])\b", bruto)
    nivel = int(encontrado.group(1)) if encontrado else None
    if nivel is None:
        return EXIT_POLICY, "sprint sem nivel de autonomia valido", None
    return 0, "", nivel


def audit(root: Path, policy: dict, evento: dict) -> tuple[bool, str]:
    caminho = root / str(policy.get("audit_path", ""))
    try:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        with caminho.open("a", encoding="utf-8") as arquivo:
            arquivo.write(json.dumps(evento, ensure_ascii=False, sort_keys=True) + "\n")
    except OSError as exc:
        return False, f"nao foi possivel escrever auditoria: {exc}"
    return True, ""


def main() -> int:
    ap = argparse.ArgumentParser(description="Executa uma acao pela politica Neural-Flow.")
    ap.add_argument("--root", default=".")
    ap.add_argument("--action", required=True)
    ap.add_argument("--sprint", required=True)
    ap.add_argument("--plan", action="store_true", help="valida sem executar")
    ap.add_argument("command", nargs=argparse.REMAINDER)
    args = ap.parse_args()
    root = Path(args.root).resolve()
    command = list(args.command)
    if command[:1] == ["--"]:
        command = command[1:]
    if not command:
        return erro("comando ausente depois de --")

    policy, policy_error = load_policy(root)
    if policy_error:
        return erro(policy_error)
    if policy is None:
        return erro("action-policy.json ausente")
    if policy.get("enabled") is not True:
        return erro("politica desabilitada; nenhuma acao pode executar")

    # O executor fecha o circuito com o guard. Assim, uma politica que foi
    # alterada depois da ultima validacao nao ganha uma brecha por ser chamada
    # diretamente, fora do nf_gate.
    validator = root / "scripts" / "validate_action_policy.py"
    if not validator.is_file():
        return erro("validate_action_policy.py ausente")
    validacao = subprocess.run(
        [sys.executable, str(validator), "--root", str(root), "--quiet"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if validacao.returncode != 0:
        detalhe = (validacao.stdout or validacao.stderr).strip().replace("\n", " ")
        return erro(f"politica reprovada pelo guard: {detalhe}")

    action = action_by_id(policy, args.action)
    if action is None:
        return erro(f"acao desconhecida: {args.action}")
    if action.get("sprint") != args.sprint:
        return erro("acao nao pertence a sprint informada")
    prefix = action.get("argv_prefix")
    if not isinstance(prefix, list) or not command_matches(prefix, command):
        return erro("comando nao corresponde ao argv_prefix permitido para a acao")

    status, motivo, nivel = validar_sprint(root, args.sprint)
    if status:
        return erro(motivo, status)
    risco = action.get("risk")
    if risco in {"sensitive", "irreversible"} and (nivel is None or nivel > 1):
        return erro(f"acao {risco} exige sprint A0/A1; sprint atual e A{nivel}")

    politica_hash = file_hash(policy_path(root))
    desafio = command_hash(args.action, args.sprint, command, policy)[:16]
    resumo = {
        "action_id": args.action,
        "item": action.get("item"),
        "risk": risco,
        "sprint": args.sprint,
        "command_hash": desafio,
    }
    if args.plan:
        print("nf_action_gateway: ALLOW-PLAN")
        print(json.dumps(resumo, ensure_ascii=False, sort_keys=True))
        return 0

    aprovado = risco == "safe"
    if risco in {"sensitive", "irreversible"}:
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            audit(root, policy, {
                "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
                "action_id": args.action,
                "sprint": args.sprint,
                "item": action.get("item"),
                "risk": risco,
                "decision": "denied",
                "reason": "interactive_tty_required",
                "command_hash": desafio,
                "policy_hash": politica_hash,
            })
            return erro("aprovacao humana exige terminal interativo (TTY)", EXIT_APPROVAL)
        print("Acao de risco elevado detectada.")
        print(f"Descricao: {action.get('description')}")
        print(f"Comando: {redacted_command(command)}")
        print(f"Desafio: APROVAR {desafio}")
        try:
            resposta = input("Digite o desafio exato para continuar: ").strip()
        except (EOFError, KeyboardInterrupt):
            resposta = ""
        aprovado = resposta == f"APROVAR {desafio}"
        if not aprovado:
            evento = {
                "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
                "action_id": args.action,
                "sprint": args.sprint,
                "item": action.get("item"),
                "risk": risco,
                "decision": "denied",
                "reason": "human_approval_missing_or_invalid",
                "command_hash": desafio,
                "policy_hash": politica_hash,
            }
            audit(root, policy, evento)
            return erro("confirmacao humana ausente ou incorreta", EXIT_APPROVAL)

    execution = policy.get("execution", {})
    sandbox_mode = execution.get("sandbox", "off") if isinstance(execution, dict) else "off"
    network = action.get("network", execution.get("network", False) if isinstance(execution, dict) else False)
    try:
        command_to_run, sandbox_used = command_for(root, command, sandbox_mode, network)
    except RuntimeError as exc:
        audit(root, policy, {
            "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
            "action_id": args.action,
            "sprint": args.sprint,
            "item": action.get("item"),
            "risk": risco,
            "decision": "denied",
            "reason": "sandbox_unavailable",
            "command_hash": desafio,
            "policy_hash": politica_hash,
        })
        return erro(str(exc))

    evento = {
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        "action_id": args.action,
        "sprint": args.sprint,
        "item": action.get("item"),
        "risk": risco,
        "decision": "approved" if aprovado else "denied",
        "approval_method": "interactive_tty" if risco != "safe" else "policy_allowlist",
        "command_hash": desafio,
        "policy_hash": politica_hash,
        "sandbox": sandbox_used,
        "network": network,
    }
    ok, motivo = audit(root, policy, evento)
    if not ok:
        return erro(motivo)

    try:
        proc = subprocess.run(
            command_to_run,
            cwd=root,
            timeout=action.get("max_runtime_seconds", 300),
            check=False,
        )
    except subprocess.TimeoutExpired:
        evento["result"] = "timeout"
        audit(root, policy, evento)
        return erro("tempo maximo da acao excedido", EXIT_TIMEOUT)
    evento["result"] = proc.returncode
    audit(root, policy, evento)
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
