#!/usr/bin/env python3
"""
Neural-Flow Framework — biblioteca compartilhada dos guards
===========================================================
Helpers usados por todos os validadores. Existe para que os guards nao dupliquem
logica de parsing: o proprio framework registra que duplicar comando operacional
foi o vetor que propagou uma forma errada para ~25 arquivos.

Sem dependencia externa, de proposito: os guards precisam rodar em qualquer
projeto, qualquer stack, sem instalar nada.
"""

from __future__ import annotations

# Assinatura de origem. O `nf_gate` so executa arquivo que a carrega — projeto
# brownfield pode ter um script homonimo com outra interface, e chama-lo com os
# nossos argumentos produz erro de uso confuso em vez de diagnostico.
NF_GUARD_ASSINATURA = "neural-flow-framework"

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

# ── Normalizacao ───────────────────────────────────────────────────────────────


def sem_acento(texto: str) -> str:
    """'Confiança' e 'Confianca' sao a mesma coisa para efeito de validacao."""
    decomposto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in decomposto if unicodedata.category(c) != "Mn")


def chave(texto: str) -> str:
    """Normaliza nome de campo: sem acento, minusculo, sem pontuacao de borda."""
    return sem_acento(texto).strip().lower().rstrip("?:").strip()


# ── Placeholders ───────────────────────────────────────────────────────────────

_PLACEHOLDERS = {
    "a preencher",
    "aaaa-mm-dd",
    "yyyy-mm-dd",
    "todo",
    "tbd",
    "...",
    "n/a",
    "xxx",
}


def eh_placeholder(valor: str) -> bool:
    """Valor de template ainda nao preenchido nao conta como conteudo."""
    limpo = sem_acento(valor).strip().strip("`*").strip()
    if not limpo:
        return True
    if limpo.lower() in _PLACEHOLDERS:
        return False if limpo.lower() in {"n/a"} else True
    if limpo.startswith("<") and limpo.endswith(">"):
        return True
    return bool(re.fullmatch(r"[Xx]{3,}|\.{3,}", limpo))


# ── Leitura ────────────────────────────────────────────────────────────────────


def ler(caminho: Path) -> list[str] | None:
    if not caminho.is_file():
        return None
    try:
        return caminho.read_text(encoding="utf-8").splitlines()
    except (UnicodeDecodeError, OSError):
        return None


def eh_template(linhas: list[str]) -> bool:
    """Arquivo ainda no estado de template (nao copiado/preenchido) nao e validado."""
    cabecalho = sem_acento(" ".join(linhas[:8]).upper())
    return "TEMPLATE NEURAL-FLOW" in cabecalho


def arquivos(raiz: Path, *padroes: str) -> list[Path]:
    """Arquivos que casam com qualquer glob, ignorando ruido de build."""
    ignorar = {".git", "node_modules", ".venv", "venv", "dist", "build_out", "__pycache__"}
    achados: list[Path] = []
    for padrao in padroes:
        for caminho in sorted(raiz.glob(padrao)):
            if not caminho.is_file():
                continue
            if ignorar & set(caminho.parts):
                continue
            achados.append(caminho)
    return achados


# ── Parsing de campos ──────────────────────────────────────────────────────────

# Casa "- Campo: valor" e "- **Campo:** valor" e "- **Campo**: valor"
_RE_CAMPO = re.compile(
    r"^\s*[-*]\s+(?:\*\*)?(?P<campo>[^:*\n]{1,60}?)(?:\*\*)?\s*:\s*(?:\*\*)?(?P<valor>.*?)(?:\*\*)?\s*$"
)


def campos(linhas: list[str], inicio: int = 0, fim: int | None = None) -> dict[str, str]:
    """Extrai campos de lista markdown → {chave normalizada: valor cru}."""
    resultado: dict[str, str] = {}
    for linha in linhas[inicio : fim if fim is not None else len(linhas)]:
        m = _RE_CAMPO.match(linha)
        if m:
            resultado.setdefault(chave(m.group("campo")), m.group("valor").strip())
    return resultado


