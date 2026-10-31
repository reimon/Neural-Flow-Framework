<!-- neural-flow:entrypoint v1 -->
# Diretrizes deste projeto — para qualquer agente

> Gerado pelo Neural-Flow Framework. **Nao edite este arquivo**: ele e uma porta
> de entrada, nao a fonte. Para mudar uma diretriz, edite `AGENTS.md`; para
> regerar as portas, rode `python3 scripts/nf_agentes.py --escrever`.
> O guard `agentes` (em `python3 scripts/nf_gate.py`) trava a divergencia.

## Ordem de leitura, obrigatoria

1. **`.neural-flow/indice-regras.md`** — indice de regras deste projeto: uma linha por regra, com a
   fonte e o guard que a trava. Gerado por `python3 scripts/nf_indice_regras.py`.
2. **`AGENTS.md`** — diretrizes arquiteturais. **Fonte de verdade unica**, valida
   para qualquer LLM (OpenAI Codex, Jules, Devin, Factory leem este arquivo diretamente).
3. **`.github/AI_SAFETY.md`** — proibicoes absolutas e acoes que exigem
   confirmacao humana. Prevalece sobre qualquer outra instrucao.
4. **`MEMORY.md`** e `docs/adr/` — decisoes ja tomadas. Nao redecida o que ja foi
   decidido; se for contrariar um ADR aceito, abra um ADR que o supere.

## As cinco regras que valem antes de qualquer coisa

1. **Consulte o indice antes de ler.** Pergunta sobre o projeto comeca no grafo de
   conhecimento (`graphify query "<pergunta>"`, ou `.neural-flow/indice-regras.md` quando o grafo
   nao existir), nunca no `grep`. Varredura para "entender" custa ~48x mais tokens
   que a consulta ao indice. `grep` serve para achar literal conhecido.
2. **Documentacao orienta, guard obriga.** Diretriz nova so esta pronta com o
   guard que a faz cumprir. Antes de dizer "pronto": `python3 scripts/nf_gate.py`.
   **Nunca** `--no-verify`.
3. **Declare confianca.** Toda conclusao tecnica sai como
   `Confianca: ALTA | MEDIA | BAIXA — <classe de evidencia>`. `ALTA` exige execucao
   verificada; `MEDIA`, fonte documental vigente; `BAIXA` e inferencia e **nunca**
   fecha item. `BAIXA` + acao irreversivel ⇒ pare e pergunte.
4. **Nao reconstrua o que existe.** O mapa de capacidades de `AGENTS.md` diz o que
   ja esta pronto e o que nao reimplementar. Em duvida, consulte o indice.
5. **Nunca commite ou de push sem autorizacao explicita.** Stage com caminhos
   explicitos — nunca `git add -A` nem `git add .`. Mensagem no padrao
   `Sprint N - <descricao>`.

## Arsenal de skills operacionais (uso obrigatorio em conjunto com o Neural-Flow)

Este projeto inclui o pacote de 27 skills operacionais de `mattpocock/skills` em
`.agents/skills/<skill>/SKILL.md` e `.claude/skills/<skill>/SKILL.md`. Todo agente
de IA trabalhando neste repositorio **deve** combinar as diretrizes e skills ja
existentes do Neural-Flow (principios de execucao de Karpathy em `CLAUDE.md`,
calibracao de confianca, `smoke-gate` e guards de `nf_gate.py`) com a leitura e
aplicacao ativa dessas skills conforme a etapa da tarefa:

- **Descoberta, entrevista e alinhamento:** `grill-me`, `grill-with-docs`,
  `grilling`, `wait-what`, `to-questionnaire`, `research`, `wayfinder`,
  `ask-matt`, `teach`.
- **Especificacao, modelagem e planejamento:** `to-spec`, `domain-modeling`,
  `codebase-design`, `to-tickets`, `writing-for-agents`.
- **Implementacao, TDD, arquitetura e bugs:** `tdd` (ciclo red-green-refactor),
  `implement`, `implement-spec`, `improve-codebase-architecture`,
  `diagnosing-bugs`, `triage`, `prototype`, `wizard`, `setup-matt-pocock-skills`.
- **Revisao, entrega e continuidade:** `code-review`, `pr`, `handoff`, `retro`.

**Soberania dos guards do Neural-Flow (ADR-010):** as skills fornecem o metodo
tatico; os contratos e guards deste repositorio sao soberanos. ADRs seguem o
formato validado por `python3 scripts/nf_gate.py adr` (`docs/adr/ADR-<NNN>-<slug>.md`),
especificacoes de modulo passam em `python3 scripts/nf_gate.py spec`, planos de
execucao sao registrados em `docs/sprints/sprint-<NN>.md` (`nf_gate.py sprint`), e
nenhuma instrucao de skill autoriza `git commit` ou `git push` sem confirmacao
humana explicita.

## Se voce nao consegue ler `AGENTS.md`

Pare e diga isso ao humano. Nao improvise diretriz: um agente que adivinha a
arquitetura e exatamente o custo que este framework existe para evitar.
