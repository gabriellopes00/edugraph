# ADR-0009: Trunk-based com PRs curtas por spec

**Status:** aceita
**Data:** 2026-09-17
**Decidido por:** o grupo
**Frente:** [T]

## Contexto

Três pessoas commitando ao mesmo tempo, com poucas semanas e sem
experiência prévia de trabalho conjunto neste repositório. O briefing
(§4.5) pede o fluxo de branches que minimize conflito e o que precisa
estar em `main` desde o primeiro dia.

A arquitetura já reduz o conflito estrutural: cada pessoa toca
essencialmente `src/<frente>`, `tests/<frente>` e
`docs/specs/frente-X` (ADR-0003). O que sobra é conflito de integração —
branches longas que divergem e explodem no merge.

## Decisão

Trunk-based: `main` protegida, integrada por PRs pequenas, uma por spec,
com CI verde. Nomes de branch `a/A-04-projecao-manual`,
`b/B-02-girvan-newman`, `c/C-04-api`. Rebase antes de abrir, squash
merge.

**Revisão por área tocada:**

- PR que toca só a própria pasta em `src/`, `tests/` e `docs/specs/`:
  mescla com CI verde; revisão opcional.
- PR que toca `contracts/`, `tests/contract/`, `data/fixtures/`,
  `__main__.py`, `pyproject.toml` ou `requirements*.txt`: **aprovação dos
  outros dois**; se muda contrato, ADR junto.

Commits em português, com o id da spec no título:
`B-03: modularidade à mão e comparação com NetworkX`.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Git-flow (`develop`, `release`, `hotfix`) | Cerimônia desenhada para software com versões publicadas; aqui só atrasa a integração |
| Um branch de longa duração por frente | Exatamente o que produz o merge catastrófico da última semana; e esconde quebra de contrato até tarde demais |
| Commitar direto em `main` | Sem CI obrigatória, a fronteira entre frentes e a restrição de ML deixam de ser garantidas |

## Consequências

**Boas.** Integração contínua de verdade: a `main` sempre roda. PRs
pequenas são revisadas em minutos, o que torna a revisão obrigatória dos
arquivos compartilhados viável em vez de burocrática. E a regra "fixtures
nunca mudam, nova versão é nova pasta" elimina a classe inteira de
conflitos "a fixture mudou e meu teste quebrou".

**Ruins.** Exige disciplina de fatiar o trabalho, o que é desconfortável
no começo. Se uma spec estiver grande demais para um PR, a resposta é
quebrar a spec — as specs foram dimensionadas para uma sessão de trabalho
justamente por isso (briefing §12).

**O que muda no código.** Nada. Muda `docs/arquitetura/branches-e-merge.md`
e a configuração de proteção de `main` no GitHub.

## Impacto no artigo

Nenhum.
