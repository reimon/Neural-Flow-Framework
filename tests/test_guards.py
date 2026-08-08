#!/usr/bin/env python3
"""
Neural-Flow Framework — testes dos guards
=========================================
O framework diz que diretriz sem guard nao esta pronta. O corolario e que
**guard sem teste tambem nao esta**: quem alterar um regex daqui precisa que algo
o pegue.

Estes testes provam as duas direcoes, que e o que separa cobertura real de verde
decorativo:

  * fixture CONFORME → todo guard passa (exit 0);
  * fixture VIOLADOR → todo guard falha (exit 1) **e emite os codigos esperados**.

Verificar so a primeira direcao seria o falso positivo que o protocolo de
Calibracao proibe: um guard quebrado que nunca reprova nada passaria no teste.

Rodar:
    python3 -m unittest discover -s tests -v
    python3 tests/test_guards.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SCRIPTS = RAIZ / "scripts"
CONFORME = RAIZ / "tests" / "fixtures" / "conforme"
VIOLADOR = RAIZ / "tests" / "fixtures" / "violador"

sys.path.insert(0, str(SCRIPTS))

# guard → (script, codigos que a fixture violador tem de disparar)
GUARDS = {
    "sprint": ("validate_sprint_state.py", {"S1", "S2", "S4", "S5"}),
    "budget": ("validate_token_budget.py", {"B3"}),
    "context": ("validate_context_sources.py", {"V1"}),
    "adr": ("validate_adr.py", {"A1", "A3", "A4", "A5", "A6"}),
    "spec": ("validate_module_spec.py", {"P1", "P2", "P3", "P4"}),
    "calibration": ("validate_calibration.py", {"C1", "C2", "C3", "C4", "C5", "C6"}),
}

RE_CODIGO = re.compile(r"^\s*\[([A-Z]\d)\]", re.MULTILINE)


def rodar(script: str, raiz: Path) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / script), "--root", str(raiz)],
        capture_output=True, text=True,
    )
    return proc.returncode, proc.stdout + proc.stderr


class TestFixtureConforme(unittest.TestCase):
    """Projeto que segue os protocolos nao pode ser reprovado (sem falso positivo)."""

    def test_todo_guard_passa(self) -> None:
        for guard, (script, _) in GUARDS.items():
            with self.subTest(guard=guard):
                codigo, saida = rodar(script, CONFORME)
                self.assertEqual(
                    codigo, 0,
                    f"guard '{guard}' reprovou a fixture conforme:\n{saida}",
                )
                self.assertNotIn("FAIL", saida)


class TestFixtureViolador(unittest.TestCase):
    """Projeto que viola os protocolos TEM de ser reprovado (sem falso negativo)."""

    def test_todo_guard_reprova(self) -> None:
        for guard, (script, _) in GUARDS.items():
            with self.subTest(guard=guard):
                codigo, saida = rodar(script, VIOLADOR)
                self.assertEqual(
                    codigo, 1,
                    f"guard '{guard}' NAO reprovou a fixture violador:\n{saida}",
                )

    def test_codigos_esperados_disparam(self) -> None:
        """Nao basta reprovar: tem de reprovar pelo motivo certo."""
        for guard, (script, esperados) in GUARDS.items():
            with self.subTest(guard=guard):
                _, saida = rodar(script, VIOLADOR)
                emitidos = set(RE_CODIGO.findall(saida))
                faltando = esperados - emitidos
                self.assertFalse(
                    faltando,
                    f"guard '{guard}' nao emitiu {sorted(faltando)}; "
                    f"emitiu {sorted(emitidos)}\n{saida}",
                )


class TestRegrasCriticas(unittest.TestCase):
    """Casos que codificam regra de seguranca do manifesto — nao podem regredir."""

    def test_escopo_sensivel_em_a3_e_bloqueado(self) -> None:
        _, saida = rodar("validate_sprint_state.py", VIOLADOR)
        self.assertIn("S4", saida)
        self.assertIn("A0/A1", saida)

    def test_ciclo_de_supersecao_e_detectado(self) -> None:
        _, saida = rodar("validate_adr.py", VIOLADOR)
        self.assertIn("ciclo de supersecao", saida)

    def test_baixa_nao_fecha_item(self) -> None:
        _, saida = rodar("validate_calibration.py", VIOLADOR)
        self.assertIn("C2", saida)
        self.assertIn("BAIXA nunca fecha item", saida)

    def test_irreversivel_exige_humano(self) -> None:
        _, saida = rodar("validate_calibration.py", VIOLADOR)
        self.assertIn("C5", saida)

    def test_budget_estourado_sem_mitigacao(self) -> None:
        _, saida = rodar("validate_token_budget.py", VIOLADOR)
        self.assertIn("B3", saida)
        self.assertIn("130%", saida)

    def test_consumo_em_andamento_com_crases_e_aceito(self) -> None:
        """Regressao: o template escreve valores em crases.

        Sem remover a decoracao markdown, `em andamento` nao casava com o estado
        literal e o guard acusava B2 em toda sprint aberta — ou seja, em toda
        sprint de todo adotante que usasse o template como esta escrito.
        """
        import tempfile

        sprint = """# Sprint 9
