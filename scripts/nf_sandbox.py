#!/usr/bin/env python3
"""Contrato do sandbox; adaptadores so entram aqui depois de validacao real."""

from __future__ import annotations

NF_GUARD_ASSINATURA = "neural-flow-framework"

from pathlib import Path


def command_for(root: Path, command: list[str], mode: str, network: bool) -> tuple[list[str], str]:
    """Devolve um comando isolado ou falha fechado.

    Nenhum adaptador suportado esta habilitado ainda. "when-available" e
    explicitamente best-effort e informa a ausencia do isolamento no evento de
    auditoria.
    """
    if mode == "off":
        return command, "off"
    if mode == "when-available":
        return command, "unavailable"
    raise RuntimeError(
        "sandbox obrigatoria sem adaptador validado para este sistema operacional"
    )
