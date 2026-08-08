#!/usr/bin/env bash
# Neural-Flow Framework — Git Hook Installer
# Instala um hook post-commit que dispara a ingestao incremental no indice
# neural-memory apos cada commit.
#
# Uso:
#   bash scripts/setup-hooks.sh
#
# Pre-requisitos:
#   - scripts/.env preenchido com as variaveis do backend de indice
#   - pip install -r scripts/requirements.txt

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
SCRIPT_DIR="${REPO_ROOT}/scripts"

# ── Onde o git realmente procura hooks ─────────────────────────────────────────
# Quando `core.hooksPath` esta configurado, o git usa SOMENTE aquele diretorio e
# ignora `.git/hooks` por completo. O guia de adocao manda rodar
# `git config core.hooksPath .githooks` para o pre-commit — instalar o
# post-commit em `.git/hooks` nesse cenario cria um hook que nunca executa.
HOOKS_PATH="$(git config --get core.hooksPath || true)"
if [[ -n "${HOOKS_PATH}" ]]; then
  case "${HOOKS_PATH}" in
    /*) HOOKS_DIR="${HOOKS_PATH}" ;;
    *)  HOOKS_DIR="${REPO_ROOT}/${HOOKS_PATH}" ;;
  esac
  echo "[hooks] core.hooksPath ativo — instalando em: ${HOOKS_DIR}"
else
  HOOKS_DIR="${REPO_ROOT}/.git/hooks"
fi

mkdir -p "${HOOKS_DIR}"
HOOK_FILE="${HOOKS_DIR}/post-commit"

echo "[hooks] Repositorio: ${REPO_ROOT}"

# ── Escreve o hook ─────────────────────────────────────────────────────────────

cat > "${HOOK_FILE}" <<'HOOKEOF'
#!/usr/bin/env bash
# Neural-Flow post-commit hook — ingestao incremental no indice neural-memory
set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
SCRIPT="${REPO_ROOT}/scripts/ingest.py"

[[ -f "${SCRIPT}" ]] || exit 0

# Roda so quando ha configuracao local (em CI as variaveis vem do ambiente).
ENV_FILE="${REPO_ROOT}/scripts/.env"
if [[ ! -f "${ENV_FILE}" ]]; then
  echo "[neural-hook] scripts/.env ausente — ingestao local pulada."
  exit 0
fi

# Interpretador: `python` nao existe em macOS moderno nem em distros sem
# python-is-python3. Resolver em tempo de execucao, nunca fixar o nome.
PY="${PYTHON:-}"
if [[ -z "${PY}" ]]; then
  for candidato in python3 python; do
    if command -v "${candidato}" >/dev/null 2>&1; then
      PY="${candidato}"
      break
    fi
  done
fi

# Falta de interpretador e erro de CONFIGURACAO, nao falha de ingestao: precisa
# ser barulhento. Tratar os dois casos como "nao-bloqueante" fazia o reindex
# nunca acontecer e ninguem perceber.
if [[ -z "${PY}" ]]; then
  echo "[neural-hook] ERRO: nenhum interpretador Python encontrado (procurei python3, python)." >&2
  echo "[neural-hook] Instale o Python ou exporte PYTHON=/caminho/do/python." >&2
  echo "[neural-hook] O indice neural-memory NAO foi atualizado." >&2
  exit 0   # post-commit nao desfaz commit; o aviso e o que importa
fi

echo "[neural-hook] Ingestao incremental com ${PY}..."
if "${PY}" "${SCRIPT}" --changed-only; then
  echo "[neural-hook] EVIDENCE_INDICE_ATUALIZADO"
else
  status=$?
  echo "[neural-hook] Ingestao falhou (codigo ${status}) — indice NAO atualizado." >&2
  echo "[neural-hook] Rode manualmente: ${PY} scripts/ingest.py --changed-only" >&2
fi
exit 0
HOOKEOF

chmod +x "${HOOK_FILE}"

# ── Verificacao: o hook precisa ser executavel de fato ─────────────────────────
if ! bash -n "${HOOK_FILE}"; then
  echo "[hooks] ERRO: hook gerado tem erro de sintaxe." >&2
  exit 1
fi

echo "[hooks] post-commit instalado em: ${HOOK_FILE}"
echo "[hooks] Rode este script novamente apos qualquer mudanca no hook."
