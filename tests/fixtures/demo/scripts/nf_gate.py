#!/usr/bin/env python3
"""Marcador: a fixture modela um projeto COM o framework instalado.

O dashboard decide pela existencia deste arquivo se pode instruir o leitor a
rodar `python3 scripts/nf_gate.py`. Sem ele, a demo sairia com o aviso de
"framework nao instalado" — verdadeiro para a pasta, falso para o projeto que
a demo representa.

Nao e executado pelos testes nem pelo dashboard: `coletar_guards` roda os
`validate_*.py`, nunca o gate. O conteudo real vive em `scripts/nf_gate.py`,
na raiz do framework.
"""

raise SystemExit("fixture: use scripts/nf_gate.py na raiz do framework")
