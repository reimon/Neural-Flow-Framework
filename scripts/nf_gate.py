#!/usr/bin/env python3
"""
Neural-Flow Framework — orquestrador dos guards
===============================================
Um comando para rodar todos os gates executaveis do framework.

    python scripts/nf_gate.py                 # roda todos
    python scripts/nf_gate.py sprint adr      # roda so os indicados
    python scripts/nf_gate.py --list          # lista os guards disponiveis
    python scripts/nf_gate.py --root <dir>    # valida outra arvore (usado pelo hook)

Exit 0 = todos PASS. Exit 1 = pelo menos um FAIL (imprime todos, nao para no
primeiro: o dev corrige tudo de uma vez em vez de descobrir de um em um).

Sem dependencia externa: roda em qualquer projeto, qualquer stack.
"""

from __future__ import annotations

import argparse
import json
import os
from html import escape
import re
import subprocess
import sys
from pathlib import Path

# Assinatura de origem. O `nf_gate` so executa arquivo que a carrega — projeto
# brownfield pode ter um script homonimo com outra interface, e chama-lo com os
# nossos argumentos produz erro de uso confuso em vez de diagnostico.
NF_GUARD_ASSINATURA = "neural-flow-framework"

AQUI = Path(__file__).resolve().parent

# nome → (script, protocolo, o que garante)
GUARDS: dict[str, tuple[str, str, str]] = {
    "sprint": (
        "validate_sprint_state.py",
        "state-protocol",
        "snapshot completo, status sem ambiguidade, escopo sensivel em A0/A1",
    ),
    "budget": (
        "validate_token_budget.py",
        "token-circuit-breaker",
        "budget declarado, consumo registrado, estouro com mitigacao",
    ),
    "context": (
        "validate_context_sources.py",
        "context-vector",
        "referencia resolve, decisao cita fonte, evidencia real",
    ),
    "adr": (
        "validate_adr.py",
        "adr-governance",
        "numeracao unica, sem referencia pendurada nem ciclo de supersecao",
    ),
    "spec": (
        "validate_module_spec.py",
        "spec-first",
        "estrutura minima de spec, invariantes com ID, aceite numerado",
    ),
    "calibration": (
        "validate_calibration.py",
        "calibration",
        "confianca declarada, BAIXA nao fecha item, irreversivel nao vira registro",
    ),
    "agentes": (
        "validate_agent_entrypoints.py",
        "agent-entrypoints",
        "toda ferramenta de IA tem porta de entrada apontando para AGENTS.md; "
        "indice de regras em dia",
    ),
}


def config(raiz: Path) -> dict:
    caminho = raiz / ".neural-flow.json"
    if caminho.is_file():
        try:
            dados = json.loads(caminho.read_text(encoding="utf-8"))
            if isinstance(dados, dict):
                return dados
            print("aviso: .neural-flow.json deve conter um objeto", file=sys.stderr)
        except json.JSONDecodeError as exc:
            print(f"aviso: .neural-flow.json invalido ({exc})", file=sys.stderr)
    return {}


def eh_nosso(script: Path) -> bool:
    """Projeto brownfield pode ter script homonimo com outra interface.

    Chamar o validador do projeto com os nossos argumentos produz um erro de uso
    ("the following arguments are required: --module") que parece defeito do
    framework — quando na verdade sao duas ferramentas diferentes com o mesmo
    nome. A assinatura resolve isso antes de executar qualquer coisa.
    """
    try:
        return "NF_GUARD_ASSINATURA" in script.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False


def resolver(raiz: Path, script: str) -> tuple[Path | None, bool]:
    """Devolve (caminho, e_nosso). Procura o nome namespaced antes do simples:
    quando ha colisao, o instalador grava o nosso como `nf_<nome>`."""
    for nome in (f"nf_{script}", script):
        candidato = raiz / "scripts" / nome
        if candidato.is_file():
            return candidato, eh_nosso(candidato)
    proprio = AQUI / script
    if proprio.is_file():
        return proprio, True
    return None, False


def relativo(raiz: Path, arquivo: str) -> str:
    caminho = Path(arquivo)
    return str(caminho.relative_to(raiz)) if caminho.is_relative_to(raiz) else arquivo


def ler_saida_legada(raiz: Path, saida: str, resultado: dict) -> None:
    """Conserva a evidencia publicada pelos guards de texto e pelos validadores proprios."""
    for linha in saida.splitlines():
        texto = linha.strip()
        if texto.startswith("verificado: "):
            resultado["arquivos"].append(relativo(raiz, texto.removeprefix("verificado: ")))
            continue
        m = re.fullmatch(r"\[([A-Z]+\d+)\] (.+?) — (.+)", texto)
        if m:
            arquivo, sep, numero = m[2].rpartition(":")
            tem_linha = bool(sep and numero.isdigit())
            resultado["achados"].append({
                "codigo": m[1], "arquivo": relativo(raiz, arquivo if tem_linha else m[2]),
                "linha": int(numero) if tem_linha else None, "msg": m[3],
            })