## Snapshot Operacional
- App/Escopo: `x`
- Status: `em andamento`
- Data de inicio: `2026-08-01`
- Data planejada de conclusao: `2026-08-15`
- Ultima atualizacao: `2026-08-08`
- Nivel de autonomia: `A1`
- Blocker principal: `nenhum`
- Proxima acao: `seguir`
## FinOps de Tokens
- Token budget: `1M`
- Consumo observado: `em andamento`
"""
        with tempfile.TemporaryDirectory() as tmp:
            destino = Path(tmp) / "docs" / "sprints"
            destino.mkdir(parents=True)
            (destino / "sprint-09.md").write_text(sprint, encoding="utf-8")
            codigo, saida = rodar("validate_token_budget.py", Path(tmp))
            self.assertEqual(codigo, 0, f"B2 falso positivo com crases:\n{saida}")


class TestProjetoSemArtefato(unittest.TestCase):
    """O guard trava quem usa errado — nao atrapalha quem nao usa."""

    def test_diretorio_vazio_passa(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            for guard, (script, _) in GUARDS.items():
                with self.subTest(guard=guard):
                    codigo, saida = rodar(script, Path(tmp))
                    self.assertEqual(codigo, 0, f"{guard} reprovou projeto vazio:\n{saida}")

    def test_template_nao_preenchido_e_ignorado(self) -> None:
        import shutil
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            destino = Path(tmp) / "build"
            destino.mkdir()
            shutil.copy(RAIZ / "templates/loop/PLANO-template.md", destino / "PLANO.md")
            shutil.copy(
                RAIZ / "templates/loop/DIVERGENCIAS-template.md",
                destino / "DIVERGENCIAS.md",
            )
            codigo, saida = rodar("validate_calibration.py", Path(tmp))
            self.assertEqual(codigo, 0, saida)


class TestTemplatesProduzemArtefatoConforme(unittest.TestCase):
    """O template preenchido tem de passar nos guards.

    Regressao real: `sprint-template.md` trazia `../../docs/Manifest-Dev-AI.md`,
    caminho relativo ao lugar de origem. Copiado para `docs/sprints/` no projeto
    do adotante, virava referencia pendurada — e o PRIMEIRO commit de quem
    seguisse o guia era bloqueado por defeito nosso, nao dele.
    """

    def test_sprint_template_preenchido_passa(self) -> None:
        import tempfile

        preenchimentos = {
            "- App/Escopo: `a preencher`": "- App/Escopo: `api de faturamento`",
            "- Status: `planejada`": "- Status: `em andamento`",
            "- Data de inicio: `YYYY-MM-DD`": "- Data de inicio: `2026-08-08`",
            "- Data planejada de conclusao: `YYYY-MM-DD`":
                "- Data planejada de conclusao: `2026-08-22`",
            "- Ultima atualizacao: `YYYY-MM-DD`": "- Ultima atualizacao: `2026-08-08`",
            "- Proxima acao: `a preencher`": "- Proxima acao: `modelar tabela`",
            "- Token budget: `a preencher`": "- Token budget: `500k`",
            "## Escopo incluido\n\n- Item 1\n- Item 2":
                "## Escopo incluido\n\n- Modelagem de faturas",
            "## Fora do escopo\n\n- Item 1\n- Item 2":
                "## Fora do escopo\n\n- Integracao com gateway",
        }
        texto = (RAIZ / "templates/sprint-template.md").read_text(encoding="utf-8")
        for de, para in preenchimentos.items():
            self.assertIn(de, texto, f"template mudou; preenchimento {de!r} nao encontrado")
            texto = texto.replace(de, para)

        with tempfile.TemporaryDirectory() as tmp:
            destino = Path(tmp) / "docs" / "sprints"
            destino.mkdir(parents=True)
            (destino / "sprint-01.md").write_text(texto, encoding="utf-8")
            for guard in ("sprint", "budget", "context"):
                with self.subTest(guard=guard):
                    script = GUARDS[guard][0]
                    codigo, saida = rodar(script, Path(tmp))
                    self.assertEqual(
                        codigo, 0,
                        f"template preenchido reprovado por '{guard}':\n{saida}",
                    )


class TestTextoDoTemplateNaoDesligaGuard(unittest.TestCase):
    """Regressao critica: a nota explicativa do template desligava o guard.

    S4 e B3 procuravam as palavras "excecao formal" / "mitigacao" em qualquer
    lugar do documento. O `sprint-template.md` explica essas regras no proprio
    corpo — entao toda sprint criada a partir dele nascia com S4 e B3
    permanentemente suprimidos. Um guard que nunca reprova e pior que nenhum:
    da a sensacao de cobertura sem a cobertura.

    Agora a excecao/mitigacao tem de ser um CAMPO com conteudo real.
    """

    def _sprint_do_template(self, **trocas: str) -> str:
        texto = (RAIZ / "templates/sprint-template.md").read_text(encoding="utf-8")
        base = {
            "- App/Escopo: `a preencher`": "- App/Escopo: `rotacao de segredo no key vault`",
            "- Status: `planejada`": "- Status: `em andamento`",
            "- Data de inicio: `YYYY-MM-DD`": "- Data de inicio: `2026-08-08`",
            "- Data planejada de conclusao: `YYYY-MM-DD`":
                "- Data planejada de conclusao: `2026-08-22`",
            "- Ultima atualizacao: `YYYY-MM-DD`": "- Ultima atualizacao: `2026-08-08`",
            "- Proxima acao: `a preencher`": "- Proxima acao: `rotacionar`",
            "- Token budget: `a preencher`": "- Token budget: `500k`",
            "## Escopo incluido\n\n- Item 1\n- Item 2": "## Escopo incluido\n\n- Rotacao",
            "## Fora do escopo\n\n- Item 1\n- Item 2": "## Fora do escopo\n\n- Automacao",
        }
        base.update(trocas)
        for de, para in base.items():
            texto = texto.replace(de, para)
        return texto

    def _rodar_em_tmp(self, texto: str, script: str) -> tuple[int, str]:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            destino = Path(tmp) / "docs" / "sprints"
            destino.mkdir(parents=True)
            (destino / "sprint-01.md").write_text(texto, encoding="utf-8")
            return rodar(script, Path(tmp))

    def test_s4_reprova_a3_em_escopo_sensivel_vindo_do_template(self) -> None:
        texto = self._sprint_do_template(
            **{"- Nivel de autonomia: `A1`": "- Nivel de autonomia: `A3`"}
        )
        self.assertIn("Excecao formal", texto, "a nota do template deve continuar la")
        codigo, saida = self._rodar_em_tmp(texto, "validate_sprint_state.py")
        self.assertEqual(codigo, 1, f"S4 nao reprovou A3 em escopo sensivel:\n{saida}")
        self.assertIn("S4", saida)

    def test_s4_aceita_a3_com_excecao_formal_declarada_como_campo(self) -> None:
        texto = self._sprint_do_template(
            **{
                "- Nivel de autonomia: `A1`":
                    "- Nivel de autonomia: `A3`\n"
                    "- Excecao formal: aprovada por seguranca em 2026-08-08, ticket SEC-42",
            }
        )
        codigo, saida = self._rodar_em_tmp(texto, "validate_sprint_state.py")
        self.assertEqual(codigo, 0, f"excecao formal declarada nao foi aceita:\n{saida}")

    def test_b3_reprova_estouro_vindo_do_template(self) -> None:
        texto = self._sprint_do_template(
            **{"- Consumo observado: `em andamento`": "- Consumo observado: `900k`"}
        )
        self.assertIn("mitigacao", texto.lower(), "a nota do template deve continuar la")
        codigo, saida = self._rodar_em_tmp(texto, "validate_token_budget.py")
        self.assertEqual(codigo, 1, f"B3 nao reprovou estouro de budget:\n{saida}")
        self.assertIn("B3", saida)

    def test_b3_aceita_estouro_com_mitigacao_declarada(self) -> None:
        texto = self._sprint_do_template(
            **{
                "- Consumo observado: `em andamento`": "- Consumo observado: `900k`",
                "- Mitigacao aplicada: `nao se aplica`":
                    "- Mitigacao aplicada: `tier reduzido para leve; budget revisto na sprint 2`",
            }
        )
        codigo, saida = self._rodar_em_tmp(texto, "validate_token_budget.py")
        self.assertEqual(codigo, 0, f"mitigacao declarada nao foi aceita:\n{saida}")


class TestInstaladorDeHooks(unittest.TestCase):
    """Regressao: `scripts/setup-hooks.sh` gerava um hook quebrado.

    Tres defeitos, do mais visivel ao mais insidioso:

    1. chamava `python`, binario ausente no macOS moderno e em distros sem
       python-is-python3;
    2. mascarava QUALQUER falha com `|| echo "(non-blocking)"`, entao o indice
       nunca era atualizado e ninguem percebia — o oposto do principio de
       evidencia honesta que o framework prega;
    3. instalava em `.git/hooks` mesmo com `core.hooksPath` configurado, caso em
       que o git ignora aquele diretorio por completo. Como o getting-started
       manda configurar `core.hooksPath=.githooks`, o hook nunca rodava para
       quem seguia o guia.
    """

    INSTALADOR = RAIZ / "scripts" / "setup-hooks.sh"

    def _repo_temporario(self, tmp: Path, hooks_path: str | None) -> None:
        import shutil

        (tmp / "scripts").mkdir(parents=True)
        shutil.copy(self.INSTALADOR, tmp / "scripts" / "setup-hooks.sh")
        (tmp / "scripts" / "ingest.py").write_text("", encoding="utf-8")
        for cmd in (["git", "init", "-q", "."], ["git", "config", "user.email", "t@t.com"],
                    ["git", "config", "user.name", "t"]):
            subprocess.run(cmd, cwd=tmp, check=True, capture_output=True)
        if hooks_path:
            (tmp / hooks_path).mkdir(exist_ok=True)
            subprocess.run(
                ["git", "config", "core.hooksPath", hooks_path],
                cwd=tmp, check=True, capture_output=True,
            )

    def _instalar(self, tmp: Path) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["bash", "scripts/setup-hooks.sh"],
            cwd=tmp, capture_output=True, text=True,
        )

    def test_instalador_nao_invoca_python_nu(self) -> None:
        texto = self.INSTALADOR.read_text(encoding="utf-8")
        self.assertNotRegex(
            texto, r'(?<![\w/.$"{])python\s+"?\$\{?SCRIPT',
            "o hook nao pode chamar `python` fixo — resolva o interpretador em runtime",
        )
        self.assertIn("python3", texto)

    def test_sintaxe_do_instalador_e_do_hook_gerado(self) -> None:
        import tempfile

        self.assertEqual(
            subprocess.run(["bash", "-n", str(self.INSTALADOR)]).returncode, 0
        )
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            self._repo_temporario(tmp, None)
            self._instalar(tmp)
            hook = tmp / ".git" / "hooks" / "post-commit"
            self.assertTrue(hook.is_file())
            self.assertEqual(subprocess.run(["bash", "-n", str(hook)]).returncode, 0)

    def test_respeita_core_hookspath(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            self._repo_temporario(tmp, ".githooks")
            proc = self._instalar(tmp)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(
                (tmp / ".githooks" / "post-commit").is_file(),
                "com core.hooksPath ativo o hook tem de ir para la",
            )
            self.assertFalse(
                (tmp / ".git" / "hooks" / "post-commit").is_file(),
                "instalar em .git/hooks com core.hooksPath ativo cria hook morto",
            )

    def test_hook_gerado_e_executavel_e_sai_zero_sem_env(self) -> None:
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            self._repo_temporario(tmp, None)
            self._instalar(tmp)
            hook = tmp / ".git" / "hooks" / "post-commit"
            self.assertTrue(os.access(hook, os.X_OK), "hook precisa ser executavel")
            proc = subprocess.run([str(hook)], cwd=tmp, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, "post-commit nunca pode quebrar o commit")
            self.assertIn(".env", proc.stdout)

    def test_hook_avisa_alto_quando_nao_ha_interpretador(self) -> None:
        """Sem Python, o hook tem de dizer que o indice NAO foi atualizado."""
        import tempfile

        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            self._repo_temporario(tmp, None)
            self._instalar(tmp)
            (tmp / "scripts" / ".env").write_text("X=1\n", encoding="utf-8")
            hook = tmp / ".git" / "hooks" / "post-commit"

            # PATH com git, mas SEM nenhum python. Esvaziar o PATH inteiro tiraria
            # tambem o git e o hook morreria antes do trecho sob teste.
            import shutil as _shutil

            bin_isolado = tmp / "bin-isolado"
            bin_isolado.mkdir()
            git_real = _shutil.which("git")
            self.assertIsNotNone(git_real, "git precisa existir para este teste")
            (bin_isolado / "git").symlink_to(git_real)

            ambiente = {"PATH": str(bin_isolado), "HOME": str(tmp)}
            self.assertIsNone(
                _shutil.which("python3", path=str(bin_isolado)),
                "o PATH isolado nao pode conter python3",
            )
            proc = subprocess.run(
                ["/bin/bash", str(hook)], cwd=tmp, capture_output=True, text=True,
                env=ambiente,
            )
            self.assertEqual(proc.returncode, 0, "post-commit nao desfaz commit")
            self.assertIn("NAO foi atualizado", proc.stdout + proc.stderr)


class TestInstalador(unittest.TestCase):
    """O instalador nao pode entregar um projeto que ja nasce reprovado.

    Este e o teste mais importante da suite do ponto de vista de adocao: se
    `nf_install.py` gera artefato que o proprio gate rejeita, o primeiro commit
    do usuario e bloqueado por defeito nosso — e ele desinstala o framework.

    Ja aconteceu tres vezes durante a construcao: AGENTS.md apontava para um
    manifesto inexistente; o `_template.md` de ADR era cobrado como ADR sem
    numero; e os exemplos de `DIVERGENCIAS.md` eram lidos como divergencias
    pendentes de verdade.
    """

    INSTALADOR = SCRIPTS / "nf_install.py"

    def _instalar(self, destino: Path, *extra: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(self.INSTALADOR), "--target", str(destino), *extra],
            capture_output=True, text=True,
        )

    def test_greenfield_gera_projeto_que_passa_no_gate(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as t:
            destino = Path(t) / "ideia"
            proc = self._instalar(destino, "--name", "Projeto Teste", "--mode", "greenfield")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("nf_gate: PASS", proc.stdout)

            for esperado in (
                "COMECE-AQUI.md", "AGENTS.md", "MEMORY.md",
                "docs/sprints/sprint-01.md", "docs/PADRAO-ESPECIFICACAO-MODULOS.md",
                "docs/adr/_template.md", "build/PROTOCOLO.md", "build/PLANO.md",
                "build/DIVERGENCIAS.md", ".githooks/pre-commit",
                "scripts/nf_gate.py", ".github/workflows/neural-flow-gates.yml",
            ):
                with self.subTest(arquivo=esperado):
                    self.assertTrue((destino / esperado).is_file(), f"faltou {esperado}")

    def test_brownfield_preserva_o_que_existe(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as t:
            destino = Path(t) / "legado"
            (destino / "src").mkdir(parents=True)
            (destino / "src" / "index.ts").write_text("export const x = 1;\n", encoding="utf-8")
            pkg_original = {
                "name": "api-legado", "version": "2.3.0",
                "scripts": {"test": "vitest"},
                "devDependencies": {"vitest": "^2.0.0"},
            }
            (destino / "package.json").write_text(
                json.dumps(pkg_original, indent=2), encoding="utf-8"
            )
            agents_original = "# AGENTS.md do time\n\nNao sobrescreva isto.\n"
            (destino / "AGENTS.md").write_text(agents_original, encoding="utf-8")
            subprocess.run(["git", "init", "-q", "."], cwd=destino, check=True)

            proc = self._instalar(destino)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("brownfield", proc.stdout)
            self.assertIn("nf_gate: PASS", proc.stdout)

            # Nada do que existia pode ser destruido.
            self.assertEqual((destino / "AGENTS.md").read_text(encoding="utf-8"), agents_original)
            pkg = json.loads((destino / "package.json").read_text(encoding="utf-8"))
            self.assertEqual(pkg["version"], "2.3.0")
            self.assertEqual(pkg["scripts"]["test"], "vitest")
            self.assertEqual(pkg["devDependencies"]["vitest"], "^2.0.0")
            # E o smoke-gate tem de entrar.
            self.assertIn("@kaiketsu/smoke-gate", pkg["devDependencies"])

    def test_smoke_gate_registrado_no_mcp(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as t:
            destino = Path(t) / "p"
            self._instalar(destino, "--mode", "greenfield")
            mcp = json.loads((destino / ".mcp.json").read_text(encoding="utf-8"))
            args = mcp["mcpServers"]["smoke-gate"]["args"]
            self.assertTrue(
                any(a.startswith("github:reimon/smoke-gate#") for a in args),
                f"smoke-gate nao registrado no MCP: {args}",
            )
            self.assertIn("mcp", args)

    def test_smoke_gate_usa_a_versao_mais_recente(self) -> None:
        """A versao e resolvida na instalacao, nao fixada no codigo do framework.

        Assim cada instalacao nasce com a mais nova sem precisar de release nossa,
        e o projeto instalado continua reproduzivel — referencia flutuante faria o
        mesmo commit auditar diferente em dias diferentes.
        """
        sys.path.insert(0, str(SCRIPTS))
        from nf_install import SMOKE_GATE_FALLBACK, resolver_ref_smoke_gate

        # Override explicito sempre vence e nao consulta a rede.
        self.assertEqual(resolver_ref_smoke_gate("main"), ("main", None))
        self.assertEqual(resolver_ref_smoke_gate("v9.9.9"), ("v9.9.9", None))

        # Sem override: tag valida (da rede) ou fallback declarado — nunca vazio.
        ref, _aviso = resolver_ref_smoke_gate(None)
        self.assertRegex(
            ref, r"^(v?\d+\.\d+\.\d+|main)$",
            f"ref resolvido invalido: {ref!r}",
        )
        self.assertTrue(SMOKE_GATE_FALLBACK.startswith("v"))

    def test_ref_do_smoke_gate_e_respeitado_nos_artefatos(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as t:
            destino = Path(t) / "p"
            (destino).mkdir()
            (destino / "package.json").write_text(
                json.dumps({"name": "x", "version": "1.0.0"}), encoding="utf-8"
            )
            self._instalar(destino, "--smoke-gate-ref", "v9.9.9")
            pkg = json.loads((destino / "package.json").read_text(encoding="utf-8"))
            self.assertEqual(
                pkg["devDependencies"]["@kaiketsu/smoke-gate"],
                "github:reimon/smoke-gate#v9.9.9",
            )
            action = (destino / ".github" / "workflows" / "smoke-gate.yml").read_text(
                encoding="utf-8"
            )
            self.assertIn("reimon/smoke-gate/action@v9.9.9", action)

    def test_claude_md_traz_os_principios_de_execucao(self) -> None:
        """CLAUDE.md e o que muda o comportamento do agente antes de qualquer guard."""
        import tempfile

        with tempfile.TemporaryDirectory() as t:
            destino = Path(t) / "p"
            self._instalar(destino, "--mode", "greenfield")
            claude = destino / "CLAUDE.md"
            self.assertTrue(claude.is_file(), "CLAUDE.md nao foi instalado")
            texto = claude.read_text(encoding="utf-8")
            for principio in (
                "Think Before Coding", "Simplicity First",
                "Surgical Changes", "Goal-Driven Execution",
            ):
                with self.subTest(principio=principio):
                    self.assertIn(principio, texto)
            self.assertIn("multica-ai/andrej-karpathy-skills", texto, "fonte nao creditada")
            self.assertIn("AGENTS.md", texto, "deve apontar para a fonte de verdade")
            self.assertIn("nf_gate.py", texto, "deve ensinar a rodar os guards")
            self.assertNotIn("TEMPLATE Neural-Flow", texto, "cabecalho de template vazou")

    def test_instalacao_e_idempotente(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as t:
            destino = Path(t) / "p"
            self._instalar(destino, "--mode", "greenfield")
            segunda = self._instalar(destino, "--mode", "greenfield")
            self.assertEqual(segunda.returncode, 0, segunda.stdout + segunda.stderr)
            self.assertIn("Criados (0)", segunda.stdout)

    def test_dry_run_nao_escreve(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as t:
            destino = Path(t) / "p"
            destino.mkdir()
            proc = self._instalar(destino, "--dry-run")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(list(destino.iterdir()), [], "dry-run escreveu no disco")

    def test_wrapper_shell_tem_sintaxe_valida(self) -> None:
        self.assertEqual(
            subprocess.run(["bash", "-n", str(RAIZ / "install.sh")]).returncode, 0
        )


class TestDashboard(unittest.TestCase):
    """O dashboard le artefatos do repositorio e gera HTML auto-contido.

    Auto-contido nao e detalhe estetico: uma pagina que busca CDN nao abre
    offline, nao roda em CI isolado e vaza para onde o time nao controla.
    """

    DASH = SCRIPTS / "nf_dashboard.py"

    def _gerar(self, raiz: Path, saida: Path) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(self.DASH), "--root", str(raiz), "--out", str(saida)],
            capture_output=True, text=True,
        )

    def test_gera_html_valido_a_partir_da_fixture(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as t:
            saida = Path(t) / "d.html"
            proc = self._gerar(CONFORME, saida)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            texto = saida.read_text(encoding="utf-8")
            self.assertTrue(texto.startswith("<!doctype html>"))
            self.assertIn("</html>", texto)
            for secao in ("Sprint ativa", "Guards", "FinOps", "smoke-gate",
                          "Protocolos", "Loop autonomo"):
                with self.subTest(secao=secao):
                    self.assertIn(secao, texto)

    def test_html_e_auto_contido(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as t:
            saida = Path(t) / "d.html"
            self._gerar(CONFORME, saida)
            texto = saida.read_text(encoding="utf-8")
            for proibido in ("http://", "https://", "<script", "src=", "@import"):
                with self.subTest(proibido=proibido):
                    self.assertNotIn(
                        proibido, texto,
                        f"dashboard nao pode depender de recurso externo ({proibido})",
                    )

    def test_projeto_vazio_nao_quebra(self) -> None:
        """Sem sprint, sem ADR, sem grafo: informa o que falta, nao explode."""
        import tempfile

        with tempfile.TemporaryDirectory() as t:
            raiz = Path(t) / "vazio"
            raiz.mkdir()
            saida = Path(t) / "d.html"
            proc = self._gerar(raiz, saida)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            texto = saida.read_text(encoding="utf-8")
            self.assertIn("Nenhuma sprint encontrada", texto)

    def test_estouro_de_budget_aparece_como_critico(self) -> None:
        """A leitura visual tem de bater com o veredito do guard."""
        import tempfile

        with tempfile.TemporaryDirectory() as t:
            saida = Path(t) / "d.html"
            self._gerar(VIOLADOR, saida)
            texto = saida.read_text(encoding="utf-8")
            self.assertIn("130%", texto)
            self.assertIn("--st-critical", texto)

    def test_dados_sao_escapados(self) -> None:
        """Titulo de sprint com HTML nao pode injetar marcacao na pagina."""
        import tempfile

        with tempfile.TemporaryDirectory() as t:
            raiz = Path(t) / "p"
            (raiz / "docs" / "sprints").mkdir(parents=True)
            (raiz / "docs" / "sprints" / "s.md").write_text(
                "# Sprint 1: <script>alert(1)</script>\n"
                "## Snapshot Operacional\n- Status: `em andamento`\n",
                encoding="utf-8",
            )
            saida = Path(t) / "d.html"
            self._gerar(raiz, saida)
            texto = saida.read_text(encoding="utf-8")
            self.assertNotIn("<script>alert", texto)
            self.assertIn("&lt;script&gt;", texto)


class TestHelpers(unittest.TestCase):
    """nf_guards e usado por todos os guards — regressao aqui contamina tudo."""

    def test_numero(self) -> None:
        from nf_guards import numero

        casos = {
            "250k": 250_000, "1.2M": 1_200_000, "250.000": 250_000,
            "1,5": 1.5, "1.234,56": 1234.56, "300000 tokens": 300_000,
            "2M": 2_000_000, "abc": None, "": None,
        }
        for entrada, esperado in casos.items():
            with self.subTest(entrada=entrada):
                obtido = numero(entrada)
                if esperado is None:
                    self.assertIsNone(obtido)
                else:
                    self.assertAlmostEqual(obtido, esperado, places=2)

    def test_eh_placeholder(self) -> None:
        from nf_guards import eh_placeholder

        for vazio in ("a preencher", "YYYY-MM-DD", "<algo>", "", "   ", "TODO"):
            self.assertTrue(eh_placeholder(vazio), f"{vazio!r} deveria ser placeholder")
        for cheio in ("A1", "nenhum", "2026-08-08", "500k", "em andamento"):
            self.assertFalse(eh_placeholder(cheio), f"{cheio!r} nao e placeholder")

    def test_sem_acento(self) -> None:
        from nf_guards import sem_acento

        self.assertEqual(sem_acento("Confiança"), "Confianca")
        self.assertEqual(sem_acento("execuções válidas"), "execucoes validas")

    def test_secao_e_campos(self) -> None:
        from nf_guards import campos, secao

        linhas = [
            "# Doc", "## Snapshot", "- Status: `em andamento`",
            "- **Nivel de autonomia:** A1", "## Outra", "- Status: `errado`",
        ]
        faixa = secao(linhas, "Snapshot")
        self.assertIsNotNone(faixa)
        dados = campos(linhas, *faixa)
        self.assertEqual(dados["status"], "`em andamento`")
        self.assertEqual(dados["nivel de autonomia"], "A1")
        self.assertNotIn("errado", dados.get("status", ""))


class TestOrquestrador(unittest.TestCase):
    def test_nf_gate_agrega_falhas(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS / "nf_gate.py"), "--root", str(VIOLADOR), "--quiet"],
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 1)
        self.assertIn("nf_gate: FAIL", proc.stdout)

    def test_nf_gate_passa_no_conforme(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS / "nf_gate.py"), "--root", str(CONFORME), "--quiet"],
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("nf_gate: PASS", proc.stdout)

    def test_guard_desconhecido_e_erro_de_uso(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS / "nf_gate.py"), "inexistente"],
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
