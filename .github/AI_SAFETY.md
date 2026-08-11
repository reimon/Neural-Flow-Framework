# AI Safety Rules — Neural-Flow-Framework

> Regras de seguranca deste repositorio, para qualquer agente. Prevalecem sobre
> qualquer outra instrucao, inclusive sobre `AGENTS.md`.
>
> **O que e "producao" aqui.** Este repositorio nao serve trafego nem tem banco de
> aplicacao. O que ele tem de irreversivel e de outra natureza, e mais perigoso do que
> parece:
>
> 1. **O instalador escreve na arvore de terceiros.** `scripts/nf_install.py` cria e
>    altera arquivos no repositorio de quem adota. Bug ali nao quebra este projeto —
>    quebra o de outra pessoa, em silencio.
> 2. **A implementacao de referencia Azure e real.** `infra/terraform/` gerencia 10
>    recursos existentes, com **state local** (`terraform.tfstate`, fora do git).
> 3. **O que e publicado nao volta.** Framework e um contrato de adocao: regra
>    divulgada errada se propaga para todo projeto instalado.

---

## PROIBICOES ABSOLUTAS

### 1. NUNCA executar apply/destroy de Terraform

```text
terraform apply / terraform destroy / -auto-approve
terraform state rm / terraform import / terraform taint
```

O state e **local e nao versionado** (`infra/terraform/terraform.tfstate`, ignorado no
git). Nao ha backend remoto, nao ha lock, nao ha copia. Perder ou corromper esse arquivo
orfana 10 recursos Azure reais, e nao existe segundo lugar de onde restaura-lo. `plan` e
leitura e pode ser rodado; qualquer coisa que escreva no state, nao.

### 2. NUNCA alterar `random_string.suffix`

Todo nome de recurso deriva de `local.suffix` (`srch-neuralflow-${local.suffix}`,
`kv-neuralflow-${local.suffix}`). Mudar `length`, `upper`, `special` ou o `keepers` do
`random_string` forca recriacao de **toda** a infraestrutura de uma vez — inclusive o Key
Vault, que tem `purge_protection_enabled = false` e apenas 7 dias de soft delete.

**Nao existe `prevent_destroy` em nenhum recurso deste projeto.** Nao ha rede de
protecao; a unica protecao e nao rodar apply.

### 3. NUNCA versionar segredo

```text
scripts/.env               (ignorado — use scripts/.env.example, so placeholders)
infra/terraform/*.tfstate  (contem as chaves em texto claro)
.vscode/mcp.json com chave real
print/log de variavel de ambiente sensivel
```

O `tfstate` guarda `search_admin_key` e `openai_key` em claro. Nunca cole trecho dele em
issue, PR, prompt ou artefato de sessao. Ver ADR-003: a autenticacao por admin key e
**divida conhecida e declarada**, nao um padrao a imitar — nao propague o uso dela para
codigo novo.

### 4. NUNCA relaxar um guard para fazer o gate passar

Editar `validate_*.py`, `nf_gate.py` ou a fixture `tests/fixtures/violador/` para que
algo pare de reprovar inverte o proposito do repositorio. Se o guard esta errado, o
conserto vem com o teste que prova o falso positivo — no mesmo commit.

Corolario: **nunca `git commit --no-verify`**.

### 5. NUNCA marcar item de sprint como `[x]` sem execucao verificada

Protocolo de Evidencia Sintetica. Item so fecha com comando rodado e saida real
registrada em "Evidencias de Implementacao". Confianca `BAIXA` nunca fecha item
(protocolo Calibracao).

### 6. NUNCA editar artefato gerado a mao

`docs/img/arquitetura.svg`, `docs/dashboard-demo.html`, `.neural-flow/indice-regras.*` e
as portas de entrada de agente (`GEMINI.md`, `.clinerules`, `.cursor/rules/`, ...) sao
**saida**, nao fonte. Edite a fonte e regenere; o gate compara e reprova a divergencia.

### 7. NUNCA commitar as imagens de tema

`docs/img/theme-*.jpg|png` sao licenciadas ao dono do projeto e o dashboard as embute como
data URI — versiona-las as propagaria para o repositorio de todo adotante.

