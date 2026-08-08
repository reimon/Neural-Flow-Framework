# Project Memory: <Nome do Projeto>

> TEMPLATE Neural-Flow. Copie para a raiz como `MEMORY.md`. Este arquivo documenta
> decisoes criticas, padroes estabelecidos, integracoes e estado atual. **O agente
> de IA deve consultar este arquivo antes de sugerir solucoes e atualiza-lo
> proativamente sempre que um padrao novo for definido ou um problema complexo for
> resolvido.**
>
> Quando o protocolo Neural-Memory (RAG) estiver ativo no projeto, este arquivo e
> fonte de ingestao do indice — mantenha entradas atomicas e datadas.

**Ultima validacao deste arquivo:** DD-MM-AAAA

## 0. Delivery Workflow (Sprints + Checklists)

- **Modelo obrigatorio de execucao:** todo desenvolvimento organizado por sprints numeradas.
- **Formato da sprint:** checklist de acoes executaveis (ver `templates/sprint-template.md`).
- **Regra de marcacao:** item so recebe `[x]` quando a acao foi **realmente executada**.
- **Padrao de commit:** toda mensagem comeca com `Sprint N - <descricao>`.
- **Historico continuo:** o checklist por sprint e a fonte de verdade do progresso.

## 1. Architecture and Tech Stack

- **Frontend:** `<stack>`
- **Backend:** `<stack>`
- **Database:** `<engine + estrategia de migrations + ultima migration aplicada em prod>`
- **Auth:** `<mecanismo>`
- **Infra:** `<IaC + recursos principais por nome>`
- **CI/CD:** `<pipeline; deploy exclusivamente via CI>`

## 2. Critical Decisions and Code Patterns

> Uma subsecao por dominio (Auth, Banco, UI, Integracoes...). Cada entrada deve
> registrar o padrao E o porque — decisoes de arquitetura maiores viram ADR em
> `docs/adr/` e sao apenas referenciadas aqui.

### <Dominio>

- `<padrao estabelecido + motivo + arquivo de referencia>`

## 3. <Modulos/Features principais>

> Estado consolidado por modulo: o que existe, onde vive, o que esta em producao.

## 4. Solutions Log and Lessons Learned

> _AI Instruction: adicionar abaixo padroes descobertos e bugs complexos
> resolvidos, para nao repetir os mesmos erros. Formato obrigatorio:_

- **[AAAA-MM-DD] - <Titulo curto>:** `<o que aconteceu, causa raiz, padrao correto adotado>`

Regras deste log:

- Sempre datar (data absoluta, nunca relativa).
- Registrar a causa raiz e o padrao correto, nao so o sintoma.
- Se a licao implica regra permanente, promover para secao 2, `AGENTS.md`
  (com guard) ou ADR — e deixar aqui apenas o registro historico.
