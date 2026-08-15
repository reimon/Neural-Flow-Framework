#!/usr/bin/env python3
"""
Neural-Flow Framework — verificacao da autenticacao Azure (ADR-003)
===================================================================
Um comando que responde a unica pergunta que trava a Sprint 3: **a via keyless
funciona neste ambiente?**

Existe porque o criterio de aceite do item 2.1 e "a ingestao roda sem admin key",
e rodar a ingestao inteira para descobrir isso e caro e escreve no indice. Este
script isola a parte que interessa — obter token pelo Entra ID e ser aceito pelos
dois servicos — e nao escreve nada.

O que faz, nesta ordem:

  1. obtem token do Entra ID para o plano de dados do Search;
  2. le a contagem de documentos do indice (`GET`, nenhuma escrita);
  3. obtem token para o Azure OpenAI e gera um embedding de uma palavra.

O passo 3 e a unica chamada com custo: um embedding de ~1 token. E o menor
teste possivel que ainda prova que a credencial serve para o que a ingestao faz.

Uso:
    python3 scripts/nf_azure_smoke.py              # keyless (padrao)
    NF_AZURE_AUTH=key python3 scripts/nf_azure_smoke.py   # compara com a via antiga
    python3 scripts/nf_azure_smoke.py --sem-openai        # so o Search, custo zero

Saida: exit 0 se as duas vias respondem; 1 com diagnostico acionavel se nao.
Nenhum segredo e impresso — nem token, nem chave, nem trecho de qualquer um.
"""

from __future__ import annotations

# Assinatura de origem. O `nf_gate` so executa arquivo que a carrega — projeto
# brownfield pode ter um script homonimo com outra interface, e chama-lo com os
# nossos argumentos produz erro de uso confuso em vez de diagnostico.
NF_GUARD_ASSINATURA = "neural-flow-framework"

import argparse
import os
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

# Diagnostico por tipo de falha. Erro de RBAC e o caso comum e o mais confuso:
# a mensagem do SDK fala em "Forbidden" sem dizer qual role falta.
DICAS = {
    403: (
        "sem permissao. A via keyless exige role assignment — as do projeto estao em "
        "`infra/terraform/main.tf` (Search Index Data Contributor, Search Service "
        "Contributor, Cognitive Services OpenAI User). Atribuicao de role leva alguns "
        "minutos para propagar."
    ),
    401: (
        "nao autenticado. Rode `az login` (ou configure a identidade gerenciada) — "
        "`DefaultAzureCredential` procura, nesta ordem: variaveis de ambiente, "
        "identidade gerenciada, Azure CLI."
    ),
    404: "endpoint ou indice nao encontrado. Confira AZURE_SEARCH_ENDPOINT e o nome do indice.",
}


def _dica(exc: Exception) -> str:
    codigo = getattr(exc, "status_code", None)
    if codigo in DICAS:
        return DICAS[codigo]
    texto = str(exc).lower()
    for chave, dica in (("forbidden", 403), ("unauthorized", 401), ("not found", 404)):
        if chave in texto:
            return DICAS[dica]
    return "verifique endpoint, rede e se o recurso existe."


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Verifica a autenticacao Azure sem escrever nada (ADR-003)."
    )
    ap.add_argument("--sem-openai", action="store_true",
                    help="pula o embedding — custo zero, prova so o Search")
    args = ap.parse_args()

    try:
        from dotenv import load_dotenv

        load_dotenv(AQUI / ".env")
    except ImportError:
        pass  # .env e conveniencia; variavel de ambiente ja setada serve igual

    from nf_azure_auth import credencial_search, descricao, kwargs_openai

    endpoint = os.environ.get("AZURE_SEARCH_ENDPOINT")
    if not endpoint:
        print("erro: AZURE_SEARCH_ENDPOINT nao definida.", file=sys.stderr)
        print("      Ela sai do output `search_service_endpoint` do Terraform.", file=sys.stderr)
        return 1
    indice = os.environ.get("AZURE_SEARCH_INDEX_NAME", "neural-memory")

    print(f"autenticacao: {descricao()}")
    print(f"endpoint:     {endpoint}")
    print(f"indice:       {indice}\n")

    falhou = False

    # ── Search ────────────────────────────────────────────────────────────────
    try:
        from azure.search.documents import SearchClient

        cliente = SearchClient(endpoint=endpoint, index_name=indice,
                               credential=credencial_search())
        total = cliente.get_document_count()
        print(f"  [ok]   Search respondeu — {total} documento(s) no indice")
    except ImportError as exc:
        print(f"  [erro] SDK ausente ({exc.name}). `pip install -r scripts/requirements.txt`")
        return 1
    except Exception as exc:  # noqa: BLE001 — o diagnostico e o produto aqui
        print(f"  [FALHA] Search: {exc.__class__.__name__} — {_dica(exc)}")
        falhou = True

    # ── OpenAI ────────────────────────────────────────────────────────────────
    if args.sem_openai:
        print("  [pulado] OpenAI (--sem-openai)")
    else:
        destino = os.environ.get("AZURE_OPENAI_ENDPOINT")
        deployment = os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT",
                                    "text-embedding-3-small")
        if not destino:
            print("  [FALHA] AZURE_OPENAI_ENDPOINT nao definida")
            falhou = True
        else:
            try:
                from openai import AzureOpenAI

                cliente_ia = AzureOpenAI(azure_endpoint=destino, api_version="2024-02-01",
                                         **kwargs_openai())
                resp = cliente_ia.embeddings.create(model=deployment, input="ping")
                print(f"  [ok]   OpenAI respondeu — embedding de "
                      f"{len(resp.data[0].embedding)} dimensoes")
            except Exception as exc:  # noqa: BLE001
                print(f"  [FALHA] OpenAI: {exc.__class__.__name__} — {_dica(exc)}")
                falhou = True

    if falhou:
        print("\nA via keyless NAO esta operante neste ambiente.")
        print("Nao contorne com NF_AZURE_AUTH=key sem registrar: e a divida do ADR-003")
        print("voltando por baixo do pano. Conserte a role assignment.")
        return 1

    print("\nVia keyless operante. Isto fecha o criterio de aceite do item 2.1 da")
    print("Sprint 3 — registre a saida como evidencia antes de marcar o item.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
