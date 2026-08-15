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

# Assinatura de origem. O `nf_gate` so executa arquivo que a carrega — projeto
# brownfield pode ter um script homonimo com outra interface, e chama-lo com os
# nossos argumentos produz erro de uso confuso em vez de diagnostico.
NF_GUARD_ASSINATURA = "neural-flow-framework"

import argparse
import json
import re
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
    por_provedor: dict[str, Consumo] = field(default_factory=dict)
    # acumuladores usados pelos leitores durante a varredura
    carimbos: list[str] = field(default_factory=list)
    sessoes_ids: set = field(default_factory=set)
    detalhe_sessoes: dict[str, Sessao] = field(default_factory=dict)
    sessoes: int = 0
    primeiro: str = ""
    ultimo: str = ""
    arquivos: int = 0
    # Como a janela foi recortada: sprint de origem, intervalo e — o que mais
    # importa — se outra sprint dividiu algum dia com esta. Sem isso o numero
    # sai com cara de exato quando e teto.
    recorte: dict = field(default_factory=dict)

    def como_dict(self) -> dict:
        return {
            "disponivel": self.disponivel, "motivo": self.motivo,
            "geral": self.geral.como_dict(),
            "por_modelo": {k: v.como_dict() for k, v in self.por_modelo.items()},
            "por_dia": {k: v.como_dict() for k, v in self.por_dia.items()},
            "por_hora": {f"{d}T{h:02d}": n for (d, h), n in self.por_hora.items()},
            "ferramentas": dict(sorted(self.ferramentas.items(), key=lambda kv: -kv[1])),
            "por_provedor": {k: v.como_dict() for k, v in self.por_provedor.items()},
            "sessoes": self.sessoes, "primeiro": self.primeiro,
            "ultimo": self.ultimo, "arquivos": self.arquivos,
            "recorte": self.recorte,
        }


# ── Recorte por sprint ─────────────────────────────────────────────────────────
# A telemetria nasceu agregando por dia. Dia nao e unidade de trabalho: uma
# sprint termina no meio da tarde e a seguinte comeca em seguida, entao o
# consumo de um dia pode pertencer a duas. Foi por isso que a Sprint 2 so pode
# registrar um limite superior (ver `docs/sprints/sprint-02-autogovernanca.md`).
#
# O recorte por sprint le as datas do proprio arquivo de sprint. Onde ele nao
# resolve — dia partilhado por duas sprints — ele **avisa**, em vez de deixar o
# numero com cara de exato. Um teto declarado como teto e honesto; um teto
# apresentado como medida nao e.

CAMPO_INICIO = "data de inicio"
CAMPOS_FIM = ("data real de conclusao", "data planejada de conclusao")
RE_DATA = re.compile(r"(\d{4})-(\d{2})-(\d{2})")


