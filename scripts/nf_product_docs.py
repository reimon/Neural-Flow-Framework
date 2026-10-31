#!/usr/bin/env python3
"""Diagnostico, aprovacao e estado da base documental do produto.

O modelo de cada papel vive em templates/product-docs e e instalado junto ao
projeto. O diagnostico e compartilhado pelo instalador, pelo dashboard e pelos
guards; nao depende de servicos de IA nem de bibliotecas externas.
"""

from __future__ import annotations

NF_GUARD_ASSINATURA = "neural-flow-framework"

import argparse
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

from nf_guards import (eh_placeholder, ler, secao, sem_acento, titulo_normalizado)

RAIZ_FRAMEWORK = Path(__file__).resolve().parent.parent
DIR_EXEMPLOS = Path(".neural-flow/product-examples")

# role -> (titulo, descricao, arquivo de modelo, secoes obrigatorias)
DOCUMENTOS = {
    "prd": ("PRD", "Requisitos, usuarios, funcionalidades e metas do produto.", "prd.md", (
        "Visao geral", "Problema e usuarios", "Metas e objetivos",
        "Funcionalidades e roadmap", "Requisitos funcionais",
        "Requisitos nao funcionais", "Experiencia do usuario",
        "Metricas de sucesso", "Criterios de aceite", "Limites e fora do escopo",
        "Decisoes pendentes", "Referencias",
    )),
    "trd": ("TRD", "Arquitetura, escolhas tecnicas, operacao e custo de manutencao.", "trd.md", (
        "Objetivo e fronteiras", "Arquitetura", "Componentes e responsabilidades",
        "Tecnologias e decisoes", "Integracoes e contratos", "Seguranca e privacidade",
        "Desempenho e disponibilidade", "Implantacao e operacao",
        "Custo de manutencao", "Modos de falha e recuperacao",
        "Decisoes pendentes e referencias",
    )),
    "app_flow": ("Fluxo do App", "Jornadas, navegacao, acesso e estados de erro.", "app-flow.md", (
        "Objetivo e limites", "Perfis e permissoes", "Mapa de navegacao",
        "Jornadas principais", "Estados alternativos e erros", "Acesso e autenticacao",
        "Inventario de telas", "Pendencias e referencias",
    )),
    "uiux": ("UI/UX Design", "Brief visual, componentes e especificacao das telas.", "uiux-design.md", (
        "Brief e principios", "Paleta de cores", "Tipografia", "Componentes e estados",
        "Telas", "Responsividade e acessibilidade", "Referencias e decisoes pendentes",
    )),
    "backend": ("Esquema Backend", "Entidades, campos, relacoes e autenticacao.", "backend-schema.md", (
        "Visao geral e fronteiras", "Entidades", "Tabelas, colecoes e campos",
        "Relacionamentos e integridade", "Acesso aos dados e contratos",
        "Autenticacao, sessoes e autorizacao", "Privacidade e seguranca",
        "Migracoes, backup e recuperacao", "Decisoes pendentes e referencias",
    )),
    "implementation_plan": ("Plano de implementacao", "Ordem de construcao com dependencias e aceite.", "implementation-plan.md", (
        "Definicao de pronto do produto", "Premissas, restricoes e fora do escopo",
        "Sequencia de implementacao", "Rastreabilidade e validacao",
        "Acompanhamento das sprints", "Riscos, decisoes pendentes e referencias",
    )),
}

ALIASES = {
    "prd": ("prd", "product-requirements", "product-requirements-document", "requisitos-produto"),
    "trd": ("trd", "technical-requirements", "technical-requirements-document", "requisitos-tecnicos"),
    "app_flow": ("app-flow", "app-flow", "user-flow", "user-journey", "fluxo-app", "fluxo-do-app"),
    "uiux": ("uiux", "ui-ux", "design-system", "design-brief", "ui-ux-design"),
    "backend": ("backend-schema", "backend-scheme", "database-schema", "data-model", "esquema-backend"),
    "implementation_plan": ("implementation-plan", "implementation-roadmap", "plano-implementacao", "plano-de-implementacao"),
}

