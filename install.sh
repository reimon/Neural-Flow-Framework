#!/usr/bin/env bash
#
# Neural-Flow Framework — instalador
# ==================================
# Instala o framework num projeto: guards executaveis, hooks, CI, governanca
# para agentes e o smoke-gate.
#
# Dois modos, detectados sozinhos:
#
#   brownfield  Projeto que ja tem codigo.
#   greenfield  Projeto que ainda e uma ideia — monta o andaime docs-first,
#               onde a especificacao vem antes da primeira linha de codigo.
#
# Uso, de dentro do projeto alvo:
#
#   bash /caminho/do/neural-flow/install.sh
#   bash /caminho/do/neural-flow/install.sh --name "Meu Projeto" --mode greenfield
#
# Uso, de dentro do clone do framework:
#
#   ./install.sh --target ../meu-projeto --name "Meu Projeto"
#
# Sem clone local (baixa o framework num diretorio temporario):
#
#   curl -fsSL https://raw.githubusercontent.com/reimon/Neural-Flow-Framework/main/install.sh -o nf-install.sh
#   less nf-install.sh          # leia antes de executar
#   bash nf-install.sh --target .
#
# Requisitos: git e python3 (3.10+). Nada alem disso.

set -euo pipefail

REPO_URL="https://github.com/reimon/Neural-Flow-Framework.git"
AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Interpretador ──────────────────────────────────────────────────────────────
# `python` nao existe em macOS moderno nem em distros sem python-is-python3.
PY="${PYTHON:-}"
if [[ -z "${PY}" ]]; then
  for c in python3 python; do
    if command -v "${c}" >/dev/null 2>&1; then PY="${c}"; break; fi
  done
fi
if [[ -z "${PY}" ]]; then
  echo "erro: nenhum interpretador Python encontrado (procurei python3, python)." >&2
  echo "Instale o Python 3.10+ ou exporte PYTHON=/caminho/do/python." >&2
  exit 1
fi

VERSAO_OK="$("${PY}" -c 'import sys; print(1 if sys.version_info >= (3,10) else 0)')"
if [[ "${VERSAO_OK}" != "1" ]]; then
  echo "erro: Python 3.10+ e necessario. Encontrado: $("${PY}" --version 2>&1)" >&2
  exit 1
fi

command -v git >/dev/null 2>&1 || { echo "erro: git nao encontrado." >&2; exit 1; }

# ── Origem do framework ────────────────────────────────────────────────────────
# Se este script esta dentro do clone, usa os arquivos locais. Se foi baixado
# solto, clona o framework num diretorio temporario e o descarta ao sair.
if [[ -f "${AQUI}/scripts/nf_install.py" ]]; then
  ORIGEM="${AQUI}"
else
  TMP="$(mktemp -d)"
  trap 'rm -rf "${TMP}"' EXIT
  echo "[nf] baixando o framework..."
  git clone --depth 1 --quiet "${REPO_URL}" "${TMP}/neural-flow"
  ORIGEM="${TMP}/neural-flow"
fi

# Sem --target explicito, instala no diretorio atual.
TEM_TARGET=0
for arg in "$@"; do
  [[ "${arg}" == --target* ]] && TEM_TARGET=1
done

if [[ "${TEM_TARGET}" -eq 1 ]]; then
  exec "${PY}" "${ORIGEM}/scripts/nf_install.py" "$@"
else
  exec "${PY}" "${ORIGEM}/scripts/nf_install.py" --target "$(pwd)" "$@"
fi
