#!/usr/bin/env python3
"""
Neural-Flow Framework — diagrama de arquitetura
===============================================
Gera `docs/img/arquitetura.svg`: o caminho de uma mudanca ate virar commit, e os
pontos onde ela e barrada.

Por que este recorte, e nao um poster com os dez protocolos: um diagrama se
justifica quando mostra um MECANISMO que a prosa faz o leitor montar sozinho.
Caixas rotuladas com nomes de protocolo seriam a lista de protocolos redesenhada
— o texto ja faz isso melhor. O que a prosa nao entrega de relance e a
sequencia: o que cada gate le, em que momento roda, e o que acontece quando
reprova.

Gerado por script para nao apodrecer: a lista de guards vem do mesmo registro
que o `nf_gate.py` usa, entao guard novo aparece no desenho sem ninguem lembrar
de redesenhar.

O SVG carrega a propria superficie clara, como um cartao. Assim ele fica legivel
em qualquer fundo — README do GitHub em tema claro ou escuro, slide, PDF — sem
depender de `currentColor`, que nao atravessa a fronteira de um `<img>`.

Uso:
    python3 scripts/nf_diagrama.py
    python3 scripts/nf_diagrama.py --out docs/img/arquitetura.svg
"""

from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nf_gate import GUARDS  # noqa: E402  — mesma fonte de verdade do orquestrador

# ── Paleta: superficie propria, legivel sobre qualquer fundo ───────────────────
SUP = "#ffffff"        # cartao
FUNDO = "#f3f6f8"      # respiro interno
LINHA = "#d3dde3"
LINHA_F = "#b3c2cb"
TINTA = "#17242c"
TINTA_2 = "#4a5a64"
FRACO = "#7d8b94"
MARCA = "#146c84"      # identidade
BLOQ = "#c0392f"       # caminho que reprova
PASSA = "#12805a"      # caminho que aprova
ARTE = "#e9f0f3"       # preenchimento de artefato


def esc(t: str) -> str:
    return html.escape(str(t), quote=True)


def caixa(x, y, w, h, titulo, linhas=(), *, borda=LINHA, fundo=SUP, r=8,
          cor_titulo=TINTA, tam=13, etiqueta="", cor_etiqueta=MARCA) -> str:
    """Caixa com titulo no topo e linhas empilhadas abaixo.

    Empilhar a partir do topo, e nao centralizar, e o que evita a colisao entre
    o titulo e o texto complementar quando a caixa cresce.
    """
    partes = [
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" '
        f'fill="{fundo}" stroke="{borda}" stroke-width="1"/>',
        f'<text x="{x + 14}" y="{y + 23}" font-size="{tam}" font-weight="620" '
        f'fill="{cor_titulo}">{esc(titulo)}</text>',
    ]
    if etiqueta:
        partes.append(
            f'<text x="{x + w - 14}" y="{y + 23}" font-size="10" font-weight="700" '
            f'fill="{cor_etiqueta}" text-anchor="end">{esc(etiqueta)}</text>'
        )
    ly = y + 41
    for linha in linhas:
        forte = linha.startswith("*")
        texto = linha[1:] if forte else linha
        peso = ' font-weight="700"' if forte else ""
        cor = TINTA if forte else TINTA_2
        partes.append(
            f'<text x="{x + 14}" y="{ly}" font-size="11"{peso} fill="{cor}">{esc(texto)}</text>'
        )
        ly += 16
    return "".join(partes)


def rotulo_coluna(x, y, texto) -> str:
    return (f'<text x="{x}" y="{y}" font-size="10" font-weight="700" fill="{FRACO}" '
            f'letter-spacing="1.4">{esc(texto)}</text>')


def seta(x1, y1, x2, y2, *, cor=LINHA_F, rotulo="", marcador="seta",
         tracejada=False, ry=0) -> str:
    tracos = ' stroke-dasharray="5 4"' if tracejada else ""
    linha = (
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{cor}" '
        f'stroke-width="1.5"{tracos} marker-end="url(#{marcador})"/>'
    )
    if not rotulo:
        return linha
    mx = (x1 + x2) / 2
    my = (y1 + y2) / 2 + ry
    # O rotulo fica ACIMA da linha. Centralizado sobre ela, ele cobre a caixa de
    # destino sempre que o vao entre colunas e menor que o texto.
    return (
        linha
        + f'<text x="{mx}" y="{my - 9}" font-size="10.5" fill="{TINTA_2}" '
          f'text-anchor="middle">{esc(rotulo)}</text>'
    )


