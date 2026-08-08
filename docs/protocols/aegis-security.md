# Aegis Protocol

## Missao

Proteger a parceria humano-IA contra vazamento de segredos, dados sensiveis e exposicao indevida de contexto.

## Regra inegociavel

Zero segredo em prompts, memoria e artefatos de acompanhamento.

## Classificacao minima de dados

- Publico: pode circular livremente
- Interno: uso restrito ao repositorio
- Sensivel: exige mascaramento
- Segredo: proibido em prompt e documentacao operacional

## Criterio PASS

- nao ha segredos em prompts ou arquivos de controle
- dados sensiveis estao mascarados
- excecoes de seguranca estao registradas

## Criterio FAIL

- segredo exposto em texto claro
- dados sensiveis sem mascaramento
- ausencia de nota de seguranca em sprint sensivel

## Acao automatica em FAIL

- parar execucao imediatamente
- remover/rotacionar segredo comprometido
- registrar incidente e plano de contencao

## Checklist rapido de seguranca

- O conteudo contem token, chave, senha ou secret?
- Existe dado pessoal identificavel sem necessidade operacional?
- A sprint sensivel possui secao de seguranca atualizada?

Se qualquer resposta for `sim`, tratar como risco ativo e aplicar contencao.
