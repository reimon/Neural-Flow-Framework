# CLAUDE.md — instrucoes para agentes de codigo neste projeto

> TEMPLATE Neural-Flow. Copie para a raiz do projeto como `CLAUDE.md`.
> Lido automaticamente pelo Claude Code; sirva-se dele tambem em Cursor, Cline e afins.

> **Diretrizes arquiteturais (tool-agnosticas): `AGENTS.md`** — fonte de verdade unica
> para qualquer LLM. **Regras de seguranca: `.github/AI_SAFETY.md`** — proibicoes
> absolutas e acoes que exigem confirmacao. **Historico e decisoes: `MEMORY.md`** e
> `docs/adr/`. Leia-os junto com este arquivo.

---

## 1. Principios de execucao (Karpathy)

Fonte: <https://github.com/multica-ai/andrej-karpathy-skills> — `CLAUDE.md`.
Aplique os quatro antes de escrever qualquer codigo.

### Think Before Coding

Explicite suposicoes em vez de decidir em silencio. Quando o pedido admite mais de uma
leitura, apresente as interpretacoes e pergunte **antes** de implementar. Confusao
declarada custa uma pergunta; confusao silenciosa custa uma reescrita.

### Simplicity First

Escreva o codigo minimo que resolve o problema **declarado**. Nada de feature
especulativa, abstracao antecipada, flexibilidade nao pedida ou tratamento de erro para
cenario impossivel. Se escreveu 200 linhas e daria 50, reescreva.

### Surgical Changes

Toque so no que a tarefa pede. Nao refatore secao vizinha nem "melhore" codigo adjacente
sem pedido. Siga o estilo existente. Remova apenas os imports e funcoes que **as suas
mudancas** tornaram orfaos — nunca codigo morto preexistente.

### Goal-Driven Execution

Converta a tarefa em criterio verificavel **antes** de implementar. "Corrigir o bug" vira
"escrever um teste que reproduz o bug e depois faze-lo passar". Tarefa de varios passos
comeca com um plano curto e checkpoints de verificacao.

> Estes principios priorizam cautela sobre velocidade. Use julgamento em tarefa trivial.
> Sucesso se mede por: menos linhas alteradas sem necessidade, menos reescrita por
> excesso de engenharia, e perguntas feitas **antes** — nao depois.

---

## 2. Como isso conversa com o Neural-Flow

Os quatro principios acima sao a disciplina do agente; os protocolos do Neural-Flow sao a
trava. Eles se encaixam assim:

| Principio Karpathy | Protocolo que o torna verificavel |
| --- | --- |
| Think Before Coding | **Spec-First** — a spec e entrada, nao saida; duvida vira divergencia registrada, nunca preenchimento plausivel |
| Simplicity First | **Vetor de Contexto** — nao reimplementar o que o mapa de capacidades ja lista em `AGENTS.md` |
| Surgical Changes | **Loop Autonomo** — um item por iteracao; nao refatorar o que ja esta verde; commit escopado, nunca `git add -A` |
| Goal-Driven Execution | **Evidencia Sintetica** — verde no comando de verificacao e a unica condicao para marcar pronto |

E a **Calibracao** atravessa os quatro: toda conclusao declara `Confianca: ALTA | MEDIA |
BAIXA` com a classe de evidencia que a sustenta. `ALTA` exige execucao verificada; `MEDIA`
exige fonte documental vigente; `BAIXA` e inferencia e **nunca fecha item**.

## 3. Antes de commitar

```bash
python3 scripts/nf_gate.py          # todos os guards
python3 scripts/nf_gate.py --list   # o que cada um trava
```

O hook de pre-commit ja roda isso sobre o que esta em stage. **Nunca use `--no-verify`**:
se o gate reclamou, ou o artefato esta errado, ou o `git add` levou o que nao devia.

## 4. Antes de responder

- Pergunta sobre o projeto comeca no **indice**, nunca no `grep`. Varredura para
  "entender" custa ~48x mais tokens que a consulta ao indice.
- Comportamento se prova **executando**, nao lendo. Se e barato executar, nao opine.
- Indice devolveu resultado fraco? **Reformule** antes de escalar para leitura bruta.
- Confianca `BAIXA` + acao irreversivel (perder dado, expor dado pessoal, gastar dinheiro,
  mexer em producao) ⇒ **pare e pergunte**. Reversivel ⇒ siga conservador e registre.

## 5. Git

- **Nunca commitar ou dar push sem autorizacao explicita.**
- Stage com caminhos explicitos. Nunca `git add -A` nem `git add .`.
- Mensagem de commit no padrao `Sprint N - <descricao>`.