RE_IMP = re.compile(r"\bIMP-\d{3,4}\b")
RE_REQ = re.compile(r"\bREQ-\d{3,4}\b")
RE_CA = re.compile(r"\bCA-\d{3,4}\b")
EXCLUIR = {".git", ".agents", ".claude", ".neural-flow", ".cursor", ".github",
           "node_modules", ".venv", "venv", "dist", "build_out",
           "__pycache__", "templates", "old", "archive", "archives"}


def carregar_config(root: Path) -> tuple[dict, str | None]:
    caminho = root / ".neural-flow.json"
    if not caminho.is_file():
        return {}, None
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {}, f".neural-flow.json invalido: {exc}"
    if not isinstance(dados, dict):
        return {}, ".neural-flow.json deve conter um objeto JSON"
    return dados, None


def _conteudo_util(linhas: list[str], faixa: tuple[int, int]) -> bool:
    instrucoes = ("descreva ", "explique ", "liste ", "registre ", "para cada ",
                  "substitua ", "use ids", "ids `", "inclua ", "marque cada ")
    exemplos = ("> exemplo", "exemplo:")
    bloco = linhas[faixa[0]:faixa[1]]
    for indice, bruto in enumerate(bloco):
        linha = bruto.strip()
        if not linha or linha.startswith(("#", ">", "<!--")):
            continue
        sem_md = re.sub(r"[`*_]", "", linha).strip(" |-:")
        normal = sem_acento(sem_md).lower()
        if not normal or eh_placeholder(sem_md):
            continue
        if any(p in normal for p in ("a preencher", "pendente", "aaaa-mm-dd", "<nome")):
            continue
        if any(normal.startswith(p) for p in instrucoes) or any(p in normal for p in exemplos):
            continue
        cells = [sem_acento(c.strip(" `*_" )).lower() for c in linha.split("|")] if "|" in linha else [normal]
        if cells and all(not c or set(c) <= set("-: ") for c in cells):
            continue
        if "|" in linha and indice + 1 < len(bloco) and re.fullmatch(
            r"\s*\|?\s*:?-{2,}:?\s*(?:\|\s*:?-{2,}:?\s*)+\|?\s*", bloco[indice + 1]
        ):
            continue
        if "|" in linha and any(p in normal for p in ("a preencher", "pendente", "aaaa-mm-dd", "<nome")):
            continue
        if "|" in linha and all(c in {"id", "funcionalidade", "usuario/necessidade", "versao",
                                       "prioridade", "evidencia", "item", "estimativa", "moeda/periodo",
                                       "premissas e volume", "fonte", "verificado em", "token", "valor",
                                       "uso", "contraste verificado", "familia/peso", "tamanho/altura",
                                       "componente", "variacao", "estado", "origem", "tipo",
                                       "obrigatorio", "restricao/indice", "entidade", "cardinalidade",
                                       "chave", "regra de exclusao", "ordem", "etapa/entregavel",
                                       "dependencias", "requisitos", "criterios de aceite"} for c in cells):
            continue
        if any(c and not eh_placeholder(c) and c not in {"id", "campo", "tipo"} for c in cells):
            return True
    return False


def _candidatos(root: Path) -> list[Path]:
    encontrados = []
    for caminho in root.rglob("*.md"):
        try:
            relativo = caminho.relative_to(root)
        except ValueError:
            continue
        if EXCLUIR & set(relativo.parts) or caminho.name.startswith("."):
            continue
        if caminho.is_file():
            encontrados.append(caminho)
    return sorted(encontrados)


def _cobertura(linhas: list[str], secoes: tuple[str, ...]) -> int:
    return sum(1 for titulo in secoes if secao(linhas, titulo) is not None)


