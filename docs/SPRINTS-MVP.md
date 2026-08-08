# Sprint MVP: Baseline e Descoberta do Projeto

## Snapshot Operacional

- App/Escopo: `<seu-projeto>`
- Status: `planejada`
- Data de inicio: `YYYY-MM-DD`
- Data planejada de conclusao: `YYYY-MM-DD`
- Data real de conclusao: `a preencher`
- Ultima atualizacao: `YYYY-MM-DD`
- Nivel de autonomia: `A0`
- Blocker principal: nenhum
- Proxima acao: adaptar este template ao seu contexto

## Controle de Protocolos Nucleares

- State Protocol: `PASS | FAIL | EXCEPTION`
- Circuit Breaker: `PASS | FAIL | EXCEPTION`
- Context Vector: `PASS | FAIL | EXCEPTION`
- Evidencia Sintetica: `PASS | FAIL | EXCEPTION`
- Aegis Protocol: `PASS | FAIL | EXCEPTION`
- Token budget da sprint: `a preencher`
- Consumo observado: `a preencher`

## Objetivo

Esta sprint inicial estabelece o baseline de governança do projeto, criando a estrutura mínima de sprints, memória institucional e planos de execução conforme o manifesto.

Resultado esperado: Projeto estruturado para começar a seguir a governança padrão, com manifesto como fonte de verdade, memoria versionada e primeira sprint concluída.

## Escopo incluido

- [ ] Estrutura de pastas (docs/, .github/prompts/, sprints/, docs/protocols/)
- [ ] Arquivo Manifest-Dev-AI.md copiado ou referenciado
- [ ] NEURAL-MEMORY.md criado e preenchido com snapshot inicial
- [ ] SPRINTS-CHECKLIST.md por app criado
- [ ] plan-setup-governanca.prompt.md adaptado ao projeto
- [ ] Primeiro commit de governança executado

## Fora do escopo

- Implementação técnica de features ou correções
- Configuração de CI/CD ou pipelines
- Infraestrutura ou provisionamento
- Integrações externas ou APIs

## Entregaveis

- [ ] E1. Diretorio `docs/` com Manifest-Dev-AI.md e NEURAL-MEMORY.md
- [ ] E2. Diretório `.github/prompts/` com plan-setup-governanca.prompt.md
- [ ] E3. Arquivo SPRINTS-CHECKLIST.md em cada app
- [ ] E4. Primeiro commit de governança em git

## Checklist de Acoes

### Bloco 1: Estrutura de Pastas

- [ ] 1.1 Criar diretório `docs/` na raiz do projeto
  - Arquivo(s): `docs/`
  - Validacao: `[ -d docs ] && echo "OK"`
  - Evidencia: screenshot ou `ls -la docs/`

- [ ] 1.2 Criar diretório `.github/prompts/`
  - Arquivo(s): `.github/prompts/`
  - Validacao: `[ -d .github/prompts ] && echo "OK"`
  - Evidencia: screenshot ou `ls -la .github/prompts/`

- [ ] 1.3 Criar diretórios `sprints/` em cada app
  - Arquivo(s): `apps/<app>/sprints/`
  - Validacao: `ls -la apps/*/sprints/`
  - Evidencia: listing de diretórios criados

- [ ] 1.4 Criar diretorio de protocolos nucleares
  - Arquivo(s): `docs/protocols/`
  - Validacao: `[ -d docs/protocols ] && echo "OK"`
  - Evidencia: `ls -la docs/protocols/`

### Bloco 2: Arquivos Canônicos

- [ ] 2.1 Copiar ou referenciar Manifest-Dev-AI.md
  - Arquivo(s): `docs/Manifest-Dev-AI.md`
  - Validacao: `[ -f docs/Manifest-Dev-AI.md ] && echo "OK"`
  - Evidencia: `wc -l docs/Manifest-Dev-AI.md`

- [ ] 2.2 Criar NEURAL-MEMORY.md inicial
  - Arquivo(s): `docs/NEURAL-MEMORY.md`
  - Validacao: `[ -f docs/NEURAL-MEMORY.md ] && echo "OK"`
  - Evidencia: `head -20 docs/NEURAL-MEMORY.md`

- [ ] 2.3 Adaptar os prompts de governanca
  - Arquivo(s): `.github/prompts/sprint-intent.prompt.md`, `.github/prompts/context-retrieval.prompt.md`
  - Validacao: `ls .github/prompts/*.prompt.md`
  - Evidencia: `wc -l .github/prompts/sprint-intent.prompt.md`

### Bloco 3: Índices de Portfolio

- [ ] 3.1 Criar SPRINTS-CHECKLIST.md para cada app
  - Arquivo(s): `apps/<app>/SPRINTS-CHECKLIST.md`
  - Validacao: `ls apps/*/SPRINTS-CHECKLIST.md`
  - Evidencia: listing dos arquivos criados

