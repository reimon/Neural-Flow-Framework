#!/usr/bin/env python3
"""
Guard do Circuit Breaker de Tokens — `docs/protocols/token-circuit-breaker.md`
=============================================================================
"Toda sprint deve declarar um orcamento de tokens e uma politica de bloqueio."
Sem guard, isso e uma frase. Com guard, e uma condicao de merge.

  B1  Sprint declara 'Token budget' com valor numerico.
  B2  Sprint declara 'Consumo observado' (ou 'em andamento' enquanto nao fecha).
  B3  Consumo >= limite de alerta (default 70%) exige registro de alerta;
      consumo >= 100% exige mitigacao OU excecao formal registrada.
  B4  Sprint concluida sem consumo registrado e FAIL — "ausencia de registro de
      consumo relevante" e criterio FAIL explicito do protocolo.

Uso:
  python scripts/validate_token_budget.py
  python scripts/validate_token_budget.py --alerta 0.7 --root <dir>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nf_guards import (  # noqa: E402
    Resultado, arquivos, campos, chave, eh_placeholder, eh_template, ler,
    numero, relatar, secao, sem_acento,
)

PROTOCOLO = "docs/protocols/token-circuit-breaker.md"

CHAVES_BUDGET = ("token budget", "orcamento de tokens", "budget de tokens")
CHAVES_CONSUMO = ("consumo observado", "consumo de tokens", "tokens consumidos")
CHAVES_MITIGACAO = (
    "mitigacao aplicada",  # nome usado por templates/sprint-template.md
    "mitigacao",
    "acao de mitigacao",
    "excecao formal",
    "rearme",
)
CHAVES_ALERTA = ("limite de alerta", "alerta")

EM_ANDAMENTO = {"em andamento", "em curso", "parcial"}

# Valores que significam "campo presente, mas sem conteudo real".
NEGATIVOS = {"nao", "nao se aplica", "nenhuma", "nenhum", "n/a", "-"}


def primeiro(dados: dict[str, str], chaves: tuple[str, ...]) -> str | None:
    """Primeiro campo preenchido, sem a decoracao markdown do valor.

    O template escreve os valores em crases (`- Consumo observado: \\`em andamento\\``);
    sem remove-las, "em andamento" nao casa com o estado literal e o guard acusa
    B2 em toda sprint que ainda nao fechou.
    """
    for k in chaves:
        if k in dados and not eh_placeholder(dados[k]):
            return dados[k].strip().strip("`*").strip()
    return None


def validar(caminho: Path, alerta_pct: float, res: Resultado) -> None:
    linhas = ler(caminho)
    if linhas is None or eh_template(linhas):
        return
    res.verificado(caminho)

    faixa = secao(linhas, "Snapshot Operacional")
    dados = campos(linhas, *(faixa or (0, len(linhas))))
    # Campos de FinOps podem viver em secao propria.
    faixa_finops = secao(linhas, "FinOps") or secao(linhas, "Token")
    if faixa_finops:
        dados.update(campos(linhas, *faixa_finops))

    status = chave(dados.get("status", "").strip("`"))
    linha_ref = (faixa or (1, 0))[0]

    # B1 — budget declarado
    bruto_budget = primeiro(dados, CHAVES_BUDGET)
    if bruto_budget is None:
        res.erro(caminho, linha_ref, "B1", "sprint sem 'Token budget' declarado")
        return
    budget = numero(bruto_budget)
    if budget is None or budget <= 0:
        res.erro(
            caminho, linha_ref, "B1",
            f"'Token budget' nao e um valor numerico utilizavel ({bruto_budget!r})",
        )
        return

    # B2 / B4 — consumo registrado
    bruto_consumo = primeiro(dados, CHAVES_CONSUMO)
    if bruto_consumo is None:
        res.erro(caminho, linha_ref, "B2", "sprint sem 'Consumo observado' declarado")
        return
    if chave(bruto_consumo) in EM_ANDAMENTO:
        if status == "concluida":
            res.erro(
                caminho, linha_ref, "B4",
                "sprint concluida com consumo 'em andamento' — protocolo exige "
                "registro de consumo para fechar",
            )
        return

    consumo = numero(bruto_consumo)
    if consumo is None:
        res.erro(
            caminho, linha_ref, "B2",
            f"'Consumo observado' nao e numerico ({bruto_consumo!r})",
        )
        return

    # B3 — proporcionalidade da resposta ao estouro.
    # A mitigacao precisa ser um CAMPO com conteudo real. Procurar a palavra no
    # corpo do documento fazia a nota explicativa do template ("...sem mitigacao
    # nem excecao formal nao passa") desligar o guard em toda sprint do adotante.
    mitigacao = primeiro(dados, CHAVES_MITIGACAO)
    tem_mitigacao = mitigacao is not None and chave(mitigacao) not in NEGATIVOS
    razao = consumo / budget

    if razao >= 1.0 and not tem_mitigacao:
        res.erro(
            caminho, linha_ref, "B3",
            f"consumo {consumo:,.0f} atingiu {razao:.0%} do budget "
            f"({budget:,.0f}) sem mitigacao nem excecao formal registrada — "
            "budget excedido sem interrupcao e FAIL do protocolo",
        )
    elif razao >= alerta_pct and not tem_mitigacao and "alerta" not in corpo:
        res.erro(
            caminho, linha_ref, "B3",
            f"consumo em {razao:.0%} do budget (limite de alerta {alerta_pct:.0%}) "
            "sem alerta registrado",
        )


def main() -> int:
    ap = argparse.ArgumentParser(description="Guard do Circuit Breaker (Neural-Flow).")
    ap.add_argument("--root", default=".")
    ap.add_argument("--glob", action="append")
    ap.add_argument(
        "--alerta", type=float, default=0.7,
        help="limite de alerta como fracao do budget (default 0.7)",
    )
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    raiz = Path(args.root).resolve()
    padroes = args.glob or [
        "docs/sprints/*.md", "sprints/*.md",
        "apps/*/sprints/*.md", "docs/sessoes/sprints/*.md",
    ]

    res = Resultado()
    for caminho in arquivos(raiz, *padroes):
        validar(caminho, args.alerta, res)
    return relatar("circuit-breaker", res, PROTOCOLO, args.quiet)


if __name__ == "__main__":
    sys.exit(main())
