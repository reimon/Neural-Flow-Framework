#!/usr/bin/env python3
"""
Neural-Flow Framework — autenticacao Azure sem chave (ADR-003)
==============================================================
O protocolo Aegis prega "zero segredo em prompt, memoria ou artefato", e a
implementacao de referencia contradizia isso: admin key distribuida por quatro
caminhos (`scripts/.env`, `.vscode/mcp.json`, GitHub Secrets e um segredo no Key
Vault). O ADR-003 registrou a divida; este modulo a paga.

Padrao vigente da Microsoft: **keyless**, via Microsoft Entra ID + RBAC
(`DefaultAzureCredential` com as roles Search Index Data Contributor/Reader e
Cognitive Services OpenAI User).

Politica deste modulo
---------------------
1. **Keyless por padrao.** Sem configuracao, usa `DefaultAzureCredential`.
2. **Chave so por opt-in explicito:** `NF_AZURE_AUTH=key`. Existe porque tenant
   sem RBAC configurado ainda precisa rodar — mas avisa em toda execucao, para a
   divida nao voltar a ser silenciosa.
3. **Sem fallback automatico.** Cair na chave sozinho quando o RBAC falha
   converteria um erro de permissao — que se conserta — em uma dependencia
   permanente de segredo, que ninguem mais ve.

Este modulo nao e um guard: e codigo da implementacao de referencia. Fica em
`scripts/` porque `ingest.py`, `search.py` e o servidor MCP compartilham a mesma
decisao de autenticacao — e decisao duplicada e decisao que diverge.
"""

from __future__ import annotations

import os
import sys

# Escopo de token do plano de dados do Azure OpenAI. Nao e o escopo do Search:
# o Search usa credencial de token direto, sem provedor de bearer.
ESCOPO_OPENAI = "https://cognitiveservices.azure.com/.default"

_avisado = False


def modo() -> str:
    """`key` so quando pedido explicitamente; caso contrario, keyless."""
    return "key" if os.environ.get("NF_AZURE_AUTH", "").strip().lower() == "key" else "entra"


def _avisar_uma_vez() -> None:
    global _avisado
    if _avisado:
        return
    _avisado = True
    print(
        "[nf] AVISO: autenticacao por admin key (NF_AZURE_AUTH=key). E divida "
        "conhecida — ver docs/adr/ADR-003. O padrao e keyless via Entra ID/RBAC.",
        file=sys.stderr,
    )


def _exigir(nome: str) -> str:
    valor = os.environ.get(nome)
    if not valor:
        raise SystemExit(
            f"erro: {nome} nao definida. Com NF_AZURE_AUTH=key ela e obrigatoria; "
            f"sem ela, remova a variavel e use Entra ID (o padrao)."
        )
    return valor


def credencial_search():
    """Credencial para Azure AI Search — plano de dados e de indice."""
    if modo() == "key":
        _avisar_uma_vez()
        from azure.core.credentials import AzureKeyCredential

        return AzureKeyCredential(_exigir("AZURE_SEARCH_ADMIN_KEY"))

    from azure.identity import DefaultAzureCredential

    return DefaultAzureCredential()


def kwargs_openai() -> dict:
    """Argumentos de autenticacao para `AzureOpenAI(**kwargs_openai())`.

    Keyless usa `azure_ad_token_provider`, nao `api_key`: o provedor renova o
    token sozinho, entao processo longo — o servidor MCP — nao morre quando o
    token expira.
    """
    if modo() == "key":
        _avisar_uma_vez()
        return {"api_key": _exigir("AZURE_OPENAI_API_KEY")}

    from azure.identity import DefaultAzureCredential, get_bearer_token_provider

    return {
        "azure_ad_token_provider": get_bearer_token_provider(
            DefaultAzureCredential(), ESCOPO_OPENAI
        )
    }


def descricao() -> str:
    return (
        "admin key (ADR-003, divida conhecida)"
        if modo() == "key"
        else "Entra ID / RBAC (DefaultAzureCredential)"
    )
