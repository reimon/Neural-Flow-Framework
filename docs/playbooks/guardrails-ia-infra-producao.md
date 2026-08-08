# Playbook Reutilizavel - Guardrails para uso de IA em Infraestrutura de Producao

> Parte do Neural-Flow Framework. Validado em producao, incluindo um incidente real de
> recriacao de infraestrutura disparado por mudanca em sufixo aleatorio. A lista critica
> de recursos ao final e exemplo Azure — adapte ao seu provider.

## Objetivo

Este documento define um padrao operacional para usar IA em tarefas de infraestrutura sem expor ambiente produtivo a destruicoes acidentais, drift critico ou mudancas nao auditadas.

Ele foi desenhado para qualquer projeto que use Terraform, Pulumi, Bicep, CloudFormation ou scripts de automacao com efeito em producao.

## Principio central

IA acelera execucao. Sem guardrails, ela tambem acelera erro.

A regra de ouro e: IA pode propor e preparar, mas somente com controles obrigatorios ela pode aplicar.

## Quadro 1 - Modos de operacao permitidos

| Modo             | Permitido para IA                                    | Restricoes                           |
| ---------------- | ---------------------------------------------------- | ------------------------------------ |
| Read-only        | inventario, diagnostico, plan, diff, validacoes      | sem alteracao de recursos            |
| Prepare          | gerar PR, editar IaC, criar pipeline, scripts        | sem apply em producao                |
| Apply controlado | executar apply em nao-producao                       | exige aprovacao humana para producao |
| Producao         | apenas com plano aprovado + gate + janela + reviewer | proibido auto-apply sem aprovacao    |

## Quadro 2 - Mudancas que exigem bloqueio automatico

| Categoria               | Exemplos                                       | Acao obrigatoria                |
| ----------------------- | ---------------------------------------------- | ------------------------------- |
| Stateful data           | PostgreSQL, MySQL, Cosmos, Redis persistente   | bloquear delete/replace         |
| Identidade e segredo    | Key Vault, app registrations, role assignments | exigir revisao de seguranca     |
| Plataforma core         | App principal, API gateway, DNS, certificados  | exigir change window            |
| Observabilidade critica | Log workspace, App Insights principal          | exigir justificativa de negocio |

## Quadro 3 - Politicas de pipeline

| Controle                        | Minimo exigido | Nivel recomendado                        |
| ------------------------------- | -------------- | ---------------------------------------- |
| Plan separado de apply          | sim            | sim                                      |
| Aprovacao manual em producao    | sim            | required reviewers + 2 aprovadores       |
| Bloqueio de destroy/replace     | sim            | gate por JSON plan + allowlist           |
| Proibicao de target em producao | sim            | enforcement por lint de pipeline         |
| Lock de state remoto            | sim            | lock + backup de state                   |
| Trilha de auditoria             | sim            | retention longa + assinatura de artefato |

## Quadro 4 - Guardrails tecnicos por IaC

| Area         | Regra                                                 |
| ------------ | ----------------------------------------------------- |
| Naming       | nomes estaveis em producao para recursos stateful     |
| Lifecycle    | prevent_destroy em banco e componentes criticos       |
| State        | backend remoto com lock e segregacao por ambiente     |
| Stack design | separar stateful-core de app-runtime                  |
| Permissions  | principal de pipeline com menor privilegio necessario |
| Drift        | rotina periodica de plan read-only + reconciliacao    |

## Quadro 5 - Sinais de parada obrigatoria (STOP)

Se qualquer item abaixo ocorrer, parar deploy imediatamente:

1. Plan contem delete/replace em recurso stateful.
2. Mudanca envolve random suffix que impacta nome de recurso critico.
3. Pipeline usa target em producao sem excecao formal.
4. Falta aprovacao humana registrada.
5. Principal de pipeline sem privilegio completo para a mudanca planejada.
6. Janela de manutencao nao aprovada.

## Quadro 6 - Fluxo seguro de execucao com IA

1. IA gera mudanca em branch e abre PR.
2. CI executa fmt, validate, lint, plan.
3. Gate analisa JSON do plan e bloqueia risco critico.
4. Humanos revisam arquitetura, impacto e rollback.
5. Aprovacao formal da mudanca.
6. Apply em homologacao e smoke tests.
7. Apply em producao com observabilidade ativa.
8. Verificacao pos-deploy e encerramento com evidencias.

## Quadro 7 - Responsabilidades (RACI simplificado)

