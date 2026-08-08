# Divergencias

## E3 — indice da tabela de slots

- **Data:** 2026-08-06
- **Spec consultada:** `docs/modulos/agendamento/spec.md`, secao Dominio de dados
- **Consultas ao indice tentadas:** "indice slots", "performance consulta agenda", "chave de busca disponibilidade"
- **O que falta / o que conflita:** a spec define os campos, mas nao diz por qual chave a disponibilidade e consultada
- **Confianca:** BAIXA — inferido do padrao de consulta descrito no criterio de aceite
- **Decisao tomada para seguir:** indice composto `(profissional_id, inicio)`, o mais conservador para o caso descrito
- **Reversivel?** sim
- **Impacto se a decisao estiver errada:** recriar o indice; sem perda de dado
- **Status:** pendente de revisao humana
