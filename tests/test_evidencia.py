import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SCRIPTS = RAIZ / "scripts"
sys.path.insert(0, str(SCRIPTS))


def cli(script, raiz, *opcoes):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), "--root", str(raiz), *opcoes],
        text=True, capture_output=True,
    )


def adr(pasta, numero, status, decisao):
    caminho = pasta / f"ADR-{numero:03d}-teste.md"
    caminho.write_text(
        f"# ADR-{numero:03d} - Teste\n\n## Status\n{status}\n\n## Decisao\n"
        f"{decisao}\n\n## Evidencia\n- Sprint de origem: Sprint 1\n- Guard associado: teste\n",
        encoding="utf-8",
    )


class Vigencia(unittest.TestCase):
    def test_superacao_parcial_preserva_regra_de_outro_escopo(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            pasta = raiz / "docs/adr"
            pasta.mkdir(parents=True)
            adr(pasta, 1, "Aceito", "### Execucao de auditoria\n- Toda auditoria exige revisao independente.\n### Execucao\n- Toda acao exige o executor antigo."
                "\n### Dados\n- Toda tabela exige uma chave primaria.")
            adr(pasta, 2, "Aceito\n\nSupera ADR-001 no contrato de execucao.",
                "Validar localmente com os testes.")
            proc = cli("nf_indice_regras.py", raiz)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            indice = raiz / ".neural-flow/indice-regras"
            dados = json.loads(indice.with_suffix(".json").read_text())
            vigentes = [r["regra"] for r in dados["regras"]]
            self.assertIn("Toda tabela exige uma chave primaria.", vigentes)
            self.assertIn("Toda auditoria exige revisao independente.", vigentes)
            self.assertNotIn("Toda acao exige o executor antigo.", vigentes)
            historica, = dados["regras_historicas"]
            self.assertEqual(historica["superacoes"][0]["sucessor"], "ADR-002")
            self.assertEqual(historica["superacoes"][0]["escopo"], "execucao")
            self.assertIn("Validar localmente com os testes.", indice.with_suffix(".md").read_text())

    def test_guard_confere_multiplos_destinos_e_ciclo_misto(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            pasta = raiz / "docs/adr"
            pasta.mkdir(parents=True)
            adr(pasta, 1, "Superado por ADR-002", "Anterior.")
            adr(pasta, 2, "Aceito\nSupera ADR-003,\nADR-004 no contrato de execucao.", "Intermediario.")
            adr(pasta, 3, "Aceito\nSupera ADR-002.", "Fechar ciclo.")
            proc = cli("nf_gate.py", raiz, "adr")
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertIn("[A3]", proc.stdout)
            self.assertIn("[A4]", proc.stdout)


class Relatorio(unittest.TestCase):
    def test_projeto_vazio_distingue_ausencia_de_conformidade(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            proc = cli("nf_gate.py", raiz, "--format", "json")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            guards = json.loads(proc.stdout)["guards"]
            self.assertEqual(len(guards), 7)
            self.assertEqual({g["estado"] for g in guards}, {"sem_artefato"})
            self.assertIn("0 guard(s) conforme", cli("nf_gate.py", raiz).stdout)

    def test_falha_traz_codigo_arquivo_e_linha(self):
        proc = cli("nf_gate.py", RAIZ / "tests/fixtures/violador", "adr", "--format", "json")
        self.assertEqual(proc.returncode, 1, proc.stderr)
        guard, = json.loads(proc.stdout)["guards"]
        self.assertEqual(guard["estado"], "falhou")
        erro = next(e for e in guard["achados"] if e["codigo"] == "A3")
        self.assertTrue(erro["arquivo"].startswith("docs/adr/"))
        self.assertGreater(erro["linha"], 0)

    def test_validador_proprio_compartilha_achados_sem_reexecutar_no_painel(self):
        from nf_dashboard import coletar_guards

        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            scripts = raiz / "scripts"
            scripts.mkdir()
            proprio = scripts / "validate_module_spec.py"
            proprio.write_text(
                'from pathlib import Path\nimport sys\n'
                'with Path("chamadas").open("a") as f: f.write("1")\n'
                'print("[P10] docs/modulos/demo.md:11 — falta <dado>")\n'
                'sys.exit(1)\n', encoding="utf-8",
            )
            proc = cli("nf_gate.py", raiz, "spec", "--format", "json")
            self.assertEqual(json.loads(proc.stdout)["guards"][0]["estado"], "nao_executado")
            (raiz / ".neural-flow.json").write_text(json.dumps({"guards": {"spec": {
                "comando": [sys.executable, str(proprio)],
            }}}))
            resumo = raiz / "resumo.md"
            proc = cli("nf_gate.py", raiz, "spec", "--format", "json", "--resumo-github", str(resumo))
            self.assertEqual(proc.returncode, 1, proc.stderr)
            self.assertEqual((raiz / "chamadas").read_text(), "1")
            relatorio = raiz / "resultado.json"
            relatorio.write_text(proc.stdout)
            guard, = json.loads(proc.stdout)["guards"]
            erro, = guard["achados"]
            self.assertEqual((erro["codigo"], erro["arquivo"], erro["linha"]),
                             ("P10", "docs/modulos/demo.md", 11))
            self.assertIn("[P10] docs/modulos/demo.md:11", resumo.read_text())
            self.assertIn("&lt;dado&gt;", resumo.read_text())
            painel, = coletar_guards(raiz, relatorio)
            self.assertEqual(painel["estado"], "fail")
            self.assertIn("docs/modulos/demo.md:11", painel["achados"][0]["msg"])
            self.assertEqual((raiz / "chamadas").read_text(), "1")

    def test_instalacao_lado_a_lado_avalia_ambos_quando_configurado(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            pasta = raiz / "scripts"
            pasta.mkdir()
            (pasta / "nf_validate_module_spec.py").write_text(
                '# NF_GUARD_ASSINATURA\nprint("spec-first: PASS — 1 arquivo(s) conforme")\n'
            )
            proprio = pasta / "validate_module_spec.py"
            proprio.write_text('print("[P10] dados.md:4 — incompleto")\nraise SystemExit(1)\n')
            (raiz / ".neural-flow.json").write_text(json.dumps({"guards": {"spec": {
                "comando": [sys.executable, str(proprio)]
            }}}))
            proc = cli("nf_gate.py", raiz, "spec", "--format", "json")
            self.assertEqual(proc.returncode, 1, proc.stdout)
            guard, = json.loads(proc.stdout)["guards"]
            self.assertEqual(guard["achados"][0]["codigo"], "P10")

    def test_mesmos_estados_no_terminal_resumo_e_painel(self):
        from nf_dashboard import coletar_guards

        estados_painel = {"conforme": "pass", "falhou": "fail", "sem_artefato": "sem_artefato",
                          "nao_executado": "nao_executado"}
        for fixture, codigo in (("conforme", 0), ("violador", 1)):
            with self.subTest(fixture=fixture), tempfile.TemporaryDirectory() as tmp:
                raiz = RAIZ / "tests/fixtures" / fixture
                resumo = Path(tmp) / "resumo.md"
                proc = cli("nf_gate.py", raiz, "--format", "json", "--resumo-github", str(resumo))
                self.assertEqual(proc.returncode, codigo)
                guards = json.loads(proc.stdout)["guards"]
                terminal = cli("nf_gate.py", raiz, "--quiet")
                self.assertEqual(terminal.returncode, codigo)
                painel = {g["nome"]: g["estado"] for g in coletar_guards(raiz)}
                self.assertEqual(len(guards), 7)
                for g in guards:
                    nome, estado = g["nome"], g["estado"]
                    self.assertEqual(painel[nome], estados_painel[estado])
                    self.assertIn(f"{nome}: {estado.replace('_', ' ')}", terminal.stdout)
                    self.assertIn(f"| {nome} | {estado.replace('_', ' ')} |", resumo.read_text())