def rodar_externo(raiz: Path, spec: dict, resultado: dict, log) -> None:
    comando = spec.get("comando")
    if not comando:
        resultado["motivo"] = "Validador e do projeto, nao do framework. Configure o comando em .neural-flow.json."
        return
    if not isinstance(comando, list) or not all(isinstance(a, str) for a in comando):
        raise ValueError("comando do validador proprio deve ser uma lista de argumentos")
    padrao = spec.get("por_modulo")
    alvos = [""]
    if padrao:
        alvos = [m[1] for p in sorted(raiz.glob(padrao))
                 if (m := re.search(r"(\d{1,3})", p.name))]
        if not alvos:
            resultado.update(estado="sem_artefato", motivo=f"Nenhum modulo casou com {padrao}")
            return

    resultado["estado"] = "conforme"
    falhas = []
    for alvo in alvos:
        cmd = [a.replace("{root}", str(raiz)).replace("{modulo}", alvo) for a in comando]
        proc = subprocess.run(cmd, cwd=raiz, capture_output=True, text=True)
        saida = proc.stdout + "\n" + proc.stderr
        ler_saida_legada(raiz, saida, resultado)
        if log:
            log(saida, proc.returncode != 0)
        if proc.returncode:
            detalhe = f"modulo {alvo}: " if alvo else ""
            falhas.append(f"{detalhe}retorno {proc.returncode}")
    if falhas:
        resultado.update(estado="falhou", motivo="Validador externo: " + ", ".join(falhas))


def rodar_interno(raiz: Path, caminho: Path, resultado: dict, log) -> None:
    proc = subprocess.run(
        [sys.executable, str(caminho), "--root", str(raiz)],
        capture_output=True, text=True, env={**os.environ, "NF_GUARD_FORMATO": "json"},
    )
    linhas = proc.stdout.splitlines()
    try:
        evidencia = json.loads(linhas[-1]) if linhas else None
    except json.JSONDecodeError:
        evidencia = None
    if not isinstance(evidencia, dict) or not {"arquivos", "achados"} <= evidencia.keys():
        # Instalacoes anteriores escrevem somente o relatorio de terminal.
        # So uma confirmacao explicita conta como conformidade.
        ler_saida_legada(raiz, proc.stdout + "\n" + proc.stderr, resultado)
        if log:
            log(proc.stdout + proc.stderr, proc.returncode != 0)
        if proc.returncode:
            resultado.update(estado="falhou", motivo=f"Validador retornou {proc.returncode}")
        elif "nada a validar" in proc.stdout:
            resultado["estado"] = "sem_artefato"
        elif re.search(r"^[^\n]+: PASS — ", proc.stdout, re.M):
            resultado["estado"] = "conforme"
        else:
            resultado.update(estado="falhou", motivo="Validador terminou sem evidencia reconhecivel")
        return

    if log:
        log("\n".join(linhas[:-1]) + proc.stderr, proc.returncode != 0)
    resultado["arquivos"] = [relativo(raiz, p) for p in evidencia["arquivos"]]
    for achado in evidencia["achados"]:
        resultado["achados"].append({**achado, "arquivo": relativo(raiz, achado["arquivo"])})
    if proc.returncode or resultado["achados"]:
        resultado["estado"] = "falhou"
    elif resultado["arquivos"]:
        resultado["estado"] = "conforme"
    else:
        resultado["estado"] = "sem_artefato"


def executar(raiz: Path, escolhidos, *, externos: bool = True, log=None) -> list[dict]:
    raiz = raiz.resolve()
    cfg = config(raiz)
    resultados = []
    for nome in escolhidos:
        script, protocolo, descricao = GUARDS[nome]
        r = {"nome": nome, "protocolo": protocolo, "descricao": descricao,
             "estado": "nao_executado", "arquivos": [], "achados": [], "motivo": ""}
        caminho, nosso = resolver(raiz, script)
        try:
            configurados = cfg.get("guards", {})
            if not isinstance(configurados, dict) or not isinstance(configurados.get(nome, {}), dict):
                raise ValueError("guards em .neural-flow.json deve mapear cada nome para um objeto")
            spec = configurados.get(nome, {})
            if caminho is None:
                r["motivo"] = "Validador nao instalado"
            elif nosso:
                rodar_interno(raiz, caminho, r, log)
            proprio = raiz / "scripts" / script
            lado_a_lado = (caminho == proprio.with_name(f"nf_{script}") and proprio.is_file()
                           and not eh_nosso(proprio) and spec.get("comando"))
            if caminho is not None and (not nosso or lado_a_lado):
                externo = {"estado": "nao_executado", "motivo": "", "arquivos": [], "achados": []}
                if externos:
                    rodar_externo(raiz, spec, externo, log)
                else:
                    externo["motivo"] = "Validador do projeto. Consulte o relatorio gerado pelo gate."
                if not lado_a_lado:
                    r.update(externo)
                else:
                    estados = (r["estado"], externo["estado"])
                    r["motivo"] = " ".join(filter(None, (
                        f"Framework: {estados[0]}.", r["motivo"],
                        f"Projeto: {estados[1]}.", externo["motivo"],
                    )))
                    r["estado"] = next(e for e in ("falhou", "nao_executado", "conforme", "sem_artefato")
                                       if e in estados)
                    r["arquivos"].extend(externo["arquivos"])
                    r["achados"].extend(externo["achados"])
        except (OSError, ValueError, TypeError) as exc:
            r.update(estado="falhou", motivo=f"Falha ao executar o validador: {exc}")
        resultados.append(r)
    return resultados


