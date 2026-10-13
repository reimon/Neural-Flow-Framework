#!/usr/bin/env python3
"""
Guard G1-G5 do contrato do Action Gateway.

O guard valida a politica versionada. Ele nao executa nenhuma acao.
"""

from __future__ import annotations

NF_GUARD_ASSINATURA = "neural-flow-framework"

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nf_action_policy import (  # noqa: E402
    ACTION_ID,
    RISCOS,
    SANDBOX_MODES,
    SHELL_FLAGS,
    SHELL_LAUNCHERS,
    action_by_id,
    argv_has_shell,
    checklist_itens,
    load_policy,
    policy_path,
    relative_safe,
    sprint_fields,
)
from nf_guards import Resultado, eh_placeholder, relatar, sem_acento  # noqa: E402

PROTOCOLO = "docs/protocols/action-gateway.md"


def validar(root: Path, res: Resultado) -> None:
    caminho = policy_path(root)
    if not caminho.is_file():
        return
    res.verificado(caminho)
    policy, erro = load_policy(root)
    if erro:
        res.erro(caminho, None, "G1", erro)
        return
    assert policy is not None

    if policy.get("version") != 1 or not isinstance(policy.get("enabled"), bool):
        res.erro(caminho, None, "G1", "version precisa ser 1 e enabled precisa ser boolean")

    audit = policy.get("audit_path")
    if not isinstance(audit, str) or not relative_safe(audit) or not audit.startswith(".neural-flow/"):
        res.erro(caminho, None, "G1", "audit_path precisa ser relativo dentro de .neural-flow")

    execution = policy.get("execution", {})
    if not isinstance(execution, dict):
        res.erro(caminho, None, "G1", "execution precisa ser objeto")
        execution = {}
    sandbox = execution.get("sandbox", "off")
    if sandbox not in SANDBOX_MODES:
        res.erro(caminho, None, "G1", f"execution.sandbox invalido: {sandbox!r}")
    if not isinstance(execution.get("network", False), bool):
        res.erro(caminho, None, "G1", "execution.network precisa ser boolean")

    actions = policy.get("actions")
    if not isinstance(actions, list):
        res.erro(caminho, None, "G2", "actions precisa ser uma lista")
        return
    if policy.get("enabled") and not actions:
        res.erro(caminho, None, "G2", "politica habilitada precisa declarar pelo menos uma acao")

    ids: set[str] = set()
    for pos, action in enumerate(actions, 1):
        local = f"{caminho} acao {pos}"
        if not isinstance(action, dict):
            res.erro(local, None, "G3", "acao precisa ser objeto")
            continue
        action_id = action.get("id")
        if not isinstance(action_id, str) or not ACTION_ID.fullmatch(action_id):
            res.erro(local, None, "G3", "id invalido")
        elif action_id in ids:
            res.erro(local, None, "G2", f"id duplicado: {action_id}")
        else:
            ids.add(action_id)

        descricao = action.get("description")
        if not isinstance(descricao, str) or eh_placeholder(descricao):
            res.erro(local, None, "G3", "description ausente ou placeholder")

        risco = action.get("risk")
        if risco not in RISCOS:
            res.erro(local, None, "G3", f"risk invalido: {risco!r}")

        prefix = action.get("argv_prefix")
        if (
            not isinstance(prefix, list)
            or not prefix
            or not all(isinstance(token, str) and token for token in prefix)
        ):
            res.erro(local, None, "G3", "argv_prefix precisa ser lista de strings nao vazia")
        elif argv_has_shell(prefix) or any(token.lower() in SHELL_FLAGS for token in prefix):
            res.erro(local, None, "G5", "argv_prefix nao pode usar shell, sudo ou flag de execucao arbitraria")

        approval = action.get("requires_human_approval")
        if not isinstance(approval, bool):
            res.erro(local, None, "G3", "requires_human_approval precisa ser boolean")
        elif risco in {"sensitive", "irreversible"} and not approval:
            res.erro(local, None, "G5", f"acao {risco} precisa exigir aprovacao humana")
        elif risco == "safe" and approval:
            res.erro(local, None, "G5", "acao safe nao deve bloquear o fluxo com aprovacao humana")

        timeout = action.get("max_runtime_seconds")
        if not isinstance(timeout, int) or isinstance(timeout, bool) or not 1 <= timeout <= 3600:
            res.erro(local, None, "G3", "max_runtime_seconds precisa ser inteiro entre 1 e 3600")

        network = action.get("network", False)
        if not isinstance(network, bool):
            res.erro(local, None, "G3", "network precisa ser boolean")

        sprint = action.get("sprint")
        item = action.get("item")
        if not isinstance(sprint, str) or not relative_safe(sprint):
            res.erro(local, None, "G4", "sprint precisa ser caminho relativo sem ..")
            continue
        sprint_path = root / sprint
        if not sprint_path.is_file():
            res.erro(local, None, "G4", f"sprint nao existe: {sprint}")
            continue
        if not isinstance(item, str) or item not in checklist_itens(sprint_fields(sprint_path)[1]):
            res.erro(local, None, "G4", f"item {item!r} nao existe na sprint {sprint}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Guard do contrato do Action Gateway.")
    ap.add_argument("--root", default=".")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    res = Resultado()
    validar(Path(args.root).resolve(), res)
    return relatar("action-policy", res, PROTOCOLO, args.quiet)


if __name__ == "__main__":
    sys.exit(main())
