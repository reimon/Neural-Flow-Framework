# Sprint 4: Fechar a divida de autenticacao e proteger o state

## Snapshot Operacional

- App/Escopo: `neural-flow-framework — verificacao da via keyless, prevent_destroy e backend remoto`
- Status: `em andamento`
- Data de inicio: `2026-08-15`
- Data planejada de conclusao: `2026-08-29`
- Data real de conclusao: `a definir`
- Ultima atualizacao: `2026-08-15`
- Nivel de autonomia: `A1`
- Blocker principal: `sem credencial Entra ID nesta maquina — 1.2, 2.1 e 2.2 dependem de execucao humana`
- Proxima acao: `rodar python3 scripts/nf_azure_smoke.py num ambiente autenticado`

> A1 e obrigatoria e aqui nao e formalidade: o escopo toca autenticacao, segredo e um
> Terraform que gerencia 10 recursos reais com state local, sem copia. O guard S4 reprova
> A2/A3 neste escopo.

## FinOps de Tokens

- Token budget: `1M`
- Limite de alerta: `70%`
- Consumo observado: `em andamento`
- Mitigacao aplicada: `nao se aplica`

> **De onde vem o 1M.** A Sprint 3 consumiu **674.006 faturaveis** em 70 requisicoes
> (`python3 scripts/nf_tokens.py --sprint 3`), com escopo maior que o desta: dois scripts
> novos, migracao de tres consumidores, ADR e testes. Esta sprint e majoritariamente
> Terraform e execucao humana, entao 1M ja tem folga. `Confianca: ALTA` para a base
> medida; `MEDIA` para o dimensionamento, que e julgamento sobre escopo.
>
> Terceira sprint seguida medindo antes de dimensionar. O default de 500k do instalador
> nunca mais foi usado sem ajuste — era essa a mitigacao acordada na Sprint 2.

## Objetivo

Transformar a migracao keyless da Sprint 3, que existe apenas como codigo, em fato
verificado — e tirar o Terraform da situacao em que um comando errado orfana 10 recursos
sem possibilidade de restauracao.

## Escopo incluido

- Ferramenta de verificacao da via keyless, sem escrita e sem custo relevante
- `prevent_destroy` nos recursos que nao podem ser recriados sem perda
- Caminho documentado para o backend remoto com lock, sem migrar nesta sprint
- Fechar o item 2.1 da Sprint 3 e superar o ADR-003, **depois** da verificacao

## Fora do escopo

- Migrar o state para o backend remoto — e operacao com o humano presente, nao de agente
- Qualquer `terraform apply` ou `destroy`
- Desabilitar `local_authentication` no Search antes de a via keyless estar provada
- Traducao do framework para ingles

## Checklist de Acoes

### Bloco 1: Verificacao da via keyless

- [x] 1.1 Ferramenta que responde "a via keyless funciona aqui?" em um comando
  - Arquivo(s): `scripts/nf_azure_smoke.py`
  - Validacao: `python3 scripts/nf_azure_smoke.py --sem-openai` num ambiente sem
    credencial devolve diagnostico acionavel, nao stack trace
  - Evidencia: verificado sem credencial — o script identifica variavel ausente e SDK
    ausente com instrucao de conserto. Nao escreve nada; a unica chamada com custo e um
    embedding de ~1 token, evitavel com `--sem-openai`. Nenhum segredo e impresso

- [ ] 1.2 Rodar a verificacao num ambiente autenticado
  - Arquivo(s): evidencia em `docs/sprints/sprint-04-fechar-a-divida-de-auth.md`
  - Validacao: `python3 scripts/nf_azure_smoke.py` sai 0
  - Evidencia: **bloqueado — exige credencial Entra ID que esta maquina nao tem.**
    E execucao humana, com `az login`. Nao ha como um agente sem tenant fechar isto

### Bloco 2: Fechar a divida (depende de 1.2)

- [ ] 2.1 Marcar o item 2.1 da Sprint 3 como concluido, com a saida como evidencia
  - Arquivo(s): `docs/sprints/sprint-03-divida-de-auth-e-telemetria.md`
  - Validacao: revisao humana
  - Evidencia: bloqueado por 1.2

