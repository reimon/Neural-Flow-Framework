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
            "nf_sandbox.py",
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

    def policy(self, actions: list[dict], sandbox: str = "off") -> None:
        (self.root / ".neural-flow" / "action-policy.json").write_text(
            json.dumps({
                "version": 1,
                "enabled": True,
                "execution": {"sandbox": sandbox, "network": False},
                "actions": actions,
                "audit_path": ".neural-flow/action-audit.jsonl",
            }),
            encoding="utf-8",
        )

    def run_gateway(self, action: str, command: list[str], *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self.root / "scripts" / "nf_action_gateway.py"),
             "--root", str(self.root), "--action", action, "--sprint", SPRINT,
             *extra, "--", *command],
            cwd=self.root,
            capture_output=True,
            text=True,
        )

    def action(self, action_id: str, risk: str, prefix: list[str], approval: bool) -> dict:
        return {
            "id": action_id,
            "description": "acao de teste",
            "risk": risk,
            "argv_prefix": prefix,
            "requires_human_approval": approval,
            "max_runtime_seconds": 30,
            "sprint": SPRINT,
            "item": "2.1" if risk != "safe" else "2.2",
        }

    def test_safe_execucao_audita_e_nao_vaza_comando(self) -> None:
        self.policy([self.action(
            "safe-test", "safe", ["python3", "-m", "unittest", "discover"], False
        )])
        proc = self.run_gateway(
            "safe-test", ["python3", "-m", "unittest", "discover", "-s", ".", "-p", "test_smoke.py"]
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        log = (self.root / ".neural-flow" / "action-audit.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("NAO_VAZAR", log)
        self.assertIn('"result": 0', log)
        self.assertIn('"command_hash":', log)

    def test_acao_desconhecida_e_bloqueada(self) -> None:
        self.policy([self.action("safe-test", "safe", ["python3", "-m", "unittest"], False)])
        proc = self.run_gateway("nao-existe", ["python3", "-m", "unittest"])
        self.assertEqual(proc.returncode, 2)
        self.assertIn("acao desconhecida", proc.stderr)

    def test_risco_alto_sem_tty_e_bloqueado_antes_do_comando(self) -> None:
        self.policy([self.action("danger", "irreversible", ["git", "push"], True)])
        proc = self.run_gateway("danger", ["git", "push", "origin", "main"])
        self.assertEqual(proc.returncode, 3)
        self.assertIn("terminal interativo", proc.stderr)
        log = (self.root / ".neural-flow" / "action-audit.jsonl").read_text(encoding="utf-8")
        self.assertIn('"decision": "denied"', log)
        self.assertIn('"reason": "interactive_tty_required"', log)
        self.assertNotIn("git push", log)

    def test_risco_alto_com_aprovacao_exata_executa(self) -> None:
        self.policy([self.action(
            "approval-test", "sensitive", ["python3", "-m", "unittest", "discover"], True
        )])
        master, slave = pty.openpty()
        argv = [
            sys.executable, str(self.root / "scripts" / "nf_action_gateway.py"),
            "--root", str(self.root), "--action", "approval-test", "--sprint", SPRINT,
            "--", "python3", "-m", "unittest", "discover", "-s", ".", "-p", "test_smoke.py",
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

    def test_sandbox_obrigatoria_falha_fechado_sem_recurso(self) -> None:
        from nf_sandbox import command_for

        with self.assertRaisesRegex(RuntimeError, "adaptador validado"):
            command_for(self.root, ["python3", "-m", "unittest"], "required", False)

    def test_sandbox_opcional_declara_ausencia_sem_fingir_isolamento(self) -> None:
        from nf_sandbox import command_for

        command, backend = command_for(
            self.root, ["python3", "-m", "unittest"], "when-available", False
        )
        self.assertEqual(command, ["python3", "-m", "unittest"])
        self.assertEqual(backend, "unavailable")


if __name__ == "__main__":
    unittest.main()
