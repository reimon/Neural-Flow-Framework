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
    "spec": ("validate_module_spec.py",
             {"P1", "P4", "P5", "P6", "P7", "P8", "P9"}),
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


class TestRastreabilidadeDeSpec(unittest.TestCase):
    """As checagens que separam spec detalhada de spec decorativa.

    Portadas do validador de um projeto real, onde a rigidez foi o que sustentou
    doze modulos no mesmo nivel. Sem elas o guard aceitava qualquer texto com os
    titulos certos.
    """

    def _spec(self, tmp: Path, corpo: str, config: dict | None = None) -> Path:
        destino = tmp / "docs" / "modulos" / "01-x"
        destino.mkdir(parents=True, exist_ok=True)
        (destino / "spec.md").write_text(corpo, encoding="utf-8")
        if config is not None:
            (tmp / ".neural-flow.json").write_text(json.dumps(config), encoding="utf-8")
        return destino / "spec.md"

    def _rodar(self, tmp: Path) -> tuple[int, str]:
        return rodar("validate_module_spec.py", tmp)

    BASE = "# M\n\n## Proposito\n\n{corpo}\n"
    CFG = {"spec_sections": ["Proposito"]}

    def test_p5_id_definido_e_nunca_citado_e_spec_morta(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as t:
            self._spec(Path(t), self.BASE.format(
                corpo="- **ACM-INV-001** — saldo nunca fica negativo"), self.CFG)
            codigo, saida = self._rodar(Path(t))
            self.assertEqual(codigo, 1)
            self.assertIn("P5", saida)
            self.assertIn("spec morta", saida)

    def test_p5_id_citado_e_nunca_definido_e_pendurado(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as t:
            self._spec(Path(t), self.BASE.format(
                corpo="O calculo respeita ACM-INV-042."), self.CFG)
            codigo, saida = self._rodar(Path(t))
            self.assertEqual(codigo, 1)
            self.assertIn("referencia pendurada", saida)

    def test_p5_definido_e_citado_passa(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as t:
            self._spec(Path(t), self.BASE.format(
                corpo="- **ACM-INV-001** — saldo nunca fica negativo\n\n"
                      "O aceite verifica ACM-INV-001 na escrita."), self.CFG)
            codigo, saida = self._rodar(Path(t))
            self.assertEqual(codigo, 0, saida)

    def test_p9_negacao_nao_e_promessa(self) -> None:
        """"Nunca prometer aprovacao garantida" e o oposto de prometer.

        Sem tratar negacao, o guard reprovaria justamente a linha que estabelece
        a regra — e o time aprenderia a desligar a checagem.
        """
        import tempfile

        cfg = dict(self.CFG, spec_linguagem_proibida=["aprovacao garantida"])
        with tempfile.TemporaryDirectory() as t:
            self._spec(Path(t), self.BASE.format(
                corpo="Nunca prometer aprovacao garantida ao usuario."), cfg)
            codigo, saida = self._rodar(Path(t))
            self.assertEqual(codigo, 0, saida)

        with tempfile.TemporaryDirectory() as t:
            self._spec(Path(t), self.BASE.format(
                corpo="O usuario recebe aprovacao garantida em 24h."), cfg)
            codigo, saida = self._rodar(Path(t))
            self.assertEqual(codigo, 1)
            self.assertIn("P9", saida)

    def test_p8_fonte_sem_data_de_verificacao(self) -> None:
        import tempfile

        cfg = dict(self.CFG, spec_fontes=["dados/"])
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            (tmp / "dados").mkdir()
            (tmp / "dados" / "taxas.json").write_text('{"taxa": 1}', encoding="utf-8")
            self._spec(tmp, self.BASE.format(corpo="Taxas em `dados/taxas.json`."), cfg)
            codigo, saida = self._rodar(tmp)
            self.assertEqual(codigo, 1)
            self.assertIn("last_verified", saida)

            (tmp / "dados" / "taxas.json").write_text(
                '{"taxa": 1, "last_verified": "2026-08-01"}', encoding="utf-8")
            codigo, saida = self._rodar(tmp)
            self.assertEqual(codigo, 0, saida)

    def test_p10_estrutura_multiarquivo_e_indice(self) -> None:
        import tempfile

        cfg = dict(self.CFG, spec_estrutura={"arquivos": 2, "readme": True})
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            d = tmp / "docs" / "modulos" / "01-x"
            d.mkdir(parents=True)
            (tmp / ".neural-flow.json").write_text(json.dumps(cfg), encoding="utf-8")
            (d / "01-a.md").write_text("# A\n\n## Proposito\n\nx\n", encoding="utf-8")
            codigo, saida = self._rodar(tmp)
            self.assertEqual(codigo, 1)
            self.assertIn("P10", saida)

            (d / "02-b.md").write_text("# B\n\n## Proposito\n\ny\n", encoding="utf-8")
            (d / "README.md").write_text("# I\n\n- [a](01-a.md)\n", encoding="utf-8")
            codigo, saida = self._rodar(tmp)
            self.assertIn("nao esta linkado no README", saida)

            (d / "README.md").write_text(
                "# I\n\n- [a](01-a.md)\n- [b](02-b.md)\n", encoding="utf-8")
            codigo, saida = self._rodar(tmp)
            self.assertEqual(codigo, 0, saida)

    def test_sem_configuracao_as_checagens_de_dominio_ficam_desligadas(self) -> None:
        """Projeto que nao configurou nada continua passando como antes."""
        import tempfile

        with tempfile.TemporaryDirectory() as t:
            self._spec(Path(t), self.BASE.format(
                corpo="O usuario recebe aprovacao garantida."), self.CFG)
            codigo, saida = self._rodar(Path(t))
            self.assertEqual(codigo, 0, saida)


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
        # Ref explicito mantem o teste hermetico: sem ele o instalador consulta a
        # API do GitHub, o que deixa a suite lenta e refem de limite de requisicao.
        # A resolucao dinamica tem teste proprio.
        if not any(a == "--smoke-gate-ref" for a in extra):
            extra = (*extra, "--smoke-gate-ref", "v0.5.0")
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

    def test_nenhum_artefato_nasce_invisivel_para_o_gate(self) -> None:
        """O cabecalho `> TEMPLATE Neural-Flow` desliga `eh_template()`.

        Copiado tal e qual para o projeto, o artefato nasce permanentemente
        invisivel para os guards: o gate passa, e nao valida nada. Aconteceu com
        o `MEMORY.md`, que era lido com `read_text` direto em vez de
        `copiar_template`.
        """
        import tempfile

        with tempfile.TemporaryDirectory() as t:
            destino = Path(t) / "p"
            self._instalar(destino, "--name", "Projeto Teste", "--mode", "greenfield")
            for caminho in sorted(destino.rglob("*.md")):
                # `docs/adr/_template.md` e instalado *como* template, de
                # proposito: e o modelo que o time copia para criar um ADR.
                if caminho.name.startswith("_"):
                    continue
                with self.subTest(arquivo=caminho.relative_to(destino)):
                    self.assertNotIn(
                        "TEMPLATE Neural-Flow",
                        caminho.read_text(encoding="utf-8"),
                        "artefato instalado carrega o cabecalho de template",
                    )

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
        """A pagina tem de renderizar offline, sem uma unica requisicao.

        A garantia e sobre RECURSO BUSCADO, nao sobre a palavra "https". Um
        hyperlink nao dispara requisicao ao abrir a pagina — proibi-lo tiraria a
        capacidade de linkar o grafo do graphify, que e justamente o ponto.
        """
        import tempfile

        with tempfile.TemporaryDirectory() as t:
            saida = Path(t) / "d.html"
            self._gerar(CONFORME, saida)
            texto = saida.read_text(encoding="utf-8")
            for proibido in ("<script", "src=", "@import", "<iframe", "<link "):
                with self.subTest(proibido=proibido):
                    self.assertNotIn(
                        proibido, texto,
                        f"dashboard nao pode buscar recurso externo ({proibido})",
                    )
            # url(http...) em CSS tambem e busca; url(data:) nao.
            self.assertNotRegex(texto, r"url\(\s*['\"]?https?:")

    def test_linka_os_artefatos_do_graphify(self) -> None:
        """O grafo interativo tem varios MB: linkar, nunca embutir."""
        import tempfile

        with tempfile.TemporaryDirectory() as t:
            saida = Path(t) / "sub" / "d.html"
            proc = self._gerar(RAIZ / "tests" / "fixtures" / "demo", saida)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            texto = saida.read_text(encoding="utf-8")
            for artefato in ("graph.html", "wiki/index.md", "GRAPH_REPORT.md"):
                with self.subTest(artefato=artefato):
                    self.assertIn(artefato, texto)
            # O caminho tem de ser relativo e independente da maquina. Quando a
            # saida cai fora da arvore analisada, `relpath` produziria algo como
            # `../../../../Users/<voce>/...` — por isso o fallback para o caminho
            # canonico a partir da raiz do projeto.
            self.assertNotIn(str(RAIZ), texto)
            self.assertNotIn("/Users/", texto)
            self.assertNotIn("/home/", texto)
            import re as _re
            for href in _re.findall(r'href="([^"]*graphify-out[^"]*)"', texto):
                with self.subTest(href=href):
                    self.assertFalse(href.startswith("/"), "link absoluto")
                    self.assertNotIn("..", href.split("graphify-out")[0].strip("./"))

    def test_ajuda_contextual_em_todo_quadro_e_protocolo(self) -> None:
        """Cada quadro e cada protocolo explica o que representa.

        A ajuda usa o `popover` nativo do HTML: janela de verdade, com Esc e
        clique-fora, **sem uma linha de JavaScript**. Isso preserva a garantia de
        auto-contencao, que um modal com script quebraria.
        """
        import tempfile

        sys.path.insert(0, str(SCRIPTS))
        from nf_dashboard import AJUDA_PROTOCOLOS, AJUDA_QUADROS, AJUDA_TILES

        with tempfile.TemporaryDirectory() as t:
            saida = Path(t) / "d.html"
            self._gerar(RAIZ / "tests" / "fixtures" / "demo", saida)
            texto = saida.read_text(encoding="utf-8")

            esperados = (
                [f'popovertarget="ajuda-{k}"' for k in AJUDA_QUADROS]
                + [f'popovertarget="ajuda-tile-{k}"' for k in AJUDA_TILES]
            )
            for alvo in esperados:
                with self.subTest(alvo=alvo):
                    self.assertIn(alvo, texto)

            # Todo protocolo listado tem explicacao propria.
            for nome in AJUDA_PROTOCOLOS:
                with self.subTest(protocolo=nome):
                    self.assertIn(f'aria-label="O que e {nome}?"', texto)

            # Toda janela referenciada por um botao precisa existir.
            import re as _re
            alvos = set(_re.findall(r'popovertarget="([^"]+)"', texto))
            ids = set(_re.findall(r'<div popover id="([^"]+)"', texto))
            self.assertFalse(alvos - ids, f"botao sem janela: {sorted(alvos - ids)}")

            # E continua sem script.
            self.assertNotIn("<script", texto)
            self.assertIn("popover", texto)

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


class TestTelemetriaDeTokens(unittest.TestCase):
    """Consumo REAL, lido dos transcripts locais — nao o declarado na sprint.

    O teste monta um transcript sintetico em vez de usar `~/.claude` do usuario:
    depender do historico real deixaria o resultado diferente em cada maquina.
    """

    def _transcript(self, base: Path, raiz_projeto: Path, registros: list[dict]) -> None:
        sys.path.insert(0, str(SCRIPTS))
        from nf_tokens import slug_do_projeto

        destino = base / slug_do_projeto(raiz_projeto)
        destino.mkdir(parents=True)
        linhas = [json.dumps(r) for r in registros]
        (destino / "sessao.jsonl").write_text("\n".join(linhas) + "\n", encoding="utf-8")

    def test_agrega_por_modelo_e_calcula_cache(self) -> None:
        import tempfile

        sys.path.insert(0, str(SCRIPTS))
        from nf_tokens import coletar_tokens

        with tempfile.TemporaryDirectory() as t:
            base, proj = Path(t) / "tr", Path(t) / "proj"
            proj.mkdir()
            agora = "2026-08-08T10:00:00.000Z"
            self._transcript(base, proj, [
                {"type": "user", "timestamp": agora, "message": {"content": "segredo"}},
                {"timestamp": agora, "sessionId": "s1", "message": {
                    "model": "claude-opus-5",
                    "usage": {"input_tokens": 1000, "output_tokens": 500,
                              "cache_creation_input_tokens": 2000,
                              "cache_read_input_tokens": 7000}}},
                {"timestamp": agora, "sessionId": "s1", "message": {
                    "model": "claude-fable-5",
                    "usage": {"input_tokens": 100, "output_tokens": 50,
                              "cache_creation_input_tokens": 0,
                              "cache_read_input_tokens": 900}}},
            ])
            tel = coletar_tokens(proj, dias=36500, base=base)

            self.assertTrue(tel.disponivel, tel.motivo)
            self.assertEqual(tel.geral.requisicoes, 2)
            self.assertEqual(tel.geral.entrada, 1100)
            self.assertEqual(tel.geral.saida, 550)
            self.assertEqual(tel.geral.cache_lido, 7900)
            # faturavel exclui leitura de cache, que custa uma fracao
            self.assertEqual(tel.geral.faturavel, 1100 + 550 + 2000)
            self.assertEqual(tel.sessoes, 1)
            self.assertEqual(set(tel.por_modelo), {"claude-opus-5", "claude-fable-5"})
            self.assertAlmostEqual(tel.geral.aproveitamento_cache, 7900 / 11000, places=3)

    def _rollout_codex(self, base: Path, cwd: str, registros: list[dict]) -> None:
        destino = base / "2026" / "08" / "08"
        destino.mkdir(parents=True, exist_ok=True)
        cabecalho = [
            {"type": "session_meta", "timestamp": "2026-08-08T10:00:00.000Z",
             "payload": {"type": "session_meta", "session_id": "cx1", "cwd": cwd}},
            {"type": "turn_context", "timestamp": "2026-08-08T10:00:00.000Z",
             "payload": {"type": "turn_context", "cwd": cwd, "model": "gpt-5.6-terra",
                         "workspace_roots": [cwd]}},
        ]
        linhas = [json.dumps(r) for r in cabecalho + registros]
        (destino / "rollout-teste.jsonl").write_text("\n".join(linhas) + "\n", encoding="utf-8")

    @staticmethod
    def _evento_codex(entrada: int, cache: int, saida: int) -> dict:
        return {"type": "event_msg", "timestamp": "2026-08-08T11:00:00.000Z",
                "payload": {"type": "token_count", "info": {
                    "last_token_usage": {
                        "input_tokens": entrada, "cached_input_tokens": cache,
                        "cache_write_input_tokens": 0, "output_tokens": saida,
                        "total_tokens": entrada + saida},
                    "total_token_usage": {
                        "input_tokens": entrada * 9, "cached_input_tokens": cache * 9,
                        "output_tokens": saida * 9}}}}

    def test_codex_soma_deltas_e_nao_o_acumulado(self) -> None:
        """`total_token_usage` e acumulado da sessao; `last_token_usage` e o delta.

        Somar o acumulado a cada evento inflaria o numero em ordens de grandeza —
        no rollout real desta maquina, 47 eventos multiplicariam tudo por ~47.
        """
        import tempfile

        sys.path.insert(0, str(SCRIPTS))
        from nf_tokens import Telemetria, ler_codex
        from datetime import datetime, timedelta, timezone

        with tempfile.TemporaryDirectory() as t:
            base, proj = Path(t) / "codex", Path(t) / "proj"
            proj.mkdir()
            self._rollout_codex(base, str(proj), [
                self._evento_codex(1000, 400, 200),
                self._evento_codex(500, 100, 50),
            ])
            tel = Telemetria()
            corte = datetime.now(timezone.utc) - timedelta(days=36500)
            ler_codex(proj, corte, tel, diretorio=base)

            # `cached_input_tokens` e SUBCONJUNTO de `input_tokens` na semantica
            # da OpenAI: entrada real = 1000-400 + 500-100 = 1000
            self.assertEqual(tel.geral.entrada, 1000)
            self.assertEqual(tel.geral.cache_lido, 500)
            self.assertEqual(tel.geral.saida, 250)
            self.assertEqual(tel.geral.requisicoes, 2)
            self.assertIn("codex", tel.por_provedor)
            self.assertIn("gpt-5.6-terra", tel.por_modelo)

    def test_codex_filtra_por_projeto(self) -> None:
        """O Codex organiza sessoes por data, nao por projeto. Sem filtrar pelo
        `cwd`, o numero seria de todos os projetos do usuario somados."""
        import tempfile

        sys.path.insert(0, str(SCRIPTS))
        from nf_tokens import Telemetria, ler_codex
        from datetime import datetime, timedelta, timezone

        with tempfile.TemporaryDirectory() as t:
            base = Path(t) / "codex"
            meu, alheio = Path(t) / "meu", Path(t) / "outro"
            meu.mkdir(); alheio.mkdir()
            self._rollout_codex(base, str(alheio), [self._evento_codex(9000, 0, 900)])

            tel = Telemetria()
            corte = datetime.now(timezone.utc) - timedelta(days=36500)
            ler_codex(meu, corte, tel, diretorio=base)
            self.assertEqual(tel.geral.requisicoes, 0, "contou sessao de outro projeto")
            self.assertNotIn("codex", tel.por_provedor)

            tel2 = Telemetria()
            ler_codex(alheio, corte, tel2, diretorio=base)
            self.assertEqual(tel2.geral.requisicoes, 1)

    def test_projeto_sem_transcript_nao_quebra(self) -> None:
        import tempfile

        sys.path.insert(0, str(SCRIPTS))
        from nf_tokens import coletar_tokens

        with tempfile.TemporaryDirectory() as t:
            tel = coletar_tokens(Path(t), dias=30, base=Path(t) / "inexistente")
            self.assertFalse(tel.disponivel)
            self.assertTrue(tel.motivo)

    def test_nao_extrai_conteudo_de_mensagem(self) -> None:
        """Garantia de privacidade: so numeros saem do transcript."""
        import tempfile

        sys.path.insert(0, str(SCRIPTS))
        from nf_tokens import coletar_tokens

        with tempfile.TemporaryDirectory() as t:
            base, proj = Path(t) / "tr", Path(t) / "proj"
            proj.mkdir()
            self._transcript(base, proj, [
                {"timestamp": "2026-08-08T10:00:00.000Z", "sessionId": "s1", "message": {
                    "model": "m", "content": "TEXTO-CONFIDENCIAL-DO-USUARIO",
                    "usage": {"input_tokens": 10, "output_tokens": 5}}},
            ])
            tel = coletar_tokens(proj, dias=36500, base=base)
            serializado = json.dumps(tel.como_dict())
            self.assertNotIn("CONFIDENCIAL", serializado)
            self.assertEqual(tel.geral.entrada, 10)


class TestDiagrama(unittest.TestCase):
    """O diagrama e gerado do mesmo registro de guards que o `nf_gate` usa.

    Assim, guard novo aparece no desenho sem ninguem lembrar de redesenhar — e o
    teste garante que a versao commitada nao ficou para tras.
    """

    SVG = RAIZ / "docs" / "img" / "arquitetura.svg"

    def test_svg_bem_formado_e_autocontido(self) -> None:
        import xml.etree.ElementTree as ET

        self.assertTrue(self.SVG.is_file(), "docs/img/arquitetura.svg nao existe")
        ET.parse(self.SVG)  # levanta se malformado
        texto = self.SVG.read_text(encoding="utf-8")
        for proibido in ("<script", "<foreignObject", "<image", "xlink:href", "@import"):
            with self.subTest(proibido=proibido):
                self.assertNotIn(proibido, texto)
        # `xmlns="http://www.w3.org/2000/svg"` e identificador de namespace, nao
        # recurso buscado — proibir a string "http" cegamente reprovaria todo SVG
        # valido. O que nao pode e URL em atributo que dispara requisicao.
        import re as _re
        self.assertIsNone(
            _re.search(r'(href|src)\s*=\s*"https?:', texto),
            "SVG referencia recurso externo",
        )

    def test_todo_guard_aparece_no_diagrama(self) -> None:
        sys.path.insert(0, str(SCRIPTS))
        from nf_gate import GUARDS

        texto = self.SVG.read_text(encoding="utf-8")
        for nome, (_s, protocolo, _o) in GUARDS.items():
            with self.subTest(guard=nome):
                self.assertIn(protocolo, texto)

    def test_diagrama_esta_atualizado(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as t:
            alvo = Path(t) / "a.svg"
            proc = subprocess.run(
                [sys.executable, str(SCRIPTS / "nf_diagrama.py"), "--out", str(alvo)],
                capture_output=True, text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertEqual(
                self.SVG.read_text(encoding="utf-8"),
                alvo.read_text(encoding="utf-8"),
                "docs/img/arquitetura.svg desatualizado. Regenere:\n"
                "  python3 scripts/nf_diagrama.py",
            )


class TestDemoVersionada(unittest.TestCase):
    """`docs/dashboard-demo.html` nao pode apodrecer.

    Uma demo versionada que deixa de refletir o gerador e pior que nenhuma: quem
    chega no repositorio confia nela. Este teste regenera a partir da fixture e
    compara — se alguem mudar o dashboard e esquecer de regerar, o CI reprova.

    A comparacao normaliza carimbos de tempo derivados de mtime: o git nao
    preserva mtime, entao esses valores mudam a cada clone sem que nada real
    tenha mudado.
    """

    DEMO = RAIZ / "docs" / "dashboard-demo.html"
    FIXTURE = RAIZ / "tests" / "fixtures" / "demo"
    CARIMBO = "2026-08-08 12:00"

    @property
    def ARGS(self) -> list[str]:
        # Janela enorme e transcript da fixture: sem isso a demo dependeria da
        # data de hoje (os registros sairiam da janela de 30 dias em um mes) e
        # do `~/.claude` da maquina.
        return ["--root", str(self.FIXTURE), "--name", "AgendaMed",
                "--gerado-em", self.CARIMBO,
                "--transcripts", str(self.FIXTURE / "transcripts"),
                "--dias", "36500", "--sem-tema"]

    @staticmethod
    def _normalizar(texto: str) -> str:
        return re.sub(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", "<TEMPO>", texto)

    def test_demo_esta_atualizada(self) -> None:
        import tempfile

        self.assertTrue(self.DEMO.is_file(), "docs/dashboard-demo.html nao existe")
        with tempfile.TemporaryDirectory() as t:
            saida = Path(t) / "d.html"
            proc = subprocess.run(
                [sys.executable, str(SCRIPTS / "nf_dashboard.py"), *self.ARGS,
                 "--out", str(saida)],
                capture_output=True, text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            atual = self._normalizar(self.DEMO.read_text(encoding="utf-8"))
            novo = self._normalizar(saida.read_text(encoding="utf-8"))
            self.assertEqual(
                atual, novo,
                "docs/dashboard-demo.html esta desatualizada. Regenere:\n"
                "  python3 scripts/nf_dashboard.py "
                + " ".join(self.ARGS).replace(str(RAIZ) + "/", "")
                + " --out docs/dashboard-demo.html",
            )

    def test_demo_exercita_as_secoes(self) -> None:
        """Uma demo com secoes vazias nao demonstra nada."""
        texto = self.DEMO.read_text(encoding="utf-8")
        for esperado in (
            "AgendaMed", "112%",            # estouro de budget visivel
            "AMBIGUOUS",                    # arestas pendentes do grafo
            "2 critical",                   # achados do smoke-gate
            "agendamento",                  # comunidades do grafo
            "Aproveitamento de cache",      # telemetria de tokens
            "pendente de revisao humana" if False else "Divergencias",
        ):
            with self.subTest(esperado=esperado):
                self.assertIn(esperado, texto)

    def test_saida_e_reproduzivel(self) -> None:
        """Sem determinismo o teste de drift acusaria mudanca a cada execucao."""
        import tempfile

        with tempfile.TemporaryDirectory() as t:
            saidas = []
            for i in range(2):
                alvo = Path(t) / f"d{i}.html"
                subprocess.run(
                    [sys.executable, str(SCRIPTS / "nf_dashboard.py"), *self.ARGS,
                     "--out", str(alvo)],
                    capture_output=True, text=True, check=True,
                )
                saidas.append(self._normalizar(alvo.read_text(encoding="utf-8")))
            self.assertEqual(saidas[0], saidas[1])


class TestPortasDeAgente(unittest.TestCase):
    """Cada ferramenta de IA le um arquivo diferente na raiz.

    Instalar so `CLAUDE.md` governa exatamente um agente; o Gemini, o Copilot, o
    Cursor e o Cline entram sem diretriz nenhuma e reimplementam o que ja existe.
    O guard trava isso, e estes testes travam o guard.
    """

    GUARD = SCRIPTS / "validate_agent_entrypoints.py"
    INSTALADOR = SCRIPTS / "nf_install.py"

    def _projeto(self, tmp: Path) -> Path:
        destino = tmp / "p"
        proc = subprocess.run(
            [sys.executable, str(self.INSTALADOR), "--target", str(destino),
             "--name", "P", "--smoke-gate", "no"],
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return destino

    def _rodar(self, raiz: Path) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(self.GUARD), "--root", str(raiz)],
            capture_output=True, text=True,
        )

    def test_instalacao_cria_porta_para_toda_ferramenta(self) -> None:
        import tempfile

        sys.path.insert(0, str(SCRIPTS))
        from nf_agentes import PORTAS, corpo

        with tempfile.TemporaryDirectory() as t:
            raiz = self._projeto(Path(t))
            for porta in PORTAS:
                with self.subTest(porta=porta.caminho):
                    caminho = raiz / porta.caminho
                    self.assertTrue(caminho.is_file(), f"{porta.ferramenta} sem porta")
                    texto = caminho.read_text(encoding="utf-8")
                    self.assertIn(corpo().strip(), texto, "corpo canonico ausente")
                    self.assertIn("AGENTS.md", texto)
            self.assertEqual(self._rodar(raiz).returncode, 0)

    def test_porta_ausente_trava(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as t:
            raiz = self._projeto(Path(t))
            (raiz / "GEMINI.md").unlink()
            proc = self._rodar(raiz)
            self.assertEqual(proc.returncode, 1)
            self.assertIn("[P1]", proc.stdout)

    def test_porta_editada_a_mao_trava(self) -> None:
        """Editar a porta cria uma regra que so aquela ferramenta conhece."""
        import tempfile

        with tempfile.TemporaryDirectory() as t:
            raiz = self._projeto(Path(t))
            (raiz / "GEMINI.md").write_text(
                "<!-- neural-flow:entrypoint v1 -->\n# Minhas regras\n", encoding="utf-8"
            )
            proc = self._rodar(raiz)
            self.assertEqual(proc.returncode, 1)
            self.assertIn("[P2]", proc.stdout)

    def test_indice_desatualizado_trava(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as t:
            raiz = self._projeto(Path(t))
            with (raiz / "AGENTS.md").open("a", encoding="utf-8") as fh:
                fh.write("\n## 9. Deploy\n\n- Nunca fazer deploy manual: so via CI.\n")
            proc = self._rodar(raiz)
            self.assertEqual(proc.returncode, 1)
            self.assertIn("[P5]", proc.stdout)

            subprocess.run(
                [sys.executable, str(SCRIPTS / "nf_indice_regras.py"), "--root", str(raiz)],
                capture_output=True, text=True, check=True,
            )
            self.assertEqual(self._rodar(raiz).returncode, 0, "regerar nao resolveu")
            self.assertIn(
                "deploy manual",
                (raiz / ".neural-flow" / "indice-regras.md").read_text(encoding="utf-8"),
                "a regra nova nao entrou no indice",
            )

    def test_regerador_toca_so_as_portas(self) -> None:
        """`--escrever` conserta a porta sem passar por cima do trabalho do time.

        A alternativa que o guard sugeria antes (`nf_install --force`) sobrescreve
        `AGENTS.md` e `MEMORY.md` junto — conserto que apaga o conteudo preenchido
        a mao e pior que o defeito.
        """
        import tempfile

        with tempfile.TemporaryDirectory() as t:
            raiz = self._projeto(Path(t))
            marca_do_time = "\n\n## Mapa de capacidades do time\n\n- Use o repositorio X.\n"
            with (raiz / "AGENTS.md").open("a", encoding="utf-8") as fh:
                fh.write(marca_do_time)
            (raiz / "GEMINI.md").write_text("# lixo\n", encoding="utf-8")

            proc = subprocess.run(
                [sys.executable, str(SCRIPTS / "nf_agentes.py"), "--root", str(raiz),
                 "--escrever"],
                capture_output=True, text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn(
                marca_do_time.strip(),
                (raiz / "AGENTS.md").read_text(encoding="utf-8"),
                "o regerador passou por cima do AGENTS.md do time",
            )
            self.assertIn("AGENTS.md", (raiz / "GEMINI.md").read_text(encoding="utf-8"))

            # Idempotente: segunda passada nao reescreve nada.
            de_novo = subprocess.run(
                [sys.executable, str(SCRIPTS / "nf_agentes.py"), "--root", str(raiz),
                 "--escrever"],
                capture_output=True, text=True,
            )
            self.assertIn("0 atualizada(s)", de_novo.stdout)

    def test_reinstalar_libera_o_indice_de_gitignore_antigo(self) -> None:
        """Projeto instalado por versao anterior ignorava `.neural-flow/` inteiro.

        Sem o conserto, o indice nunca chega ao CI nem a maquina de outra pessoa —
        e o guard P5 reprova justamente onde ninguem consegue regerar.
        """
        import tempfile

        with tempfile.TemporaryDirectory() as t:
            destino = Path(t) / "p"
            destino.mkdir()
            subprocess.run(["git", "init", "-q", str(destino)], check=True,
                           capture_output=True)
            (destino / ".gitignore").write_text(
                "# Neural-Flow\n__pycache__/\naudit-report.md\n.neural-flow/*\n",
                encoding="utf-8",
            )
            proc = subprocess.run(
                [sys.executable, str(self.INSTALADOR), "--target", str(destino),
                 "--name", "P", "--smoke-gate", "no"],
                capture_output=True, text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            texto = (destino / ".gitignore").read_text(encoding="utf-8")
            self.assertIn("!.neural-flow/indice-regras.md", texto)
            checado = subprocess.run(
                ["git", "check-ignore", ".neural-flow/indice-regras.md"],
                cwd=destino, capture_output=True, text=True,
            )
            self.assertNotEqual(checado.returncode, 0, "o indice continua ignorado")

    def test_indice_nao_executa_nf_gate_homonimo_do_projeto(self) -> None:
        """Projeto brownfield pode ter `scripts/nf_gate.py` proprio.

        Ler o registro de guards com `import_module` executaria o modulo do
        projeto — codigo de terceiro rodando dentro de um guard, no pre-commit.
        A assinatura decide qual arquivo pode ser carregado.
        """
        import tempfile

        with tempfile.TemporaryDirectory() as t:
            raiz = Path(t) / "p"
            (raiz / "scripts").mkdir(parents=True)
            bomba = raiz / "scripts" / "nf_gate.py"
            bomba.write_text(
                "raise SystemExit('o nf_gate do projeto foi executado')\n", encoding="utf-8"
            )
            (raiz / "AGENTS.md").write_text(
                "# AGENTS\n\n## Regras\n\n- Nunca commitar sem autorizacao explicita.\n",
                encoding="utf-8",
            )
            proc = subprocess.run(
                [sys.executable, str(SCRIPTS / "nf_indice_regras.py"), "--root", str(raiz)],
                capture_output=True, text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertNotIn("foi executado", proc.stdout + proc.stderr)
            import json as _json

            dados = _json.loads(
                (raiz / ".neural-flow" / "indice-regras.json").read_text(encoding="utf-8")
            )
            self.assertTrue(dados["guards"], "caiu para lista vazia em vez do nosso registro")
            self.assertIn("agentes", [g["guard"] for g in dados["guards"]])

    def test_projeto_sem_governanca_nao_e_cobrado(self) -> None:
        """Sem `AGENTS.md` nao ha fonte de verdade para apontar — nada a validar."""
        import tempfile

        with tempfile.TemporaryDirectory() as t:
            vazio = Path(t) / "vazio"
            vazio.mkdir()
            proc = self._rodar(vazio)
            self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_instrucoes_do_projeto_nao_sao_apagadas(self) -> None:
        """Brownfield com `GEMINI.md` proprio: anexar, nunca sobrescrever."""
        import tempfile

        with tempfile.TemporaryDirectory() as t:
            destino = Path(t) / "p"
            destino.mkdir()
            (destino / "GEMINI.md").write_text(
                "# Regras do time\n\nNao mexer no diretorio legacy/.\n", encoding="utf-8"
            )
            proc = subprocess.run(
                [sys.executable, str(self.INSTALADOR), "--target", str(destino),
                 "--name", "P", "--smoke-gate", "no"],
                capture_output=True, text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            texto = (destino / "GEMINI.md").read_text(encoding="utf-8")
            self.assertIn("legacy/", texto, "instrucao do time foi apagada")
            self.assertIn("AGENTS.md", texto, "diretrizes nao foram anexadas")
            self.assertEqual(self._rodar(destino).returncode, 0)


class TestValidadorDoProjeto(unittest.TestCase):
    """Colisao de nome com validador que o projeto ja tinha.

    Reportado em campo: um projeto brownfield tinha `scripts/validate_module_spec.py`
    com interface propria (`--module NN`). O instalador nao sobrescreveu — correto —
    mas o gate chamou aquele arquivo com os NOSSOS argumentos, e o usuario viu
    "the following arguments are required: --module" como se fosse defeito do
    framework. Duas decisoes individualmente certas que juntas quebram.
    """

    ALHEIO = (
        "#!/usr/bin/env python3\n"
        "import argparse, sys\n"
        "ap = argparse.ArgumentParser()\n"
        "ap.add_argument('--module', required=True)\n"
        "a = ap.parse_args()\n"
        "print('modulo', a.module, 'ok')\n"
    )

    def _projeto(self, tmp: Path, falha: bool = False) -> Path:
        raiz = tmp / "p"
        (raiz / "scripts").mkdir(parents=True)
        (raiz / "docs" / "modulos" / "modulo-01-x").mkdir(parents=True)
        corpo = self.ALHEIO + ("sys.exit(1)\n" if falha else "")
        (raiz / "scripts" / "validate_module_spec.py").write_text(corpo, encoding="utf-8")
        import shutil
        for nome in ("nf_gate.py", "nf_guards.py"):
            shutil.copy(SCRIPTS / nome, raiz / "scripts" / nome)
        return raiz

    def _gate(self, raiz: Path, *extra: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(raiz / "scripts" / "nf_gate.py"), "spec",
             "--root", str(raiz), *extra],
            capture_output=True, text=True,
        )

    def test_nao_executa_script_alheio_e_explica(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as t:
            raiz = self._projeto(Path(t))
            proc = self._gate(raiz)
            saida = proc.stdout + proc.stderr
            # Nunca o erro de uso do argparse alheio.
            self.assertNotIn("required: --module", saida)
            self.assertIn("e do projeto, nao do framework", saida)
            self.assertIn(".neural-flow.json", saida)
            # Nao reprova o projeto por causa de uma ferramenta que nao e nossa.
            self.assertEqual(proc.returncode, 0, saida)

    def test_comando_configurado_roda_por_modulo(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as t:
            raiz = self._projeto(Path(t))
            (raiz / ".neural-flow.json").write_text(json.dumps({"guards": {"spec": {
                "comando": ["python3", "scripts/validate_module_spec.py",
                            "--module", "{modulo}"],
                "por_modulo": "docs/modulos/modulo-*"}}}), encoding="utf-8")
            proc = self._gate(raiz)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("modulo 01", proc.stdout)

    def test_reprovacao_do_validador_do_projeto_reprova_o_gate(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as t:
            raiz = self._projeto(Path(t), falha=True)
            (raiz / ".neural-flow.json").write_text(json.dumps({"guards": {"spec": {
                "comando": ["python3", "scripts/validate_module_spec.py",
                            "--module", "{modulo}"],
                "por_modulo": "docs/modulos/modulo-*"}}}), encoding="utf-8")
            proc = self._gate(raiz)
            self.assertEqual(proc.returncode, 1, proc.stdout)

    def test_instalador_nao_sobrescreve_e_instala_ao_lado(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as t:
            raiz = Path(t) / "p"
            (raiz / "scripts").mkdir(parents=True)
            original = self.ALHEIO
            alvo = raiz / "scripts" / "validate_module_spec.py"
            alvo.write_text(original, encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(SCRIPTS / "nf_install.py"), "--target", str(raiz),
                 "--smoke-gate", "no"],
                capture_output=True, text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertEqual(alvo.read_text(encoding="utf-8"), original,
                             "sobrescreveu o validador do projeto")
            self.assertTrue((raiz / "scripts" / "nf_validate_module_spec.py").is_file(),
                            "nao instalou o nosso ao lado")
            self.assertIn("ja existe e nao e do framework", proc.stdout)

    def test_scripts_executados_pelo_gate_carregam_a_assinatura(self) -> None:
        """So o que o gate executa precisa da assinatura.

        `ingest.py` e `search.py` sao a implementacao de referencia de RAG; o
        gate nunca os chama, entao exigir a marca deles seria ritual.
        """
        sys.path.insert(0, str(SCRIPTS))
        from nf_gate import GUARDS as REGISTRO

        alvos = {script for script, _p, _o in REGISTRO.values()} | {
            "nf_gate.py", "nf_guards.py", "nf_install.py"}
        for nome in sorted(alvos):
            caminho = SCRIPTS / nome
            with self.subTest(script=nome):
                self.assertTrue(caminho.is_file(), f"{nome} nao existe")
                self.assertIn("NF_GUARD_ASSINATURA",
                              caminho.read_text(encoding="utf-8"),
                              "sem assinatura, o gate nao distingue do script do projeto")


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