- [ ] 2.2 ADR que supera o ADR-003
  - Arquivo(s): `docs/adr/`
  - Validacao: `python3 scripts/nf_gate.py adr`
  - Evidencia: bloqueado por 1.2. Superar um ADR de divida sem execucao verificada e a
    falha que o protocolo de Calibracao proibe — nao e formalidade de processo

- [ ] 2.3 Desabilitar `local_authentication` no Search e remover a admin key do Key Vault
  - Arquivo(s): `infra/terraform/main.tf`
  - Validacao: `terraform plan` sem destroy de recurso stateful
  - Evidencia: bloqueado por 1.2. Fazer antes de a via keyless estar provada deixa o
    projeto sem nenhuma via de acesso

### Bloco 3: Proteger o state

- [x] 3.1 `prevent_destroy` nos recursos que nao podem ser recriados
  - Arquivo(s): `infra/terraform/main.tf`
  - Validacao: `terraform validate`
  - Evidencia: cinco recursos protegidos — `random_string.suffix` (gerador de nome, cuja
    recriacao derruba a infra inteira e ja e a proibicao numero 2 do `AI_SAFETY`), o
    resource group, o Search (recriar apaga o indice inteiro), o OpenAI (muda endpoint e
    subdominio) e o Key Vault (`purge_protection` desligado, soft delete de 7 dias).
    `Success! The configuration is valid`. Transforma regra escrita em erro de plan

- [x] 3.2 Caminho documentado para o backend remoto com lock
  - Arquivo(s): `infra/terraform/backend.tf.exemplo`
  - Validacao: extensao `.exemplo` — o Terraform ignora, nada muda por engano
  - Evidencia: runbook em quatro passos, na ordem que importa: provisionar o storage
    **fora** deste state (ele nao pode se gerenciar), ativar versionamento no blob, copiar
    o `tfstate` para fora do repositorio, so entao `init -migrate-state` e conferir que o
    plan sai "No changes". Plan com destroy = migracao errada, PARE

- [ ] 3.3 Migrar o state para o backend remoto
  - Arquivo(s): `backend.tf`, ativado a partir do modelo `.exemplo`
  - Validacao: `terraform plan` sai "No changes" apos a migracao
  - Evidencia: **deliberadamente nao feito por agente.** State local, 10 recursos reais,
    zero copia: migracao errada orfana tudo. E operacao com o humano presente

## Riscos / Blockers / ETA

- Risco: a verificacao keyless falhar por role ainda nao propagada e alguem "resolver" com
  `NF_AZURE_AUTH=key`. Impacto: a divida do ADR-003 volta por baixo do pano. Mitigacao: o
  proprio script diz isso na mensagem de falha, e o modo `key` avisa em toda execucao.
- Risco: `prevent_destroy` bloquear um plan legitimo no futuro. Impacto: friccao. Aceito:
  remover o bloco e uma linha e um commit revisado — recriar o Key Vault, nao.
- Risco: o state local se perder antes da migracao. Impacto: 10 recursos orfaos. Mitigacao
  parcial: o passo 2 do runbook e copiar o state para fora. Enquanto 3.3 nao rodar, o
  risco continua aberto e conhecido.

## Evidencias de Implementacao

- `terraform validate` — configuration is valid, com os cinco `prevent_destroy`
- `terraform fmt` — limpo nos arquivos alterados
- `python3 scripts/nf_azure_smoke.py --sem-openai` — diagnostico acionavel sem credencial
- `python3 -m unittest discover -s tests` — 80 testes, verde
- `python3 scripts/nf_gate.py` — 7 guards conforme

## Pendencias para a Proxima Sprint

- Nada nesta sprint fecha sem 1.2; se a credencial nao aparecer, o bloco 2 inteiro
  escorrega - sprint alvo: 5
- Aceitar ou rejeitar o ADR-005 (decisao humana) - sprint alvo: 4

## Regras

- Validar antes de commitar: `python3 scripts/nf_gate.py`
- Item so recebe `[x]` quando a acao foi realmente executada.
