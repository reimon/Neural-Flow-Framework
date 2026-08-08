#!/usr/bin/env bash
# Neural-Flow Framework — Git Hook Installer
# Installs a post-commit hook that triggers incremental ingestion
# into the Azure AI Search neural-memory index after every commit.
#
# Usage:
#   bash scripts/setup-hooks.sh
#
# Prerequisites:
#   - scripts/.env populated with AZURE_* variables
#   - pip install -r scripts/requirements.txt

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOKS_DIR="${REPO_ROOT}/.git/hooks"
HOOK_FILE="${HOOKS_DIR}/post-commit"
SCRIPT_DIR="${REPO_ROOT}/scripts"

echo "[hooks] Repository root: ${REPO_ROOT}"

# ── Write hook script ──────────────────────────────────────────────────────────

cat > "${HOOK_FILE}" <<'HOOKEOF'
#!/usr/bin/env bash
# Neural-Flow post-commit hook — incremental ingestion into neural-memory index
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
SCRIPT="${REPO_ROOT}/scripts/ingest.py"

if [[ ! -f "${SCRIPT}" ]]; then
  exit 0
fi

# Run only if .env exists (silently skip in CI where env vars are injected)
ENV_FILE="${REPO_ROOT}/scripts/.env"
if [[ ! -f "${ENV_FILE}" ]]; then
  echo "[neural-hook] scripts/.env not found — skipping local ingestion."
  exit 0
fi

echo "[neural-hook] Running incremental ingestion..."
python "${SCRIPT}" --changed-only || echo "[neural-hook] Ingestion failed (non-blocking)."
HOOKEOF

chmod +x "${HOOK_FILE}"
echo "[hooks] post-commit hook installed at: ${HOOK_FILE}"
echo "[hooks] Done. Run 'bash scripts/setup-hooks.sh' again after any future hook changes."