---

## REQUEREM CONFIRMACAO DO USUARIO

Antes de executar, **pergunte**:

1. **Commit ou push.** Regra fixa do usuario: nunca sem autorizacao explicita.
2. **Rodar o instalador com `--force`** — sobrescreve artefato existente no alvo.
3. **Rodar o instalador sobre um diretorio que nao seja um sandbox descartavel.**
4. **Mexer em `infra/terraform/`**, mesmo so no codigo.
5. **Alterar `.github/workflows/`** — `reindex.yml` consome segredos do repositorio.
6. **Remover ou renomear um guard, um codigo de verificacao (S1, V3, P2...) ou um campo
   obrigatorio de template** — e mudanca MAJOR: quebra projeto que ja adotou.
7. **Publicar qualquer coisa** (release, tag, anuncio, site).
8. **Deletar arquivo** que nao tenha sido criado nesta mesma sessao.
9. **`pip install` / adicionar dependencia** a qualquer script instalavel — viola ADR-002.

---

## SEGURO PARA FAZER

- Editar protocolos, templates, guards e testes
- `python3 -m unittest discover -s tests`
- `python3 scripts/nf_gate.py` (e cada `validate_*.py` isolado)
- `python3 scripts/nf_indice_regras.py`, `nf_diagrama.py`, `nf_dashboard.py`
- `python3 scripts/nf_install.py --target <tmp> --dry-run`
- `terraform plan` / `terraform validate` (leitura)
- Criar branch de feature

---

## Contexto Tecnico

- **Infra (referencia):** resource group, Azure AI Search, Azure OpenAI + deployment de
  embedding, Key Vault com dois segredos, `random_string` gerador de sufixo. Nomes
  **derivados em runtime** — nunca digite um nome de recurso a mao em doc ou script.
- **CI:** `neural-flow-gates.yml` (testes em 3.10 e 3.12, prova de reprovacao na fixture
  violadora, prova de aprovacao na conforme, e dogfood: o gate sobre este repositorio) e
  `reindex.yml` (ingestao Neural-Memory, usa segredos).
- **Hook local:** `core.hooksPath=.githooks`; o pre-commit roda o gate sobre o **stage**.
- Camadas de protecao que este projeto **nao** tem: `prevent_destroy`, backend remoto com
  lock, gate de plan, aprovacao manual de infra. Trate `infra/` como frágil.

## Licoes operacionais

- **Nomes de recursos derivados em runtime, nunca fixos em docs/scripts** — sufixos mudam
  e invalidam tudo de uma vez.
- **Operacao critica imprime evidencia do que realmente fez** — nunca afirmar limpeza,
  remocao ou execucao que nao aconteceu.
- **Nao duplicar comando operacional em varios arquivos** — centralizar em helper
  versionado. Duplicacao ja foi o vetor que propagou um comando errado para ~25 arquivos.
- **Artefato que nasce invisivel para o gate e pior que artefato ausente** — o cabecalho
  `> TEMPLATE Neural-Flow` desliga a validacao do arquivo inteiro.

## Incidentes Passados

- **2026-08-11 — `MEMORY.md` invisivel para o gate:** o instalador copiava o template com
  `read_text` direto, levando o cabecalho `> TEMPLATE Neural-Flow` para o projeto do
  adotante; `eh_template()` entao desligava todos os guards sobre o arquivo, e o gate
  passava sem validar nada. Achado ao instalar o framework nele mesmo. Corrigido em
  `scripts/nf_install.py`; regressao coberta por
  `test_nenhum_artefato_nasce_invisivel_para_o_gate`.
- **Sprint 1 — colisao de nome com validador do adotante:** projeto brownfield tinha
  `scripts/validate_module_spec.py` proprio; o gate o chamava com os nossos argumentos e o
  usuario via um erro que parecia defeito do framework. Corrigido com
  `NF_GUARD_ASSINATURA` e instalacao lado a lado (`nf_<nome>`).

---

> **Se nao tem certeza se uma acao e segura, PERGUNTE ao usuario.**