| Atividade           | IA  | Eng. Infra | Revisor Senior | Dono do sistema |
| ------------------- | --- | ---------- | -------------- | --------------- |
| Propor mudanca      | R   | A          | C              | C               |
| Avaliar risco       | C   | R          | A              | C               |
| Aprovar producao    | N   | C          | A              | A               |
| Executar apply prod | C   | R          | A              | C               |
| Aprovar rollback    | N   | R          | A              | A               |

Legenda: R = responsavel, A = aprovador, C = consultado, N = nao participa.

## Quadro 8 - Checklist obrigatorio antes de qualquer apply em producao

- [ ] Plan sem delete/replace de stateful
- [ ] prevent_destroy ativo para bancos
- [ ] rollback testado e documentado
- [ ] janela de mudanca aprovada
- [ ] observabilidade e alertas ativos
- [ ] backup/restore confirmado
- [ ] aprovacao humana registrada
- [ ] execucao por pipeline oficial (sem comando manual ad-hoc)

## Prompt padrao para usar com IA (copiar e adaptar)

Use este prompt em qualquer agente de codigo/infra para impor travas de seguranca:

```text
Voce e um agente de infraestrutura com tolerancia zero para destruicao acidental em producao.

Contexto:
- Ambiente alvo: <dev|hml|prod>
- Repositorio: <repo>
- Objetivo da mudanca: <objetivo>
- Recursos esperados para mudar: <lista explicita>

Regras obrigatorias:
1) Nao execute apply em producao sem aprovacao humana explicita.
2) Sempre rode plan e apresente impacto por recurso.
3) Bloqueie execucao se houver delete ou replace em recursos stateful (banco, redis persistente, key vault, openai, recurso critico de app).
4) Nao use -target em pipeline principal de producao.
5) Exija nomes estaveis para recursos stateful; rejeite mudancas baseadas em sufixo aleatorio para esses recursos.
6) Se detectar risco critico, pare e gere plano de remediacao em vez de aplicar.
7) Antes de qualquer comando destrutivo, solicite confirmacao textual com frase exata: "APROVO MUDANCA DESTRUTIVA".
8) Gere checklist de preflight: backup, restore, permissao RBAC, janela de mudanca, observabilidade.
9) Sempre produza comandos em modo seguro primeiro (read-only), depois modo apply somente apos validacoes.
10) Em caso de duvida, escolha a alternativa mais conservadora e nao destrutiva.

Formato de resposta:
- Secao 1: Diagnostico
- Secao 2: Impacto previsto por recurso
- Secao 3: Plano seguro em etapas
- Secao 4: Comandos read-only
- Secao 5: Condicoes para permitir apply
- Secao 6: Plano de rollback
```

## Implementacao recomendada no CI (modelo)

1. terraform plan -out=tfplan
2. terraform show -json tfplan > tfplan.json
3. script gate:
   - se encontrar delete/replace em recursos criticos, sair com codigo 1
4. somente se gate passar: liberar etapa de aprovacao manual
5. somente apos aprovacao: terraform apply tfplan

## Script de gate (exemplo de logica)

Pseudo-logica:

- Ler resource_changes do tfplan.json
- Para cada recurso:
  - Se tipo em lista critica e actions contem delete ou replace:
    - Imprimir erro
    - Encerrar com falha

Lista critica inicial:

- azurerm_postgresql_flexible_server
- azurerm_postgresql_flexible_server_database
- azurerm_cosmosdb_account
- azurerm_key_vault
- azurerm_cognitive_account
- azurerm_linux_web_app (principal)

## Politica organizacional minima para IA em infraestrutura

1. Toda mudanca de producao deve ter issue e aprovador.
2. Nao existe excecao para auto-apply destrutivo.
3. Prompt de guardrail deve ser versionado no repositorio.
4. Toda falha relevante gera postmortem e acao preventiva codificada.

## Anti-padroes que devem ser proibidos

- Rodar apply direto no terminal sem plan aprovado.
- Misturar mudanca de storage simples com stack completa stateful.
- Confiar em import dinamico de state sem validacao de IDs.
- Permitir que IA execute acoes irreversiveis sem checkpoint humano.

## Resultado esperado ao adotar este playbook

- Reducao drastica de incidentes de destruicao acidental.
- Mudancas com trilha clara de risco, aprovacao e rollback.
- Uso de IA com produtividade alta e risco controlado.
