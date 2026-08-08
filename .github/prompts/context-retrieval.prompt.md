---
description: "Recuperação semântica de contexto histórico antes de qualquer tarefa técnica significativa. Chama query_neural_memory com a intenção da tarefa e injeta os chunks mais relevantes no contexto antes da execução."
applyTo: "**"
---

# Neural-Prompt: Context Retrieval

## Objetivo

Antes de executar qualquer tarefa técnica relevante, este prompt instrui o agente a consultar o banco vetorial neural-memory para recuperar decisões históricas, regras operacionais e referências de sprint que sejam semanticamente relacionadas à intenção atual.

## Quando aplicar

- Antes de iniciar qualquer novo item de checklist de sprint
- Antes de propor mudanças em arquitetura, autenticação, infraestrutura ou segurança
- Antes de criar ou modificar arquivos de protocolo ou manifesto
- Antes de qualquer ação que o State Protocol classifique como A2 ou A3

## Instrução ao agente

1. **Extraia a intenção** da tarefa atual em uma frase concisa de 10-20 palavras.

2. **Chame `query_neural_memory`** com essa intenção:

   ```
   query_neural_memory(question="<intenção da tarefa>", top=5)
   ```

3. **Analise os resultados** retornados:
   - Se houver chunks com `[SEED]`: leia com atenção — são regras de política prioritárias.
   - Se houver chunks de `type=commit`: verifique se a proposta atual é consistente com mudanças anteriores similares.
   - Se houver chunks de `type=markdown` com `source_file` em `docs/protocols/`: aplique o protocolo referenciado.

4. **Chame `check_contradiction`** se a tarefa envolver:
   - mudança de arquitetura ou segurança
   - nova política ou exceção ao manifesto
   - reversão de decisão anteriormente registrada

5. **Registre o contexto recuperado** no início da sessão de sprint (memória de sessão), indicando:
   - fontes recuperadas (`source_file`)
   - decisões relevantes encontradas
   - se alguma contradição foi detectada pelo `check_contradiction`

## Saída esperada

O agente deve produzir um bloco de contexto estruturado antes de agir:

```
## Contexto Recuperado — [YYYY-MM-DD]

Intenção: "<intenção da tarefa>"

Fontes relevantes:
- [tipo] source_file — resumo do chunk (sprint_ref, data)
- ...

Contradições detectadas: CLEAR | WARNING | BLOCK
Ação tomada: prosseguir | aguardar revisão humana
```

## Regra de Gates

Se `check_contradiction` retornar `BLOCK`, o agente deve:

1. Interromper a execução
2. Registrar o bloqueio como pendência com `proxima_acao: revisao humana obrigatoria`
3. NÃO prosseguir com a tarefa sem aprovação explícita
