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

## Se voce nao consegue ler `AGENTS.md`

Pare e diga isso ao humano. Nao improvise diretriz: um agente que adivinha a
arquitetura e exatamente o custo que este framework existe para evitar.
