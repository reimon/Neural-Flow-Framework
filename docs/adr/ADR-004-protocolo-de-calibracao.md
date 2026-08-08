# ADR-004 — Criacao do protocolo de Calibracao e Incerteza

## Status

Aceito (Sprint 1)

## Contexto

Os nove protocolos anteriores eram binarios: PASS/FAIL, verde/vermelho,
CLEAR/WARNING/BLOCK. Isso e correto para gates, mas deixa um ponto cego entre "provado" e
"bloqueado" — onde vive a maior parte do trabalho real, a inferencia razoavel. Sem
calibracao, uma conclusao ancorada em teste executado e uma ancorada em plausibilidade
saem com a mesma cara, e o revisor humano perde o unico sinal que permitiria priorizar a
revisao.

Auditoria dos protocolos contra oito comportamentos esperados de agente mostrou que
"mede confianca" nao tinha nenhuma cobertura (zero ocorrencia de confianca/incerteza no
repositorio) e "sabe quando perguntar de novo" tinha cobertura apenas pelo eixo risco
(irreversibilidade), nunca pelo eixo incerteza.

## Decisao

Criar o 10o protocolo, com tres mecanismos:

1. **Confianca derivada da classe de evidencia**, nao de introspeccao: ALTA (execucao
   verificada), MEDIA (fonte documental vigente), BAIXA (inferencia). Cadeia com um elo
   inferido e conclusao inferida; repetir uma inferencia nao a promove.
2. **Escada de verificacao proporcional**: BAIXA obriga um degrau a mais de prova antes de
   responder — buscar fonte e, se for executavel, executar.
3. **Gatilho de reconsulta**: indice fraco exige reformular antes de escalar para
   varredura; BAIXA + irreversivel exige parar e perguntar; BAIXA + reversivel segue
   conservador com divergencia registrada.

## Consequencias

Positivas:

- o revisor humano passa a saber onde olhar primeiro
- fecha os dois unicos comportamentos de agente sem cobertura

Trade-offs:

- adiciona um campo obrigatorio no diario e na divergencia (atrito por iteracao)
- a classificacao depende de honestidade do agente sobre a evidencia que usou; o guard
  verifica a declaracao, nao a veracidade dela

Fora de escopo nesta etapa:

- inferir automaticamente o nivel de confianca a partir das ferramentas efetivamente
  chamadas na sessao

## Evidencia (Neural-Flow)

- Sprint de origem: `Sprint 1`
- Guard associado: `python scripts/nf_gate.py calibration` (C1-C6), coberto por
  `tests/test_guards.py`
- Artefatos: `docs/protocols/calibration.md`, `scripts/validate_calibration.py`
