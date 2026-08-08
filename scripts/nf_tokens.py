#!/usr/bin/env python3
"""
Neural-Flow Framework — telemetria real de tokens
=================================================
Le o consumo de tokens dos transcripts locais do Claude Code e agrega por
modelo, por dia e por sessao. Fecha a lacuna do Circuit Breaker: ate aqui o
FinOps mostrava o que a sprint DECLARAVA; agora mostra tambem o que foi
MEDIDO — e a divergencia entre os dois.

Privacidade
-----------
So sao lidos numeros: `usage`, `model`, `timestamp` e `sessionId`. **O conteudo
das mensagens nunca e lido nem gravado.** Tudo acontece na sua maquina; nada
sai dela. O leitor faz um pre-filtro por substring e descarta a linha inteira
quando ela nao tem bloco de uso.

Escopo
------
Le apenas o diretorio de transcripts DO PROJETO analisado, nao todos. Num
disco com ~1 GB de historico, varrer tudo levaria segundos; o diretorio de um
projeto sai em centesimos.

Uso:
    python3 scripts/nf_tokens.py                    # projeto atual
    python3 scripts/nf_tokens.py --root ../outro
    python3 scripts/nf_tokens.py --dias 30
    python3 scripts/nf_tokens.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

BASE_TRANSCRIPTS = Path.home() / ".claude" / "projects"

# Campos numericos que interessam. Qualquer outra coisa e ignorada de proposito.
CAMPOS = (
    "input_tokens", "output_tokens",
    "cache_creation_input_tokens", "cache_read_input_tokens",
)


@dataclass
class Consumo:
    entrada: int = 0
    saida: int = 0
    cache_escrito: int = 0
    cache_lido: int = 0
    requisicoes: int = 0

    def somar(self, u: dict) -> None:
        self.entrada += int(u.get("input_tokens") or 0)
        self.saida += int(u.get("output_tokens") or 0)
        self.cache_escrito += int(u.get("cache_creation_input_tokens") or 0)
        self.cache_lido += int(u.get("cache_read_input_tokens") or 0)
        self.requisicoes += 1

    @property
    def total(self) -> int:
        """Tudo que passou pelo modelo, incluindo o que veio de cache."""
        return self.entrada + self.saida + self.cache_escrito + self.cache_lido

    @property
    def faturavel(self) -> int:
        """Leitura de cache custa uma fracao — separa-la do resto evita
        confundir volume de contexto com custo."""
        return self.entrada + self.saida + self.cache_escrito

    @property
    def aproveitamento_cache(self) -> float:
        """Fracao do contexto de entrada que veio de cache em vez de ser
        reprocessada. Quanto maior, mais barata a sessao."""
        base = self.entrada + self.cache_lido + self.cache_escrito
        return (self.cache_lido / base) if base else 0.0

    def como_dict(self) -> dict:
        return {
            "entrada": self.entrada, "saida": self.saida,
            "cache_escrito": self.cache_escrito, "cache_lido": self.cache_lido,
            "requisicoes": self.requisicoes, "total": self.total,
            "faturavel": self.faturavel,
            "aproveitamento_cache": round(self.aproveitamento_cache, 4),
        }


@dataclass
class Sessao:
    id: str
    inicio: str = ""
    fim: str = ""
    consumo: Consumo = field(default_factory=Consumo)

    @property
    def duracao_min(self) -> int:
        try:
            a = datetime.fromisoformat(self.inicio)
            b = datetime.fromisoformat(self.fim)
        except ValueError:
            return 0
        return max(0, int((b - a).total_seconds() // 60))


@dataclass
class Telemetria:
    disponivel: bool = False
    motivo: str = ""
    geral: Consumo = field(default_factory=Consumo)
    por_modelo: dict[str, Consumo] = field(default_factory=dict)
    por_dia: dict[str, Consumo] = field(default_factory=dict)
    # (dia, hora UTC) -> requisicoes. Alimenta o mapa de ritmo.
    por_hora: dict[tuple[str, int], int] = field(default_factory=dict)
    ferramentas: dict[str, int] = field(default_factory=dict)
    detalhe_sessoes: dict[str, Sessao] = field(default_factory=dict)
    sessoes: int = 0
    primeiro: str = ""
    ultimo: str = ""
    arquivos: int = 0

    def como_dict(self) -> dict:
        return {
            "disponivel": self.disponivel, "motivo": self.motivo,
            "geral": self.geral.como_dict(),
            "por_modelo": {k: v.como_dict() for k, v in self.por_modelo.items()},
            "por_dia": {k: v.como_dict() for k, v in self.por_dia.items()},
            "por_hora": {f"{d}T{h:02d}": n for (d, h), n in self.por_hora.items()},
            "ferramentas": dict(sorted(self.ferramentas.items(), key=lambda kv: -kv[1])),
            "sessoes": self.sessoes, "primeiro": self.primeiro,
            "ultimo": self.ultimo, "arquivos": self.arquivos,
        }


def slug_do_projeto(raiz: Path) -> str:
    """O Claude Code nomeia o diretorio de transcript pelo caminho absoluto,
    com os separadores virando hifen."""
    return str(raiz.resolve()).replace("/", "-").replace("\\", "-")


def coletar_tokens(raiz: Path, dias: int = 30, base: Path | None = None,
                   diretorio: Path | None = None) -> Telemetria:
    """`diretorio` le aquela pasta diretamente, sem derivar o slug do caminho.

    O slug vem do caminho absoluto do projeto, entao muda de maquina para
    maquina. Para saida reproduzivel — a pagina de demonstracao versionada — e
    preciso poder apontar uma pasta fixa.
    """
    tel = Telemetria()

    if diretorio is not None:
        if not diretorio.is_dir():
            tel.motivo = "diretorio de transcripts informado nao existe"
            return tel
    else:
        base = base or BASE_TRANSCRIPTS
        if not base.is_dir():
            tel.motivo = "sem transcripts locais do Claude Code nesta maquina"
            return tel
        diretorio = base / slug_do_projeto(raiz)
        if not diretorio.is_dir():
            tel.motivo = f"nenhuma sessao registrada para {raiz.name}"
            return tel

    arquivos = sorted(diretorio.glob("*.jsonl"))
    if not arquivos:
        tel.motivo = f"nenhuma sessao registrada para {raiz.name}"
        return tel

    corte = datetime.now(timezone.utc) - timedelta(days=dias)
    sessoes: set[str] = set()
    carimbos: list[str] = []

    for arquivo in arquivos:
        try:
            with arquivo.open(encoding="utf-8", errors="replace") as f:
                for linha in f:
                    # Pre-filtro barato: a maioria das linhas e conteudo de
                    # mensagem e nem chega ao parser.
                    tem_uso = '"usage"' in linha
                    tem_ferramenta = '"tool_use"' in linha
                    if not tem_uso and not tem_ferramenta:
                        continue
                    try:
                        registro = json.loads(linha)
                    except json.JSONDecodeError:
                        continue
                    msg = registro.get("message")
                    if not isinstance(msg, dict):
                        continue
                    # Nome de ferramenta e um numero de uso, nao conteudo: conta
                    # QUAIS ferramentas o agente usou, nunca com que argumentos.
                    if tem_ferramenta:
                        blocos = msg.get("content")
                        if isinstance(blocos, list):
                            for bloco in blocos:
                                if isinstance(bloco, dict) and bloco.get("type") == "tool_use":
                                    nome_f = bloco.get("name") or "desconhecida"
                                    tel.ferramentas[nome_f] = tel.ferramentas.get(nome_f, 0) + 1

                    uso = msg.get("usage")
                    if not isinstance(uso, dict):
                        continue
                    if not any(uso.get(c) for c in CAMPOS):
                        continue

                    carimbo = registro.get("timestamp") or ""
                    quando = None
                    if carimbo:
                        try:
                            quando = datetime.fromisoformat(carimbo.replace("Z", "+00:00"))
                        except ValueError:
                            quando = None
                    if quando and quando < corte:
                        continue

                    tel.geral.somar(uso)
                    modelo = msg.get("model") or "desconhecido"
                    tel.por_modelo.setdefault(modelo, Consumo()).somar(uso)
                    if quando:
                        # UTC sempre. Usar o fuso local faria o mesmo transcript
                        # render dias diferentes em maquinas diferentes.
                        dia = quando.astimezone(timezone.utc).date().isoformat()
                        tel.por_dia.setdefault(dia, Consumo()).somar(uso)
                        carimbos.append(dia)
                        hora = quando.astimezone(timezone.utc).hour
                        tel.por_hora[(dia, hora)] = tel.por_hora.get((dia, hora), 0) + 1
                    if sid := registro.get("sessionId"):
                        sessoes.add(sid)
                        s = tel.detalhe_sessoes.setdefault(sid, Sessao(id=sid))
                        s.consumo.somar(uso)
                        if quando:
                            iso = quando.astimezone(timezone.utc).isoformat()
                            s.inicio = min(s.inicio, iso) if s.inicio else iso
                            s.fim = max(s.fim, iso) if s.fim else iso
        except OSError:
            continue

    tel.arquivos = len(arquivos)
    tel.sessoes = len(sessoes)
    if carimbos:
        tel.primeiro, tel.ultimo = min(carimbos), max(carimbos)
    tel.disponivel = tel.geral.requisicoes > 0
    if not tel.disponivel:
        tel.motivo = f"sessoes encontradas, mas sem registro de uso nos ultimos {dias} dias"
    return tel


def fmt(n: float) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M".replace(".0M", "M")
    if n >= 10_000:
        return f"{n / 1_000:.0f}k"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k".replace(".0k", "k")
    return f"{n:.0f}"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Consumo real de tokens do projeto, lido dos transcripts locais.",
    )
    ap.add_argument("--root", default=".")
    ap.add_argument("--dias", type=int, default=30, help="janela em dias (default: 30)")
    ap.add_argument("--json", action="store_true", help="saida em JSON")
    args = ap.parse_args()

    raiz = Path(args.root).resolve()
    tel = coletar_tokens(raiz, args.dias)

    if args.json:
        print(json.dumps(tel.como_dict(), indent=2, ensure_ascii=False))
        return 0

    if not tel.disponivel:
        print(f"tokens: {tel.motivo}")
        return 0

    g = tel.geral
    print(f"Consumo real — {raiz.name} (ultimos {args.dias} dias)")
    print(f"  periodo:      {tel.primeiro} a {tel.ultimo}")
    print(f"  requisicoes:  {g.requisicoes}  em {tel.sessoes} sessao(oes)")
    print(f"  entrada:      {fmt(g.entrada)}")
    print(f"  saida:        {fmt(g.saida)}")
    print(f"  cache escrito:{fmt(g.cache_escrito):>8}")
    print(f"  cache lido:   {fmt(g.cache_lido)}  "
          f"({g.aproveitamento_cache:.0%} do contexto veio de cache)")
    print(f"  faturavel:    {fmt(g.faturavel)}  (entrada + saida + escrita de cache)")
    if tel.ferramentas:
        print("\n  ferramentas mais usadas:")
        for nome, n in sorted(tel.ferramentas.items(), key=lambda kv: -kv[1])[:6]:
            print(f"    {nome:<32} {n}")
    print("\n  por modelo:")
    for modelo, c in sorted(tel.por_modelo.items(), key=lambda kv: -kv[1].faturavel):
        print(f"    {modelo:<28} {fmt(c.faturavel):>7}  ({c.requisicoes} req)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