# "1. Titulo", "1) Titulo", "01 - Titulo", "§2 Titulo" → "Titulo".
# Spec numerada e a forma mais comum de escrever secao obrigatoria; sem isto o
# guard nao acha nenhuma delas.
_RE_ENUMERACAO = re.compile(r"^\s*(?:§\s*)?\d{1,3}\s*[.)\-–—:]?\s+")


def titulo_normalizado(texto: str) -> str:
    return chave(_RE_ENUMERACAO.sub("", texto.strip()))


def secao(linhas: list[str], titulo: str) -> tuple[int, int] | None:
    """Intervalo [inicio, fim) das linhas de uma secao markdown pelo titulo."""
    alvo = titulo_normalizado(titulo)
    inicio = None
    nivel = 0
    for n, linha in enumerate(linhas):
        m = re.match(r"^(#{1,6})\s+(.*)$", linha)
        if not m:
            continue
        if inicio is None and titulo_normalizado(m.group(2)).startswith(alvo):
            inicio, nivel = n + 1, len(m.group(1))
        elif inicio is not None and len(m.group(1)) <= nivel:
            return (inicio, n)
    return (inicio, len(linhas)) if inicio is not None else None


def numero(valor: str) -> float | None:
    """Interpreta '250k', '1.2M', '250_000', '250.000' → float. None se nao for numero."""
    limpo = sem_acento(valor).strip().strip("`*").replace("_", "").replace(" ", "")
    limpo = re.sub(r"(tokens?|usd|\$|R\$)", "", limpo, flags=re.IGNORECASE).strip()
    m = re.fullmatch(r"(?P<n>[\d.,]+)\s*(?P<suf>[kKmM])?", limpo)
    if not m:
        return None
    bruto = m.group("n")
    if "." in bruto and "," in bruto:
        # pt-BR: 1.234,56 → ponto e milhar, virgula e decimal
        bruto = bruto.replace(".", "").replace(",", ".")
    elif "," in bruto:
        bruto = bruto.replace(",", ".")
    elif bruto.count(".") == 1 and len(bruto.rsplit(".", 1)[1]) == 3:
        # 250.000 e milhar; 1.2 e decimal e fica como esta
        bruto = bruto.replace(".", "")
    try:
        n = float(bruto)
    except ValueError:
        return None
    suf = (m.group("suf") or "").lower()
    return n * {"k": 1_000, "m": 1_000_000}.get(suf, 1)


# ── Resultado ──────────────────────────────────────────────────────────────────


@dataclass
class Resultado:
    erros: list[str] = field(default_factory=list)
    verificados: list[str] = field(default_factory=list)

    def erro(self, arquivo: Path | str, linha: int | None, codigo: str, msg: str) -> None:
        local = f"{arquivo}:{linha}" if linha else str(arquivo)
        self.erros.append(f"[{codigo}] {local} — {msg}")

    def verificado(self, caminho: Path | str) -> None:
        self.verificados.append(str(caminho))

    def juntar(self, outro: "Resultado") -> None:
        self.erros.extend(outro.erros)
        self.verificados.extend(outro.verificados)

    @property
    def ok(self) -> bool:
        return not self.erros


def relatar(nome: str, res: Resultado, protocolo: str, quiet: bool = False) -> int:
    """Imprime o resultado padronizado e devolve o exit code."""
    if not res.verificados:
        if not quiet:
            print(f"{nome}: nada a validar — OK")
        return 0
    if not quiet:
        for caminho in res.verificados:
            print(f"  verificado: {caminho}")
    if res.erros:
        print(f"\n{nome}: FAIL — {len(res.erros)} violacao(oes)\n")
        for erro in res.erros:
            print(f"  {erro}")
        print(f"\nProtocolo: {protocolo}")
        return 1
    print(f"\n{nome}: PASS — {len(res.verificados)} arquivo(s) conforme")
    return 0
