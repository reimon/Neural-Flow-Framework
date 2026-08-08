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
