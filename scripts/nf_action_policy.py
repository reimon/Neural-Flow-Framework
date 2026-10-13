#!/usr/bin/env python3
"""
Neural-Flow Framework — helpers da politica do Action Gateway
==============================================================
Leitura compartilhada do contrato JSON. O guard e o executor usam a mesma
normalizacao para nao criarem duas politicas divergentes.
"""

from __future__ import annotations

NF_GUARD_ASSINATURA = "neural-flow-framework"

import hashlib
import json
import re
from pathlib import Path

from nf_guards import campos, chave, checklist_itens, ler, secao, sem_acento

RISCOS = ("safe", "sensitive", "irreversible")
SANDBOX_MODES = ("off", "when-available", "required")
RISCO_ORDEM = {nome: n for n, nome in enumerate(RISCOS)}
SHELL_LAUNCHERS = {
    "bash", "cmd", "command", "fish", "powershell", "pwsh", "sh", "sudo", "zsh",
}
SHELL_FLAGS = {"-c", "-command", "-e", "--command"}
ACTION_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{1,63}$")
def policy_path(root: Path) -> Path:
    return root / ".neural-flow" / "action-policy.json"


def load_policy(root: Path) -> tuple[dict | None, str | None]:
    caminho = policy_path(root)
    if not caminho.is_file():
        return None, None
    try:
        valor = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, f"politica invalida: {exc}"
    if not isinstance(valor, dict):
        return None, "politica precisa ser um objeto JSON"
    return valor, None


def action_by_id(policy: dict, action_id: str) -> dict | None:
    for action in policy.get("actions", []):
        if isinstance(action, dict) and action.get("id") == action_id:
            return action
    return None


def sprint_fields(caminho: Path) -> tuple[dict[str, str], list[str]]:
    linhas = ler(caminho) or []
    faixa = secao(linhas, "Snapshot Operacional")
    return (campos(linhas, *faixa) if faixa else {}), linhas


def relative_safe(path: str) -> bool:
    caminho = Path(path)
    return not caminho.is_absolute() and ".." not in caminho.parts


def argv_has_shell(argv: list[str]) -> bool:
    for token in argv:
        base = Path(token).name.lower()
        if base in SHELL_LAUNCHERS or token.lower() in SHELL_FLAGS:
            return True
    return False


def command_matches(prefix: list[str], command: list[str]) -> bool:
    return len(command) >= len(prefix) and command[:len(prefix)] == prefix


def command_hash(action_id: str, sprint: str, command: list[str], policy: dict) -> str:
    payload = {
        "action": action_id,
        "sprint": sprint,
        "command": command,
        "policy": policy,
    }
    bruto = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()


def file_hash(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def normalizar_status(valor: str) -> str:
    return chave(sem_acento(valor.strip("`")))