def gerar() -> str:
    L, A = 1280, 720
    M = 40                      # margem
    C1, W1 = M, 186             # intencao
    C2, W2 = 300, 286           # artefatos
    C3, W3 = 700, 250           # gate local
    C4, W4 = 1010, 230          # autoridade
    Y0 = 148                    # topo das colunas

    codigos = {
        "sprint": "S1–S6", "budget": "B1–B4", "context": "V1–V3",
        "adr": "A1–A6", "spec": "P1–P4", "calibration": "C1–C6",
    }
    artefatos = [
        ("docs/sprints/", "sprint validada, escopo, autonomia", "S1–S6 · B1–B4"),
        ("docs/modulos/", "spec no padrao obrigatorio", "P1–P4"),
        ("docs/adr/", "decisao numerada e imutavel", "A1–A6"),
        ("build/", "plano, diario, divergencias", "C1–C6"),
        ("graphify-out/", "indice consultado antes de ler", "V1–V3"),
    ]

    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {L} {A}" '
        f'width="{L}" height="{A}" role="img" font-family="ui-sans-serif,-apple-system,'
        f'&quot;Segoe UI&quot;,Roboto,sans-serif" '
        f'aria-label="Caminho de uma mudanca no Neural-Flow: os artefatos do projeto sao '
        f'lidos pelos guards; o hook de pre-commit valida o que esta em stage e barra o '
        f'commit quando algum reprova; depois do push o CI revalida, porque o hook e '
        f'opt-in por clone. Divergencias, evidencia e memoria realimentam o ciclo.">',
        '<defs>',
    ]
    for ident, cor in (("seta", LINHA_F), ("seta-bloq", BLOQ), ("seta-passa", PASSA)):
        p.append(f'<marker id="{ident}" viewBox="0 0 10 10" refX="9" refY="5" '
                 f'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
                 f'<path d="M0,1 L9,5 L0,9 z" fill="{cor}"/></marker>')
    p.append('</defs>')
    p.append(f'<rect width="{L}" height="{A}" rx="14" fill="{SUP}"/>')

    # ── Cabecalho ──
    p.append(f'<text x="{M}" y="50" font-size="21" font-weight="700" fill="{TINTA}">'
             f'Neural-Flow — como uma mudanca vira commit</text>')
    p.append(f'<text x="{M}" y="73" font-size="12.5" fill="{FRACO}">'
             f'O caminho da intencao ate a branch, e os pontos onde ele e barrado</text>')
    p.append(f'<line x1="{M}" y1="94" x2="{L - M}" y2="94" stroke="{LINHA}"/>')

    # ── Coluna 1 ──
    p.append(rotulo_coluna(C1, 124, "INTENCAO"))
    p.append(caixa(C1, Y0, W1, 62, "Agente ou pessoa",
                   ["quer mudar o sistema"], borda=LINHA_F))
    p.append(caixa(C1, Y0 + 78, W1, 76, "Sem sprint,",
                   ["nao ha execucao", "*autorizada."], borda=LINHA, fundo=FUNDO))

    # ── Coluna 2 ──
    p.append(rotulo_coluna(C2, 124, "ARTEFATOS QUE O GATE LE"))
    y = Y0
    for nome, desc, etiqueta in artefatos:
        p.append(caixa(C2, y, W2, 54, nome, [desc], fundo=ARTE, borda=LINHA,
                       tam=12.5, etiqueta=etiqueta))
        y += 62
    fim_art = y - 62 + 54
    p.append(seta(C1 + W1 + 6, Y0 + 27, C2 - 8, Y0 + 27, rotulo="produz"))

    # ── Coluna 3 ──
    meio3 = Y0 + 152
    p.append(rotulo_coluna(C3, 124, "GATE LOCAL"))
    p.append(caixa(C3, Y0, W3, 62, "git add",
                   ["caminhos explicitos, nunca -A"], borda=LINHA_F))
    p.append(seta(C3 + W3 / 2, Y0 + 62, C3 + W3 / 2, Y0 + 96))
    p.append(caixa(C3, Y0 + 96, W3, 108, "hook de pre-commit",
                   ["materializa o indice numa",
                    "arvore temporaria e valida *la*".replace("*la*", "la"),
                    "o checado e o que entraria",
                    "no commit — nao o editor"],
                   borda=MARCA, fundo="#f1f8fa"))
    p.append(seta(C2 + W2 + 6, meio3, C3 - 8, meio3, rotulo="le o stage"))

    # ── Ramo que reprova: desce do hook e volta aos artefatos ──
    y_rep = Y0 + 226
    p.append(seta(C3 + W3 / 2, Y0 + 204, C3 + W3 / 2, y_rep - 8, cor=BLOQ,
                  marcador="seta-bloq"))
    p.append(caixa(C3, y_rep, W3, 58, "reprovou: commit barrado",
                   ["corrija o artefato, nao o gate"],
                   borda=BLOQ, fundo="#fdf3f2", cor_titulo=BLOQ, tam=12))
    p.append(f'<path d="M{C3} {y_rep + 29} L{C2 + W2 + 28} {y_rep + 29} '
             f'L{C2 + W2 + 28} {fim_art - 18} L{C2 + W2 + 8} {fim_art - 18}" '
             f'fill="none" stroke="{BLOQ}" stroke-width="1.5" stroke-dasharray="5 4" '
             f'marker-end="url(#seta-bloq)"/>')

    # ── Coluna 4 ──
    p.append(rotulo_coluna(C4, 124, "AUTORIDADE"))
    p.append(seta(C3 + W3 + 6, meio3, C4 - 8, meio3, cor=PASSA, rotulo="passou",
                  marcador="seta-passa"))
    p.append(caixa(C4, Y0, W4, 62, "commit",
                   ["um por item do plano"], borda=LINHA_F))
    p.append(seta(C4 + W4 / 2, Y0 + 62, C4 + W4 / 2, Y0 + 96))
    p.append(caixa(C4, Y0 + 96, W4, 108, "CI: os mesmos guards",
                   ["o hook e opt-in por clone,",
                    "entao guard que depende de",
                    "configuracao de maquina",
                    "*nao e guard"],
                   borda=PASSA, fundo="#f1f9f5"))
    p.append(seta(C4 + W4 / 2, Y0 + 204, C4 + W4 / 2, Y0 + 238, marcador="seta-passa",
                  cor=PASSA))
    p.append(caixa(C4, Y0 + 238, W4, 56, "branch", ["estado publicado"], borda=LINHA))

    # ── Realimentacao ──
    yr = 486
    p.append(f'<line x1="{M}" y1="{yr - 24}" x2="{L - M}" y2="{yr - 24}" stroke="{LINHA}"/>')
    p.append(rotulo_coluna(C1, yr, "O QUE VOLTA PARA O CICLO"))
    volta = [
        ("divergencias", "decisao que o loop tomou sozinho", "fila de revisao humana"),
        ("evidencia", "verde do comando de verificacao", "fecha o item da sprint"),
        ("memoria e indice", "licao datada, reindex incremental", "barateia a proxima sessao"),
    ]
    lw = (L - 2 * M - 2 * 20) / 3
    xr = C1
    for titulo, meio, fim_txt in volta:
        p.append(caixa(xr, yr + 14, lw, 74, titulo,
                       [meio, f"→ {fim_txt}"], borda=LINHA, fundo=FUNDO, tam=12.5))
        xr += lw + 20
    p.append(seta(C4 + W4 / 2, Y0 + 294, C4 + W4 / 2, yr - 34, tracejada=True))
    p.append(f'<text x="{C4 + W4 / 2 + 10}" y="{Y0 + 318}" font-size="10.5" '
             f'fill="{TINTA_2}">realimenta</text>')

    # ── Rodape: guards vindos do registro do nf_gate ──
    yg = 606
    p.append(f'<line x1="{M}" y1="{yg}" x2="{L - M}" y2="{yg}" stroke="{LINHA}"/>')
    p.append(f'<text x="{M}" y="{yg + 26}" font-size="10" font-weight="700" fill="{FRACO}" '
             f'letter-spacing="1.4">GUARDS EXECUTAVEIS<tspan fill="{MARCA}">'
             f'   python3 scripts/nf_gate.py</tspan></text>')
    n = len(GUARDS)
    gw = (L - 2 * M - (n - 1) * 10) / n
    xg = M
    for nome, (_script, protocolo, _o_que) in GUARDS.items():
        p.append(caixa(xg, yg + 38, gw, 50, protocolo, [nome], borda=LINHA,
                       fundo=FUNDO, tam=11, etiqueta=codigos.get(nome, "")))
        xg += gw + 10

    p.append('</svg>')
    return "\n".join(p) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Gera o diagrama de arquitetura do Neural-Flow.")
    ap.add_argument("--out", default="docs/img/arquitetura.svg")
    args = ap.parse_args()
    destino = Path(args.out)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(gerar(), encoding="utf-8")
    print(f"diagrama: {destino}  ({destino.stat().st_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
