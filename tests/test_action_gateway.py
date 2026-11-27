"""Testes de comportamento da fronteira executavel de acoes."""

from __future__ import annotations

import json
import os
import pty
import re
import select
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


RAIZ = Path(__file__).resolve().parent.parent
SCRIPTS = RAIZ / "scripts"
SPRINT = "docs/sprints/sprint-05-gateway-de-acoes.md"
COMANDO_TESTE = ["python3", "-m", "unittest", "test_smoke"]
sys.path.insert(0, str(SCRIPTS))


class TestActionGateway(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "scripts").mkdir()
        (self.root / "docs" / "sprints").mkdir(parents=True)
        (self.root / ".neural-flow").mkdir()
        for nome in (
            "nf_guards.py",
            "nf_action_policy.py",
            "validate_action_policy.py",
            "validate_sprint_state.py",
            "nf_product_docs.py",
            "nf_action_gateway.py",
        ):
            shutil.copy2(SCRIPTS / nome, self.root / "scripts" / nome)
        shutil.copy2(RAIZ / "docs" / "sprints" / "sprint-05-gateway-de-acoes.md",
                     self.root / SPRINT)
        (self.root / "test_smoke.py").write_text(
            "import unittest\n\nclass Smoke(unittest.TestCase):\n"
            "    def test_ok(self):\n        self.assertTrue(True)\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def policy(self, actions: list[dict], *, version: int = 2, enabled: bool = True) -> None:
        (self.root / ".neural-flow" / "action-policy.json").write_text(
            json.dumps({
                "version": version,
                "enabled": enabled,
                "actions": actions,
                "audit_path": ".neural-flow/action-audit.jsonl",
            }),
            encoding="utf-8",
        )

    def run_gateway(self, action: str, command: list[str], *extra: str, sprint: str = SPRINT) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self.root / "scripts" / "nf_action_gateway.py"),
             "--root", str(self.root), "--action", action, "--sprint", sprint,
             *extra, "--", *command],
            cwd=self.root,
            capture_output=True,
            text=True,
        )

    def action(self, action_id: str, risk: str, argv: list[str], approval: bool) -> dict:
        return {
            "id": action_id,
            "description": "acao de teste",
            "risk": risk,
            "argv": argv,
            "requires_human_approval": approval,
            "max_runtime_seconds": 30,
            "sprint": SPRINT,
            "item": "2.1" if risk != "safe" else "2.2",
        }

    def test_safe_execucao_audita_e_nao_vaza_comando(self) -> None:
        self.policy([self.action(
            "safe-test", "safe", COMANDO_TESTE, False
        )])
        proc = self.run_gateway(
            "safe-test", COMANDO_TESTE
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        log = (self.root / ".neural-flow" / "action-audit.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("test_smoke", log)
        self.assertNotIn('"sandbox"', log)
        self.assertNotIn('"network"', log)
        self.assertIn("Ran 1 test", proc.stderr)
        self.assertIn('"result": 0', log)
        self.assertIn('"command_hash":', log)

    def test_acao_desconhecida_e_bloqueada(self) -> None:
        self.policy([self.action("safe-test", "safe", ["python3", "-m", "unittest"], False)])
        proc = self.run_gateway("nao-existe", ["python3", "-m", "unittest"])
        self.assertEqual(proc.returncode, 2)
        self.assertIn("acao desconhecida", proc.stderr)

    def test_risco_alto_sem_tty_e_bloqueado_antes_do_comando(self) -> None:
        self.policy([self.action("danger", "irreversible", COMANDO_TESTE, True)])
        proc = self.run_gateway("danger", COMANDO_TESTE)
        self.assertEqual(proc.returncode, 3)
        self.assertIn("terminal interativo", proc.stderr)
        log = (self.root / ".neural-flow" / "action-audit.jsonl").read_text(encoding="utf-8")
        self.assertIn('"decision": "denied"', log)
        self.assertIn('"reason": "interactive_tty_required"', log)
        self.assertNotIn("test_smoke", log)
        self.assertNotIn("Ran 1 test", proc.stderr)

    def test_risco_alto_com_aprovacao_exata_executa(self) -> None:
        self.policy([self.action(
            "approval-test", "sensitive", COMANDO_TESTE, True
        )])
        master, slave = pty.openpty()
        argv = [
            sys.executable, str(self.root / "scripts" / "nf_action_gateway.py"),
            "--root", str(self.root), "--action", "approval-test", "--sprint", SPRINT,
            "--", *COMANDO_TESTE,
        ]
        proc = subprocess.Popen(argv, cwd=self.root, stdin=slave, stdout=slave, stderr=slave)
        os.close(slave)
        saida = b""
        prazo = time.monotonic() + 8
        try:
            while b"Desafio: APROVAR " not in saida and time.monotonic() < prazo:
                disponivel, _, _ = select.select([master], [], [], 0.25)
                if disponivel:
                    saida += os.read(master, 4096)
            desafio = re.search(rb"Desafio: APROVAR ([0-9a-f]{16})", saida)
            self.assertIsNotNone(desafio, saida.decode(errors="replace"))
            os.write(master, b"APROVAR " + desafio.group(1) + b"\n")
            proc.wait(timeout=8)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
            os.close(master)
        self.assertEqual(proc.returncode, 0, saida.decode(errors="replace"))
        log = (self.root / ".neural-flow" / "action-audit.jsonl").read_text(encoding="utf-8")
        self.assertIn('"approval_method": "interactive_tty"', log)
        self.assertIn('"decision": "approved"', log)

    def test_argumento_adicional_e_bloqueado_inclusive_em_plano(self) -> None:
        self.policy([self.action("safe-test", "safe", COMANDO_TESTE, False)])
        plano = self.run_gateway("safe-test", COMANDO_TESTE, "--plan")
        self.assertEqual(plano.returncode, 0, plano.stderr)
        self.assertIn("ALLOW-PLAN", plano.stdout)
        for extra in ((), ("--plan",)):
            proc = self.run_gateway("safe-test", [*COMANDO_TESTE, "-v"], *extra)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("argv completo", proc.stderr)
            self.assertNotIn("Ran 1 test", proc.stderr)
        self.assertFalse((self.root / ".neural-flow" / "action-audit.jsonl").exists())

    def test_politica_v1_exige_migracao_inclusive_em_plano(self) -> None:
        self.policy([], version=1, enabled=False)
        for extra in ((), ("--plan",)):
            proc = self.run_gateway("safe-test", COMANDO_TESTE, *extra)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("migracao explicita", proc.stderr)

    def test_politica_desabilitada_bloqueia_comando(self) -> None:
        self.policy([], enabled=False)
        proc = self.run_gateway("safe-test", COMANDO_TESTE)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("politica desabilitada", proc.stderr)

    def test_sprint_incompativel_bloqueia_comando(self) -> None:
        self.policy([self.action("safe-test", "safe", COMANDO_TESTE, False)])
        proc = self.run_gateway("safe-test", COMANDO_TESTE, sprint="outra.md")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("acao nao pertence a sprint", proc.stderr)

    def test_auditoria_indisponivel_bloqueia_comando(self) -> None:
        (self.root / ".neural-flow" / "action-audit.jsonl").mkdir()
        self.policy([self.action("safe-test", "safe", COMANDO_TESTE, False)])
        proc = self.run_gateway("safe-test", COMANDO_TESTE)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("nao foi possivel escrever auditoria", proc.stderr)
        self.assertNotIn("Ran 1 test", proc.stderr)

    def test_timeout_e_auditado(self) -> None:
        (self.root / "espera.py").write_text("import time\ntime.sleep(10)\n", encoding="utf-8")
        command = ["python3", "espera.py"]
        action = self.action("safe-test", "safe", command, False)
        action["max_runtime_seconds"] = 1
        self.policy([action])
        proc = self.run_gateway("safe-test", command)
        self.assertEqual(proc.returncode, 124, proc.stderr)
        log = (self.root / ".neural-flow" / "action-audit.jsonl").read_text(encoding="utf-8")
        self.assertIn('"result": "timeout"', log)

    def test_falha_de_inicio_e_auditada(self) -> None:
        command = ["./executavel-ausente"]
        self.policy([self.action("safe-test", "safe", command, False)])
        proc = self.run_gateway("safe-test", command)
        self.assertEqual(proc.returncode, 2)
        log = (self.root / ".neural-flow" / "action-audit.jsonl").read_text(encoding="utf-8")
        self.assertIn('"result": "start_failed"', log)


if __name__ == "__main__":
    unittest.main()