ROTULOS = {"conforme": "conforme", "falhou": "falhou", "sem_artefato": "sem artefato",
           "nao_executado": "nao executado"}


def local_achado(a: dict) -> str:
    return f"{a['arquivo']}:{a['linha']}" if a["linha"] else a["arquivo"]


def texto(guards: list[dict], quiet: bool) -> None:
    for g in guards:
        if not quiet:
            print(f"\n=== {g['nome']} ({g['protocolo']}) ===")
            for caminho in g["arquivos"]:
                print(f"  verificado: {caminho}")
        for a in g["achados"]:
            print(f"  [{a['codigo']}] {local_achado(a)} — {a['msg']}")
        print(f"  {g['nome']}: {ROTULOS[g['estado']]}" + (f" — {g['motivo']}" if g["motivo"] else ""))
    totais = {e: sum(g["estado"] == e for g in guards) for e in ROTULOS}
    status = "FAIL" if totais["falhou"] else "PASS"
    print(f"nf_gate: {status} — {totais['conforme']} guard(s) conforme; "
          f"{totais['falhou']} falhou; {totais['sem_artefato']} sem artefato; "
          f"{totais['nao_executado']} inativo(s) (nao executado)")


def resumo_github(guards: list[dict]) -> str:
    indice = ".neural-flow/indice-regras.md"
    if os.environ.get("GITHUB_REPOSITORY") and os.environ.get("GITHUB_SHA"):
        servidor = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
        indice = f"{servidor}/{os.environ['GITHUB_REPOSITORY']}/blob/{os.environ['GITHUB_SHA']}/{indice}"
    linhas = ["## Neural-Flow", "", f"[Regras da revisao verificada]({indice})", "",
              "| Guard | Resultado | Arquivos identificados |",
              "| --- | --- | ---: |"]
    for g in guards:
        linhas.append(f"| {g['nome']} | {ROTULOS[g['estado']]} | {len(g['arquivos'])} |")
    # O conteudo dos projetos pode conter HTML ou Markdown. Em pre, trate-o como texto.
    detalhes = []
    for g in guards:
        if g["motivo"]:
            detalhes.append(f"{g['nome']}: {g['motivo']}")
        for a in g["achados"]:
            detalhes.append(f"{g['nome']} [{a['codigo']}] {local_achado(a)} — {a['msg']}")
    if detalhes:
        linhas += ["", "<pre>" + escape("\n".join(detalhes)) + "</pre>"]
    return "\n".join(linhas) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Roda os gates executaveis do Neural-Flow Framework.")
    ap.add_argument("guards", nargs="*", help="quais rodar (default: todos)")
    ap.add_argument("--root", default=".")
    ap.add_argument("--list", action="store_true", help="lista os guards e sai")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--format", choices=("text", "json"), default="text")
    ap.add_argument("--resumo-github", type=Path, help="anexa a evidencia ao resumo do job")
    args = ap.parse_args()
    if args.list:
        if args.format == "json":
            print(json.dumps([{"nome": nome, "protocolo": proto, "descricao": descricao}
                              for nome, (_, proto, descricao) in GUARDS.items()], ensure_ascii=False))
            return 0
        print("Guards do Neural-Flow:\n")
        for nome, (_, protocolo, descricao) in GUARDS.items():
            print(f"  {nome:<12} {protocolo:<22} {descricao}")
        return 0
    escolhidos = args.guards or list(GUARDS)
    desconhecidos = [g for g in escolhidos if g not in GUARDS]
    if desconhecidos:
        ap.error(f"guard desconhecido: {', '.join(desconhecidos)}")

    def log(mensagem: str, falhou: bool) -> None:
        if mensagem.strip() and (not args.quiet or falhou):
            print(mensagem.rstrip(), file=sys.stderr if args.format == "json" else sys.stdout)

    guards = executar(Path(args.root), escolhidos, log=log)
    if args.format == "json":
        print(json.dumps({"versao": 1, "guards": guards}, ensure_ascii=False, indent=2))
    else:
        texto(guards, args.quiet)
    if args.resumo_github:
        with args.resumo_github.open("a", encoding="utf-8") as f:
            f.write(resumo_github(guards))
    return int(any(g["estado"] == "falhou" for g in guards))


if __name__ == "__main__":
    sys.exit(main())