def _data(valor: str) -> date | None:
    m = RE_DATA.search(valor or "")
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def sprints_do_projeto(raiz: Path) -> list[dict]:
    """Todas as sprints com intervalo resolvido, ordenadas por inicio."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from nf_guards import campos, eh_template, ler, secao  # noqa: E402

    achadas = []
    for caminho in sorted(raiz.glob("docs/sprints/*.md")):
        linhas = ler(caminho)
        if linhas is None or eh_template(linhas):
            continue
        faixa = secao(linhas, "Snapshot Operacional")
        dados = campos(linhas, *(faixa or (0, len(linhas))))
        inicio = _data(dados.get(CAMPO_INICIO, ""))
        if not inicio:
            continue
        fim = None
        for chave_fim in CAMPOS_FIM:
            fim = _data(dados.get(chave_fim, ""))
            if fim:
                break
        m = re.search(r"(\d{1,3})", caminho.stem)
        achadas.append({
            "arquivo": str(caminho.relative_to(raiz)),
            "numero": int(m.group(1)) if m else None,
            "titulo": linhas[0].lstrip("# ").strip() if linhas else caminho.stem,
            "inicio": inicio,
            "fim": fim or date.today(),
            "status": dados.get("status", "").strip("`"),
        })
    return sorted(achadas, key=lambda s: s["inicio"])


def janela_da_sprint(raiz: Path, alvo: str) -> dict:
    """Intervalo de uma sprint, mais as sprints que dividem dia com ela.

    `alvo` e o numero (`3`) ou um caminho de arquivo.
    """
    todas = sprints_do_projeto(raiz)
    if not todas:
        raise SystemExit("nenhuma sprint com 'Data de inicio' em docs/sprints/")

    escolhida = None
    if alvo.isdigit():
        escolhida = next((s for s in todas if s["numero"] == int(alvo)), None)
    else:
        pedido = Path(alvo).name
        escolhida = next((s for s in todas if Path(s["arquivo"]).name == pedido), None)
    if escolhida is None:
        disponiveis = ", ".join(str(s["numero"]) for s in todas if s["numero"])
        raise SystemExit(f"sprint '{alvo}' nao encontrada (disponiveis: {disponiveis})")

    sobrepostas = [
        s["arquivo"] for s in todas
        if s is not escolhida
        and s["inicio"] <= escolhida["fim"] and escolhida["inicio"] <= s["fim"]
    ]
    return {**escolhida, "sobrepostas": sobrepostas}


def slug_do_projeto(raiz: Path) -> str:
    """O Claude Code nomeia o diretorio de transcript pelo caminho absoluto,
    com os separadores virando hifen."""
    return str(raiz.resolve()).replace("/", "-").replace("\\", "-")


def coletar_tokens(raiz: Path, dias: int = 30, base: Path | None = None,
                   diretorio: Path | None = None, desde: datetime | None = None,
                   ate: datetime | None = None) -> Telemetria:
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
            _finalizar(tel, raiz, dias, datetime.now(timezone.utc) - timedelta(days=dias), 0)
            if tel.disponivel:
                tel.motivo = ""
            return tel
        diretorio = base / slug_do_projeto(raiz)
        if not diretorio.is_dir():
            tel.motivo = f"nenhuma sessao registrada para {raiz.name}"
            _finalizar(tel, raiz, dias, datetime.now(timezone.utc) - timedelta(days=dias), 0)
            if tel.disponivel:
                tel.motivo = ""
            return tel

    arquivos = sorted(diretorio.glob("*.jsonl"))
    if not arquivos:
        tel.motivo = f"nenhuma sessao registrada para {raiz.name}"
        return tel

    corte = desde or (datetime.now(timezone.utc) - timedelta(days=dias))
    sessoes: set[str] = tel.sessoes_ids
    carimbos: list[str] = tel.carimbos
    prov_cc = tel.por_provedor.setdefault("claude-code", Consumo())

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
                    if quando and (quando < corte or (ate and quando > ate)):
                        continue

                    tel.geral.somar(uso)
                    prov_cc.somar(uso)
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

    if prov_cc.requisicoes == 0:
        tel.por_provedor.pop("claude-code", None)

    _finalizar(tel, raiz, dias, corte, len(arquivos), ate)
    return tel


def _finalizar(tel: Telemetria, raiz: Path, dias: int, corte: datetime,
               arquivos: int, ate: datetime | None = None) -> None:
    ler_codex(raiz, corte, tel, ate=ate)
    tel.arquivos = arquivos
    tel.sessoes = len(tel.sessoes_ids)
    if tel.carimbos:
        tel.primeiro, tel.ultimo = min(tel.carimbos), max(tel.carimbos)
    tel.disponivel = tel.geral.requisicoes > 0
    if not tel.disponivel:
        tel.motivo = f"sessoes encontradas, mas sem registro de uso nos ultimos {dias} dias"




# ── Codex ──────────────────────────────────────────────────────────────────────
# O Codex grava o uso nos rollouts de sessao, em `~/.codex/sessions/AAAA/MM/DD/`.
# Nao e preciso ler `auth.json` nem consultar a API: tudo que interessa esta no
# arquivo de sessao.

BASE_CODEX = Path.home() / ".codex" / "sessions"


def _codex_normaliza(uso: dict) -> dict:
    """Traduz o vocabulario do Codex para o do coletor.

    Na semantica da OpenAI, `cached_input_tokens` e SUBCONJUNTO de
    `input_tokens` — nao uma parcela adicional. Somar os dois contaria o cache
    duas vezes e inflaria a entrada. Verificado no proprio rollout:
    `total_tokens == input_tokens + output_tokens`.
    """
    entrada = int(uso.get("input_tokens") or 0)
    cache_lido = int(uso.get("cached_input_tokens") or 0)
    return {
        "input_tokens": max(0, entrada - cache_lido),
        "output_tokens": int(uso.get("output_tokens") or 0),
        "cache_creation_input_tokens": int(uso.get("cache_write_input_tokens") or 0),
        "cache_read_input_tokens": cache_lido,
    }


def _pertence(caminhos: list[str], raiz: Path) -> bool:
    """O Codex organiza sessoes por data, nao por projeto: o vinculo vem do
    `cwd`. Sem esse filtro o numero seria de todos os projetos somados.

    Os dois lados sao resolvidos antes de comparar. O caminho gravado no rollout
    pode passar por symlink — em macOS `/tmp` e `/private/tmp` sao o mesmo lugar
    com nomes diferentes — e a comparacao textual descartaria tudo em silencio,
    que e o pior tipo de falha: numero zerado sem nenhum aviso.
    """
    alvo = str(raiz.resolve())
    for c in caminhos:
        if not c:
            continue
        try:
            r = str(Path(c).resolve())
        except (OSError, ValueError):
            r = c
        if r == alvo or r.startswith(alvo + "/"):
            return True
    return False


def ler_codex(raiz: Path, corte: datetime, tel: Telemetria,
              base: Path | None = None, diretorio: Path | None = None,
              ate: datetime | None = None) -> None:
    origem = diretorio or base or BASE_CODEX
    if not origem.is_dir():
        return
    prov = tel.por_provedor.setdefault("codex", Consumo())

    for arquivo in sorted(origem.rglob("*.jsonl")):
        cwd_atual: list[str] = []
        modelo_atual = "desconhecido"
        sessao_id = arquivo.stem
        try:
            with arquivo.open(encoding="utf-8", errors="replace") as f:
                for linha in f:
                    if ('"token_count"' not in linha and '"cwd"' not in linha
                            and '"model"' not in linha):
                        continue
                    try:
                        registro = json.loads(linha)
                    except json.JSONDecodeError:
                        continue
                    p = registro.get("payload")
                    if not isinstance(p, dict):
                        continue

                    tipo = registro.get("type")
                    if tipo in ("session_meta", "turn_context"):
                        caminhos = [p.get("cwd")] + list(p.get("workspace_roots") or [])
                        cwd_atual = [c for c in caminhos if c]
                        if p.get("model"):
                            modelo_atual = p["model"]
                        if p.get("session_id"):
                            sessao_id = p["session_id"]
                        continue

                    if p.get("type") != "token_count":
                        continue
                    if not _pertence(cwd_atual, raiz):
                        continue

                    info = p.get("info") or {}
                    # `last_token_usage` e o delta do turno; `total_token_usage`
                    # e acumulado da sessao. Somar o acumulado a cada evento
                    # inflaria o numero em ordens de magnitude.
                    uso = _codex_normaliza(info.get("last_token_usage") or {})
                    if not any(uso.values()):
                        continue

                    carimbo = registro.get("timestamp") or ""
                    quando = _instante(carimbo)
                    if quando and (quando < corte or (ate and quando > ate)):
                        continue

                    tel.geral.somar(uso)
                    prov.somar(uso)
                    tel.por_modelo.setdefault(modelo_atual, Consumo()).somar(uso)
                    if quando:
                        dia = quando.astimezone(timezone.utc).date().isoformat()
                        tel.por_dia.setdefault(dia, Consumo()).somar(uso)
                        hora = quando.astimezone(timezone.utc).hour
                        tel.por_hora[(dia, hora)] = tel.por_hora.get((dia, hora), 0) + 1
                        tel.carimbos.append(dia)
                    s = tel.detalhe_sessoes.setdefault(sessao_id, Sessao(id=sessao_id))
                    s.consumo.somar(uso)
                    if quando:
                        iso = quando.astimezone(timezone.utc).isoformat()
                        s.inicio = min(s.inicio, iso) if s.inicio else iso
                        s.fim = max(s.fim, iso) if s.fim else iso
                    tel.sessoes_ids.add(sessao_id)
        except OSError:
            continue

    if prov.requisicoes == 0:
        tel.por_provedor.pop("codex", None)


def _instante(carimbo: str) -> datetime | None:
    if not carimbo:
        return None
    try:
        return datetime.fromisoformat(carimbo.replace("Z", "+00:00"))
    except ValueError:
        return None


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
    ap.add_argument("--sprint", help="recorta pelo intervalo de uma sprint (numero ou arquivo)")
    ap.add_argument("--desde", help="inicio do recorte (AAAA-MM-DD)")
    ap.add_argument("--ate", help="fim do recorte, inclusive (AAAA-MM-DD)")
    ap.add_argument("--json", action="store_true", help="saida em JSON")
    args = ap.parse_args()

    raiz = Path(args.root).resolve()

    desde = ate = None
    recorte: dict = {}
    if args.sprint:
        janela = janela_da_sprint(raiz, args.sprint)
        desde, fim = janela["inicio"], janela["fim"]
        ate = fim
        recorte = {
            "sprint": janela["arquivo"], "titulo": janela["titulo"],
            "desde": desde.isoformat(), "ate": ate.isoformat(),
            "sobrepostas": janela["sobrepostas"],
            # Dia e a menor unidade que os transcripts datam de forma confiavel;
            # sprint que divide dia com outra so admite teto, nunca medida.
            "exato": not janela["sobrepostas"],
        }
    if args.desde:
        desde = _data(args.desde) or desde
    if args.ate:
        ate = _data(args.ate) or ate
    if (args.desde or args.ate) and not args.sprint:
        recorte = {
            "desde": desde.isoformat() if desde else "",
            "ate": ate.isoformat() if ate else "",
            "sobrepostas": [], "exato": True,
        }

    # Data vira instante: o intervalo e fechado nos dois extremos, entao o fim e
    # o ultimo segundo do dia. Sem isso, `--ate` cortaria o dia inteiro.
    d_ini = (datetime.combine(desde, datetime.min.time(), tzinfo=timezone.utc)
             if desde else None)
    d_fim = (datetime.combine(ate, datetime.max.time(), tzinfo=timezone.utc)
             if ate else None)

    tel = coletar_tokens(raiz, args.dias, desde=d_ini, ate=d_fim)
    tel.recorte = recorte

    if args.json:
        print(json.dumps(tel.como_dict(), indent=2, ensure_ascii=False))
        return 0

    if not tel.disponivel:
        print(f"tokens: {tel.motivo}")
        return 0

    g = tel.geral
    if tel.recorte.get("sprint"):
        print(f"Consumo real — {tel.recorte['titulo']}")
        print(f"  recorte:      {tel.recorte['desde']} a {tel.recorte['ate']}  "
              f"({tel.recorte['sprint']})")
    elif tel.recorte:
        print(f"Consumo real — {raiz.name}")
        print(f"  recorte:      {tel.recorte.get('desde') or 'inicio'} a "
              f"{tel.recorte.get('ate') or 'hoje'}")
    else:
        print(f"Consumo real — {raiz.name} (ultimos {args.dias} dias)")
    print(f"  periodo:      {tel.primeiro} a {tel.ultimo}")
    print(f"  requisicoes:  {g.requisicoes}  em {tel.sessoes} sessao(oes)")
    print(f"  entrada:      {fmt(g.entrada)}")
    print(f"  saida:        {fmt(g.saida)}")
    print(f"  cache escrito:{fmt(g.cache_escrito):>8}")
    print(f"  cache lido:   {fmt(g.cache_lido)}  "
          f"({g.aproveitamento_cache:.0%} do contexto veio de cache)")
    print(f"  faturavel:    {fmt(g.faturavel)}  (entrada + saida + escrita de cache)")
    if len(tel.por_provedor) > 1:
        print("\n  por provedor:")
        for nome, c in sorted(tel.por_provedor.items(), key=lambda kv: -kv[1].faturavel):
            print(f"    {nome:<16} {fmt(c.faturavel):>8}  ({c.requisicoes} req)")
        print("    (volume, nao custo: preco por token difere entre provedores)")
    if tel.ferramentas:
        print("\n  ferramentas mais usadas:")
        for nome, n in sorted(tel.ferramentas.items(), key=lambda kv: -kv[1])[:6]:
            print(f"    {nome:<32} {n}")
    print("\n  por modelo:")
    for modelo, c in sorted(tel.por_modelo.items(), key=lambda kv: -kv[1].faturavel):
        print(f"    {modelo:<28} {fmt(c.faturavel):>7}  ({c.requisicoes} req)")

    if tel.recorte.get("sobrepostas"):
        print("\n  ATENCAO — este numero e LIMITE SUPERIOR, nao medida exata.")
        print("  O intervalo desta sprint divide dia(s) com:")
        for outra in tel.recorte["sobrepostas"]:
            print(f"    - {outra}")
        print("  Os transcripts datam por instante, mas a atribuicao a uma sprint")
        print("  so e confiavel ate o dia: consumo de um dia partilhado nao tem")
        print("  como ser repartido sem inventar rateio. Registre como teto.")
    elif tel.recorte.get("sprint"):
        print("\n  Recorte exclusivo: nenhuma outra sprint divide dia com esta.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