def _resolver(root: Path, papel: str, config: dict, candidatos: list[Path]) -> tuple[Path | None, dict, list[str]]:
    definidos = config.get("documents", {}) if isinstance(config, dict) else {}
    mapeado = definidos.get(papel) if isinstance(definidos, dict) else None
    if mapeado is not None:
        if isinstance(mapeado, str):
            mapeado = {"path": mapeado}
        if not isinstance(mapeado, dict) or not isinstance(mapeado.get("path"), str):
            return None, {}, [f"mapeamento de {papel} invalido; informe path"]
        caminho = (root / mapeado["path"]).resolve()
        try:
            caminho.relative_to(root.resolve())
        except ValueError:
            return None, mapeado, ["o caminho mapeado precisa ficar dentro do projeto"]
        return caminho, mapeado, []

    titulo, _, _, secoes = DOCUMENTOS[papel]
    aliases = {sem_acento(a).lower().replace("_", "-") for a in ALIASES[papel]}
    pontuados = []
    for caminho in candidatos:
        stem = sem_acento(caminho.stem).lower().replace("_", "-").replace(" ", "-")
        linhas = ler(caminho) or []
        points = 100 if stem in aliases or stem.startswith(tuple(a + "-" for a in aliases)) else _cobertura(linhas, secoes)
        if points >= 2:
            pontuados.append((points, caminho))
    if not pontuados:
        return None, {}, []
    melhor = max(points for points, _ in pontuados)
    vencedores = [c for points, c in pontuados if points == melhor]
    if len(vencedores) != 1:
        return None, {}, ["mais de um documento corresponde; defina o mapeamento em .neural-flow.json: "
                         + ", ".join(str(p.relative_to(root)) for p in vencedores)]
    return vencedores[0], {}, []


