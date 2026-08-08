# ADR-003 — Divida conhecida: admin key em vez de Entra ID/RBAC

## Status

Aceito (Sprint 1)

## Contexto

O protocolo Aegis prega "zero segredo em prompt, memoria ou artefato". A implementacao de
referencia deste repositorio contradiz parcialmente esse principio: a autenticacao contra
Azure AI Search e Azure OpenAI usa **admin key** distribuida por quatro caminhos —
`scripts/.env`, `.vscode/mcp.json`, GitHub Secrets e um segredo gravado no Key Vault pelo
Terraform (`infra/terraform/main.tf`).

A recomendacao vigente da Microsoft (verificada em 2026-08) e autenticacao **keyless** via
Microsoft Entra ID + RBAC (`DefaultAzureCredential` com as roles Search Index Data
Contributor / Reader). Os proprios docstrings de `scripts/ingest.py` mencionam
`DefaultAzureCredential` como alternativa, mas o codigo nao a implementa.

Publicar o framework sem registrar isto seria o modo de falha que o protocolo de
Calibracao proibe: afirmar com a mesma firmeza o que foi verificado e o que foi suposto.

## Decisao

Registrar a divida explicitamente em vez de silencia-la ou de bloquear a divulgacao por
causa dela:

1. A divida fica declarada aqui, no README e no protocolo Aegis.
2. A admin key permanece **apenas** na implementacao de referencia Azure; nenhum protocolo,
   template ou guard depende dela.
3. A migracao para RBAC entra como item de sprint futura, nao como pre-requisito de
   divulgacao — os guards e os protocolos nao sao afetados.
4. Nenhum segredo real e versionado: `scripts/.env` e `infra/terraform/*.tfstate` estao no
   `.gitignore`, e `scripts/.env.example` contem apenas placeholders.

## Consequencias

Positivas:

- o adotante sabe o risco antes de copiar a implementacao de referencia
- a contradicao vira item rastreavel em vez de critica externa

Trade-offs:

- o framework e divulgado com uma inconsistencia conhecida entre o que prega (Aegis) e o
  que a referencia Azure faz
- quem copiar `ingest.py`/`search.py` sem ler este ADR herda a pratica ruim

Fora de escopo nesta etapa:

- migrar `ingest.py`, `search.py` e o servidor MCP para `DefaultAzureCredential`
- adicionar as role assignments no Terraform

## Evidencia (Neural-Flow)

- Sprint de origem: `Sprint 1`
- Guard associado: parcial — `.gitignore` impede versionar segredo, mas nao existe guard
  que detecte uso de admin key no codigo; declarado **aspiracional** ate a migracao
- Artefatos: `scripts/.env.example`, `infra/terraform/main.tf`, `docs/protocols/aegis-security.md`
- Referencia externa: Microsoft Learn — "Connect Using Azure Roles" (Azure AI Search)