### Bloco 4: Ativacao dos 5 Protocolos

- [ ] 4.1 Validar State Protocol antes da primeira execucao tecnica
  - Arquivo(s): `docs/protocols/state-protocol.md`
  - Validacao: snapshot preenchido e status de sprint definido
  - Evidencia: secao "Controle de Protocolos Nucleares" preenchida

- [ ] 4.2 Definir budget para Circuit Breaker de Tokens
  - Arquivo(s): `docs/protocols/token-circuit-breaker.md`
  - Validacao: budget e limite de alerta registrados
  - Evidencia: campos "Token budget" e "Consumo observado"

- [ ] 4.3 Confirmar Vetor de Contexto para leitura de baseline
  - Arquivo(s): `docs/protocols/context-vector.md`
  - Validacao: manifesto e MEMORY consultados no inicio
  - Evidencia: delta de sessao com fontes usadas

- [ ] 4.4 Exigir Evidencia Sintetica no fechamento
  - Arquivo(s): `docs/protocols/synthetic-evidence.md`
  - Validacao: cada item concluido com prova minima
  - Evidencia: tabela acao x evidencia no resumo final

- [ ] 4.5 Aplicar Aegis Protocol em prompts e memoria
  - Arquivo(s): `docs/protocols/aegis-security.md`
  - Validacao: ausencia de segredos e dados sensiveis nao mascarados
  - Evidencia: notas de seguranca atualizadas

## Dependencias Tecnologicas

- Git (para versionamento)
- Editor de markdown (para documentação)
- Acesso ao repositório do projeto
- Nenhuma dependência de biblioteca ou framework

## Notas de Seguranca

Não se aplica.

## Delta desde a ultima atualizacao

`YYYY-MM-DD` - Sprint criada com estrutura inicial e checklist padrão.

## Riscos / Blockers / ETA

- Risco baixo: Esta é uma sprint de estruturação, sem código técnico.
- Dependência: Acesso e permissão de escrita no repositório Git.
- ETA: 30 a 45 minutos para agente IA, 1-2 horas para execução manual.

## Evidencias de Implementacao

- [ ] Diretorio `docs/` criado com arquivos
- [ ] Diretorio `.github/prompts/` criado com plan
- [ ] SPRINTS-CHECKLIST.md criado em cada app
- [ ] NEURAL-MEMORY.md preenchido com snapshot inicial
- [ ] Protocolos nucleares criados em `docs/protocols/`
- [ ] Budget de tokens definido e monitorado
- [ ] Git status limpo e pronto para commit

## Commits Executados

- `<hash-curto>` - `docs(governança): inicia setup de manifesto` - estrutura inicial

## Resumo das Atividades

| Acao | O que foi feito                         | Arquivos alterados                                |
| ---- | --------------------------------------- | ------------------------------------------------- |
| 1.1  | Criou diretório docs/                   | `docs/`                                           |
| 1.2  | Criou diretório .github/prompts/        | `.github/prompts/`                                |
| 1.3  | Criou sprints/ em cada app              | `apps/*/sprints/`                                 |
| 1.4  | Criou diretorio de protocolos nucleares | `docs/protocols/`                                 |
| 2.1  | Copiou Manifest-Dev-AI.md               | `docs/Manifest-Dev-AI.md`                         |
| 2.2  | Criou NEURAL-MEMORY.md                  | `docs/NEURAL-MEMORY.md`                           |
| 2.3  | Adaptou plan-setup-governanca.prompt.md | `.github/prompts/plan-setup-governanca.prompt.md` |
| 3.1  | Criou SPRINTS-CHECKLIST.md em cada app  | `apps/*/SPRINTS-CHECKLIST.md`                     |
| 4.1  | Validou State Protocol                  | `docs/protocols/state-protocol.md`                |
| 4.2  | Configurou Circuit Breaker              | `docs/protocols/token-circuit-breaker.md`         |
| 4.3  | Aplicou Context Vector                  | `docs/protocols/context-vector.md`                |
| 4.4  | Aplicou Evidencia Sintetica             | `docs/protocols/synthetic-evidence.md`            |
| 4.5  | Aplicou Aegis Protocol                  | `docs/protocols/aegis-security.md`                |

## Pendencias para a Proxima Sprint

- Popular NEURAL-MEMORY.md com estado real do projeto (apps, services, status) e executar primeiro reindex
- Criar primeira sprint detalhada de feature/mudança técnica
- Ajustar caminhos e referências nos templates para contexto específico

## Regras

- Seguir `docs/Manifest-Dev-AI.md` para todas as sprints futuras