def hash_documento(caminho: Path, root: Path, mapeamento: dict) -> str:
    texto = caminho.read_text(encoding="utf-8")
    # O acompanhamento das sprints pode mudar sem alterar o plano mestre aprovado.
    linhas = texto.splitlines()
    faixa = secao(linhas, "Acompanhamento das sprints")
    if faixa:
        linhas[faixa[0]:faixa[1]] = ["<estado-de-sprint-excluido-do-hash>"]
    normalizado = "\n".join(re.sub(r"\[(?:x|X| )\]", "[ ]", l) for l in linhas)
    payload = json.dumps({"path": str(caminho.relative_to(root)), "sections": mapeamento.get("sections", {}),
                          "content": normalizado}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def diagnostico(root: Path, exemplos_root: Path | None = None) -> dict:
    root = root.resolve()
    config, erro_config = carregar_config(root)
    produto = config.get("product_docs", {})
    ativo = isinstance(produto, dict) and produto.get("enabled") is True
    aprovados = produto.get("approvals", {}) if isinstance(produto, dict) else {}
    candidatos = _candidatos(root)
    exemplos_root = exemplos_root or root
    exemplos_dir = exemplos_root / DIR_EXEMPLOS
    if not exemplos_dir.is_dir():
        exemplos_dir = RAIZ_FRAMEWORK / "templates" / "product-docs"
        extensao = ".md"
    else:
        extensao = ".md.example"

    saida = []
    for papel, (titulo, descricao, modelo, secoes) in DOCUMENTOS.items():
        caminho, mapeamento, avisos = _resolver(root, papel, produto if isinstance(produto, dict) else {}, candidatos)
        itens_lacuna = list(avisos)
        estrutura = "ausente"
        revisao = "nao_aprovada"
        hash_atual = None
        relativos = []
        apro = aprovados.get(papel) if isinstance(aprovados, dict) else None
        waiver_hash = hashlib.sha256(
            ("nao-se-aplica:" + papel + ":" + str(apro.get("evidence", ""))).encode("utf-8")
        ).hexdigest() if isinstance(apro, dict) else None
        if caminho is None and isinstance(apro, dict) and apro.get("not_applicable") is True:
            if apro.get("sha256") == waiver_hash and apro.get("reviewer") and apro.get("evidence"):
                estrutura, revisao = "nao_se_aplica", "nao_se_aplica"
                itens_lacuna = ["nao se aplica: " + str(apro["evidence"])]
        if caminho is not None:
            relativo = str(caminho.relative_to(root))
            linhas = ler(caminho)
            if linhas is None:
                estrutura = "incompleto"
                itens_lacuna.append("nao foi possivel ler como UTF-8")
            else:
                estrutura = "completo"
                sec_map = mapeamento.get("sections", {}) if isinstance(mapeamento, dict) else {}
                for obrigatoria in secoes:
                    nome_real = sec_map.get(obrigatoria, obrigatoria)
                    faixa = secao(linhas, nome_real)
                    if faixa is None:
                        itens_lacuna.append(f"secao ausente: {obrigatoria}")
                        estrutura = "incompleto"
                    elif not _conteudo_util(linhas, faixa):
                        itens_lacuna.append(f"secao sem conteudo: {obrigatoria}")
                        estrutura = "incompleto"
                hash_atual = hash_documento(caminho, root,
                                            mapeamento if isinstance(mapeamento, dict) else {})
                apro = aprovados.get(papel) if isinstance(aprovados, dict) else None
                if estrutura == "completo" and isinstance(apro, dict):
                    if apro.get("not_applicable") is True and str(apro.get("evidence", "")).strip():
                        revisao = "nao_se_aplica"
                    elif apro.get("sha256") == hash_atual and apro.get("reviewer") and apro.get("evidence"):
                        revisao = "aprovada"
                    elif apro:
                        revisao = "alterado_apos_aprovacao"
                if estrutura == "completo" and revisao == "nao_aprovada":
                    revisao = "aguardando_revisao"
                relativos = [relativo]
        if itens_lacuna and estrutura == "ausente":
            estrutura = "ambiguo"
        if estrutura == "ausente":
            itens_lacuna.append("documento nao encontrado; use o exemplo para preparar a primeira versao")
        nome_exemplo = Path(modelo).stem + extensao
        exemplo = exemplos_dir / nome_exemplo
        if not exemplo.is_file():
            exemplo = exemplos_dir / modelo
        texto_exemplo = exemplo.read_text(encoding="utf-8") if exemplo.is_file() else None
        status = ("incompleto" if estrutura in {"incompleto", "ambiguo"} else
                  "ausente" if estrutura == "ausente" else
                  "alterado_apos_aprovacao" if revisao == "alterado_apos_aprovacao" else
                  "aprovado" if revisao in {"aprovada", "nao_se_aplica"} else "aguardando_revisao")
        saida.append({"id": papel, "titulo": titulo, "descricao": descricao,
                      "arquivo": relativos[0] if relativos else None, "candidatos": avisos,
                      "estrutura": estrutura, "revisao": revisao, "status": status,
                      "lacunas": itens_lacuna, "sha256": hash_atual,
                      "exemplo": texto_exemplo})

    issues = erros_plano(root, {"documents": saida})
    if erro_config:
        issues.insert(0, erro_config)
    valido = ativo and all(d["status"] == "aprovado" for d in saida) and not issues
    return {"enabled": ativo, "configuration_error": erro_config,
            "ready": valido, "documents": saida, "issues": issues}


def erros_plano(root: Path, docs: dict) -> list[str]:
    plano = next((d for d in docs["documents"] if d["id"] == "implementation_plan"), None)
    if not plano or plano["estrutura"] != "completo" or not plano["arquivo"]:
        return []
    erros = _validar_plano((root / plano["arquivo"]).resolve())
    prd = next(d for d in docs["documents"] if d["id"] == "prd")
    ids_req, ids_ca = [], []
    if prd.get("arquivo"):
        for linha in (root / prd["arquivo"]).read_text(encoding="utf-8").splitlines():
            match = re.match(r"^\s*\|\s*(REQ-\d{3,4})\s*\|", linha)
            if match:
                ids_req.append(match.group(1))
            match = re.match(r"^\s*[-*]\s*\*\*(CA-\d{3,4})\s*:", linha)
            if match:
                ids_ca.append(match.group(1))
    if len(ids_req) != len(set(ids_req)):
        erros.append("IDs REQ duplicados no PRD")
    if len(ids_ca) != len(set(ids_ca)):
        erros.append("IDs CA duplicados no PRD")
    ids_req, ids_ca = set(ids_req), set(ids_ca)
    linhas = (root / plano["arquivo"]).read_text(encoding="utf-8").splitlines()
    faixa = secao(linhas, "Sequencia de implementacao")
    if faixa:
        for linha in linhas[faixa[0]:faixa[1]]:
            cells = [c.strip().strip("`") for c in linha.strip().strip("|").split("|")]
            if len(cells) < 6 or not RE_IMP.fullmatch(cells[1]):
                continue
            for ident in RE_REQ.findall(cells[4]):
                if ident not in ids_req:
                    erros.append(f"{cells[1]} referencia requisito inexistente: {ident}")
            for ident in RE_CA.findall(cells[5]):
                if ident not in ids_ca:
                    erros.append(f"{cells[1]} referencia criterio inexistente: {ident}")
    return erros


def validar_rastreabilidade_sprint(linhas: list[str], root: Path) -> list[str]:
    """Confere os IDs de plano e os criterios em cada acao de implementacao."""
    config, erro = carregar_config(root)
    if erro:
        return [erro]
    produto = config.get("product_docs", {})
    docs = diagnostico(root)
    plano = next((d for d in docs["documents"] if d["id"] == "implementation_plan"), None)
    if not isinstance(produto, dict) or not isinstance(plano, dict) or not plano.get("arquivo"):
        return ["plano mestre nao encontrado"]
    plano_linhas = ler(root / plano["arquivo"]) or []
    faixa = secao(plano_linhas, "Sequencia de implementacao")
    ids_imp = set()
    ids_ca = set()
    ids_req_plano = set()
    if faixa:
        for linha in plano_linhas[faixa[0]:faixa[1]]:
            cells = [c.strip().strip("`") for c in linha.strip().strip("|").split("|")]
            if len(cells) >= 6 and RE_IMP.fullmatch(cells[1]):
                ids_imp.add(cells[1])
                ids_req_plano.update(RE_REQ.findall(cells[4]))
                ids_ca.update(RE_CA.findall(cells[5]))
    faixa_prd = next((d for d in docs["documents"] if d["id"] == "prd"), None)
    ids_prd = set()
    if faixa_prd and faixa_prd.get("arquivo"):
        prd_linhas = ler(root / faixa_prd["arquivo"]) or []
        for linha in prd_linhas:
            m = re.match(r"^\s*\|\s*(CA-\d{3,4})\s*\|", linha)
            if m:
                ids_prd.add(m.group(1))
            m = re.match(r"^\s*[-*]\s*\*\*(CA-\d{3,4})\s*:", linha)
            if m:
                ids_prd.add(m.group(1))
    erros = []
    faixa_acoes = secao(linhas, "Checklist de Acoes")
    if not faixa_acoes:
        return ["secao 'Checklist de Acoes' ausente"]
    for numero, linha in enumerate(linhas[faixa_acoes[0]:faixa_acoes[1]], faixa_acoes[0] + 1):
        m = RE_IMP.search(linha)
        if not re.match(r"^\s*[-*]\s*\[[ xX]\]\s*\d+(?:\.\d+)*\s+", linha):
            continue
        if not m:
            erros.append(f"linha {numero}: acao sem referencia IMP-###")
            continue
        if m.group(0) not in ids_imp:
            erros.append(f"linha {numero}: item inexistente no plano: {m.group(0)}")
        refs_req = set(RE_REQ.findall(linha))
        refs_ca = set(RE_CA.findall(linha))
        if not refs_req and not refs_ca:
            erros.append(f"linha {numero}: acao precisa referenciar REQ-### ou CA-###")
        for ident in refs_req:
            if ident not in ids_req_plano:
                erros.append(f"linha {numero}: requisito fora do plano mestre: {ident}")
        for ident in RE_CA.findall(linha):
            if ident not in ids_ca and ident not in ids_prd:
                erros.append(f"linha {numero}: criterio de aceite inexistente: {ident}")
    return erros


def _validar_plano(caminho: Path) -> list[str]:
    linhas = caminho.read_text(encoding="utf-8").splitlines()
    faixa = secao(linhas, "Sequencia de implementacao")
    if not faixa:
        return []
    ids = []
    ordens = []
    dependencias = {}
    for linha in linhas[faixa[0]:faixa[1]]:
        celulas = [c.strip().strip("`") for c in linha.strip().strip("|").split("|")]
        if len(celulas) < 6 or not celulas[0].isdigit() or not RE_IMP.fullmatch(celulas[1]):
            continue
        ordem, ident = int(celulas[0]), celulas[1]
        ids.append(ident)
        ordens.append((ordem, ident))
        dependencias[ident] = set(RE_IMP.findall(celulas[3]))
        if (eh_placeholder(celulas[2]) or eh_placeholder(celulas[3])
                or eh_placeholder(celulas[4]) or eh_placeholder(celulas[5])):
            erros_item = f"item {ident} sem entregavel, dependencia, requisito ou criterio de aceite"
            return [erros_item]
    erros = []
    if not ids:
        erros.append("sequencia sem itens IMP numerados")
    if len(ids) != len(set(ids)):
        erros.append("IDs IMP duplicados no plano")
    if len(ordens) != len(set(n for n, _ in ordens)):
        erros.append("ordem duplicada no plano")
    if ordens and [n for n, _ in ordens] != list(range(1, len(ordens) + 1)):
        erros.append("a ordem do plano precisa ser crescente e sequencial a partir de 1")
    rank = {ident: ordem for ordem, ident in ordens}
    for ident, deps in dependencias.items():
        for dep in deps:
            if dep not in rank:
                erros.append(f"{ident} depende de item inexistente: {dep}")
            elif rank[dep] >= rank[ident]:
                erros.append(f"dependencia {dep} precisa anteceder {ident}")
    return erros


def _salvar_aprovacao(root: Path, papel: str, reviewer: str, evidencia: str,
                      nao_se_aplica: bool = False) -> tuple[bool, str]:
    relatorio = diagnostico(root)
    doc = next((d for d in relatorio["documents"] if d["id"] == papel), None)
    if doc is None:
        return False, f"papel documental desconhecido: {papel}"
    if nao_se_aplica and doc["arquivo"]:
        return False, f"{papel}: ha documento associado; remova o mapeamento antes de registrar ausencia"
    if nao_se_aplica and doc.get("candidatos"):
        return False, f"{papel}: resolva os documentos candidatos antes de justificar ausencia"
    if not nao_se_aplica and (not doc["arquivo"] or doc["estrutura"] != "completo"):
        return False, f"{papel}: documento ausente ou estruturalmente incompleto"
    if not reviewer.strip() or not evidencia.strip() or not doc["sha256"]:
        return False, "revisor, evidencia e hash valido sao obrigatorios"
    root_config, erro = carregar_config(root)
    if erro:
        return False, erro
    produto = root_config.setdefault("product_docs", {"enabled": True, "documents": {}, "approvals": {}})
    produto["enabled"] = True
    aprovacoes = produto.setdefault("approvals", {})
    digest = (hashlib.sha256(("nao-se-aplica:" + papel + ":" + evidencia.strip()).encode("utf-8")).hexdigest()
              if nao_se_aplica else doc["sha256"])
    aprovacoes[papel] = {"sha256": digest, "reviewer": reviewer.strip(),
                         "date": date.today().isoformat(), "evidence": evidencia.strip(),
                         "not_applicable": nao_se_aplica}
    caminho = root / ".neural-flow.json"
    caminho.write_text(json.dumps(root_config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True, f"{papel} aprovado para o hash {doc['sha256']}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Diagnostica e registra revisao da base documental do produto.")
    ap.add_argument("--root", default=".", help="raiz do projeto")
    ap.add_argument("--format", choices=("text", "json"), default="text")
    ap.add_argument("--approve", choices=tuple(DOCUMENTOS), help="registra aprovacao para um documento completo")
    ap.add_argument("--not-applicable", choices=tuple(DOCUMENTOS), help="registra ausencia justificada, revisada e aprovada")
    ap.add_argument("--by", help="pessoa que revisou")
    ap.add_argument("--evidence", help="referencia da aprovacao explicita")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    if args.approve or args.not_applicable:
        if args.approve and args.not_applicable:
            ap.error("use --approve ou --not-applicable, nao ambos")
        papel = args.approve or args.not_applicable
        if not args.by or not args.evidence:
            ap.error("aprovacao exige --by e --evidence")
        ok, message = _salvar_aprovacao(root, papel, args.by, args.evidence,
                                        nao_se_aplica=bool(args.not_applicable))
        print(message)
        return 0 if ok else 1
    relatorio = diagnostico(root)
    for issue in erros_plano(root, relatorio):
        relatorio.setdefault("issues", []).append(issue)
    if args.format == "json":
        print(json.dumps(relatorio, ensure_ascii=False, indent=2))
    else:
        print("Base documental: " + ("pronta" if relatorio["ready"] else "em preparacao"))
        if not relatorio["enabled"]:
            print("Controle ainda nao ativado neste projeto.")
        if relatorio.get("configuration_error"):
            print("Configuracao: " + relatorio["configuration_error"])
        for doc in relatorio["documents"]:
            print(f"- {doc['titulo']}: {doc['status']}" + (f" ({doc['arquivo']})" if doc["arquivo"] else ""))
            for lacuna in doc["lacunas"]:
                print(f"  - {lacuna}")
        for issue in relatorio.get("issues", []):
            print("- Plano: " + issue)
    return 0


if __name__ == "__main__":
    sys.exit(main())
