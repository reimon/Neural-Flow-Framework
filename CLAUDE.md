# CLAUDE.md — instrucoes para agentes de codigo neste projeto

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

| Principio Karpathy | Protocolo que o torna verificavel | Skills operacionais (`mattpocock/skills`) |
| --- | --- | --- |
| Think Before Coding | **Spec-First** — a spec e entrada, nao saida; duvida vira divergencia registrada, nunca preenchimento plausivel | `grill-me`, `grill-with-docs`, `grilling`, `wait-what`, `to-questionnaire`, `to-spec` |
| Simplicity First | **Vetor de Contexto** — nao reimplementar o que o mapa de capacidades ja lista em `AGENTS.md` | `domain-modeling`, `codebase-design`, `improve-codebase-architecture`, `research`, `wayfinder` |
| Surgical Changes | **Loop Autonomo** — um item por iteracao; nao refatorar o que ja esta verde; commit escopado, nunca `git add -A` | `to-tickets`, `implement`, `implement-spec`, `diagnosing-bugs`, `triage`, `writing-for-agents` |
| Goal-Driven Execution | **Evidencia Sintetica** — verde no comando de verificacao e a unica condicao para marcar pronto | `tdd` (red-green-refactor), `code-review`, `pr`, `handoff`, `retro` |

E a **Calibracao** atravessa os quatro: toda conclusao declara `Confianca: ALTA | MEDIA |
BAIXA` com a classe de evidencia que a sustenta. `ALTA` exige execucao verificada; `MEDIA`
exige fonte documental vigente; `BAIXA` e inferencia e **nunca fecha item**.

## 2.1 Arsenal de skills operacionais (`mattpocock/skills` — uso obrigatorio)

Fonte: <https://github.com/mattpocock/skills> — instalado em `.agents/skills/<skill>/SKILL.md`
e `.claude/skills/<skill>/SKILL.md`.

Todo agente trabalhando neste projeto **deve** usar essas skills sempre em conjunto com as
diretrizes do Neural-Flow e com os quatro principios acima:

1. **Descoberta e entrevista:** antes de assumir requisitos ambiguos, use `grill-me`,
   `grill-with-docs`, `grilling`, `wait-what` ou `to-questionnaire`; para mapear o
   repositorio apos compactacao, use `wayfinder` e `research`.
2. **Especificacao, arquitetura e planejamento:** use `to-spec` para especificacoes,
   `domain-modeling` e `codebase-design` para desenhar *deep modules*, e `to-tickets` para
   fatiar entregas verticais.
3. **Implementacao, TDD e bugs:** use `tdd` (teste falhando → codigo minimo → refatoracao),
   `implement` / `implement-spec`, `improve-codebase-architecture`, `diagnosing-bugs` e `triage`.
4. **Revisao e passagem de bastao:** use `code-review`, `pr`, `handoff` e `retro`.
5. **Soberania do Neural-Flow:** os contratos e guards (`python3 scripts/nf_gate.py`) sao
   soberanos sobre qualquer template de skill (ADRs em `docs/adr/ADR-<NNN>-<slug>.md`,
   specs em `docs/modulos/<modulo>.md`, sprints em `docs/sprints/sprint-<NN>.md`, e
   proibicao de `git commit` / `git push` sem autorizacao humana explicita).

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
