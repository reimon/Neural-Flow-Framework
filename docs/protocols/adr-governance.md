# Protocolo ADR (Architecture Decision Records)

## Missao

Registrar toda decisao arquitetural relevante como documento numerado, imutavel e
auditavel, para que agentes e humanos decidam ancorados em historico explicito em
vez de reconstruir (ou contradizer) decisoes passadas.

## Regra inegociavel

Nenhuma decisao arquitetural relevante existe apenas em conversa, commit message ou
memoria de sessao. Se muda estrutura, padrao, dependencia critica ou trade-off de
longo prazo, vira ADR em `docs/adr/`.

## O que exige ADR

- Adocao/remocao de padrao estrutural (camadas, repository, DI, tenancy)
- Escolha de dependencia ou servico com efeito de longo prazo (banco, provider LLM, IaC)
- Decisao que aceita trade-off consciente ("SQL raw em vez de ORM por ora")
- Reversao/superacao de decisao anterior (novo ADR com `Superado por`, nunca edicao)

O que NAO exige ADR: correcao de bug, padrao local de um arquivo, licao operacional
(vai para `MEMORY.md` secao Solutions Log).

## Regras de ciclo de vida

1. Numeracao sequencial `ADR-NNN`; numero nunca e reutilizado.
2. ADR aceito e **imutavel** — mudanca de rumo gera novo ADR que o supera.
3. Status permitidos: Proposto, Aceito (Sprint N), Superado por ADR-MMM, Rejeitado.
4. Todo ADR referencia a sprint de origem (rastreabilidade Neural-Flow).
5. Se o ADR estabelece regra impositiva, deve nascer com guard (lint/teste/CI) ou
   declarar explicitamente que o guard e aspiracional — principio "documentacao
   orienta, guard obriga" (`templates/AGENTS-template.md`).

## Template

`templates/adr-template.md`

## Integracao com os demais protocolos

- **Vetor de Contexto:** ADRs sao fonte prioritaria de contexto para decisao.
- **Neural-Memory:** `docs/adr/*.md` entra nas fontes indexadas; `check_contradiction`
  deve retornar WARNING/BLOCK para proposta que contradiz ADR aceito.
- **Evidencia Sintetica:** ADR aceito e evidencia valida de decisao em sprint.

## Guard executavel

Este protocolo trava, nao sugere. Principio n. 0 do framework: **diretriz sem guard
nao esta pronta**.

```bash
python scripts/nf_gate.py adr          # so este protocolo
python scripts/nf_gate.py                  # todos os guards
```

Verifica: A1 numeracao unica · A2 status valido · A3 sem referencia pendurada · A4 sem ciclo de supersecao · A5 sprint de origem · A6 guard declarado.

Roda no **pre-commit** (sobre o que esta em stage, nao sobre a arvore de trabalho) e no
**CI** (autoritativo — hook local e opt-in por clone). Instalacao em
`templates/githooks/pre-commit` e `.github/workflows/neural-flow-gates.yml`.

## Criterio PASS

- Toda decisao arquitetural do periodo possui ADR com status e sprint de origem
- Nenhum ADR aceito foi editado apos aceite (mudancas via superacao)
- ADRs impositivos possuem guard ou declaracao de guard aspiracional

## Criterio FAIL

- Decisao estrutural executada sem ADR
- ADR aceito editado em vez de superado
- Proposta contradizendo ADR aceito executada sem novo ADR de superacao
