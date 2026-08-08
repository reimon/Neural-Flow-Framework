# AI Safety Rules — <Nome do Projeto>

> TEMPLATE Neural-Flow. Copie para `.github/AI_SAFETY.md` e preencha os blocos `<...>`.
> Evolucao operacional do Aegis Protocol, validada em producao.

> **Este arquivo e lido por TODAS as ferramentas de IA** (GitHub Copilot,
> Claude Code, Cursor, Windsurf, Cline, Aider, etc.).
> As regras aqui sao OBRIGATORIAS independente da ferramenta.

---

## PROIBICOES ABSOLUTAS

### 1. NUNCA fazer deploy manual

```text
<listar comandos proibidos: az webapp deploy, swa deploy, deploy.sh, kubectl apply prod...>
```

Deploy e EXCLUSIVAMENTE via CI (`<workflow>`).

### 2. NUNCA executar apply de IaC diretamente

```text
terraform apply / destroy / -auto-approve
<equivalentes: pulumi up, cdk deploy...>
```

Apply e executado APENAS pelo CI. Para mudar infra: edite o codigo IaC, abra PR,
o pipeline cuida.

### 3. NUNCA remover lifecycle guards

Blocos `prevent_destroy = true` (ou equivalente) sao protecao contra destruicao
acidental. Recursos protegidos:

- `<recurso stateful 1 — banco>`
- `<recurso 2 — key vault / storage>`
- `<recurso gerador de nomes (random suffix) — ponto unico de falha que cascateia>`

### 4. NUNCA modificar o gerador de sufixo/nome de recursos

Alterar atributos de `<random_string/sufixo>` forca recriacao de TODA a infra.
(Incidente real: mudanca de sufixo recriou 20 recursos e derrubou login por 2h.)

### 5. NUNCA rodar comandos destrutivos em banco de producao

```text
DROP TABLE / DROP DATABASE / TRUNCATE
DELETE FROM ... (sem WHERE restritivo)
ALTER TABLE ... DROP COLUMN (sem backup)
```

### 6. NUNCA expor secrets

```text
console.log/print de env sensivel
hardcode de senha/chave em codigo
commit de .env, *.tfvars com secrets
```

---

## REQUEREM CONFIRMACAO DO USUARIO

Antes de executar, **pergunte**:

1. Modificar arquivos de IaC (`<dir>`) — pode causar downtime.
2. Criar/modificar migrations — schema em producao e irreversivel.
3. Deletar arquivos.
4. Modificar workflows de CI/CD.
5. `git push` para a branch de deploy.
6. Abrir regra de firewall temporaria — SEMPRE remover apos uso (preferir helper
   com `trap EXIT` que remove sozinho e imprime evidencia de criacao/remocao).

---

## SEGURO PARA FAZER

- Editar codigo de aplicacao (`<dirs>`)
- Rodar testes, build, lint
- Ler configuracao
- Ambiente local (docker compose up/down)
- Criar branches de feature

---

## Contexto Tecnico

- `<recursos de infra por nome — derivados, nunca digitados a mao>`
- `<pipeline de deploy resumido>`
- Camadas de seguranca de IaC: prevent_destroy → gate de plan (bloqueia
  DELETE/REPLACE de stateful) → aprovacao manual → remote state com lock.

## Licoes operacionais (padrao Neural-Flow)

- Nomes de recursos derivados em runtime, nunca fixos em docs/scripts — sufixos
  mudam e invalidam tudo de uma vez.
- Operacao critica imprime **evidencia** (`EVIDENCE_*`) do que realmente fez;
  nunca afirmar limpeza/remocao que nao aconteceu.
- Nao duplicar comandos operacionais em varios arquivos — centralizar em helper
  versionado; duplicacao foi o vetor de propagacao de comando errado em ~25 arquivos.

## Incidentes Passados

- `<data>`: `<resumo>` — post-mortem: `<link>`

---

> **Se nao tem certeza se uma acao e segura, PERGUNTE ao usuario.**
