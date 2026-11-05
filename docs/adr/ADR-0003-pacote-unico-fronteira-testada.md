# ADR-0003: Pacote único, um subpacote por frente, fronteira verificada por teste

**Status:** aceita
**Data:** 2026-09-17
**Decidido por:** o grupo
**Frente:** [T]

## Contexto

A ADR-0001 decidiu que as frentes se comunicam por disco. Falta decidir
como elas convivem no repositório e, principalmente, **como garantir que
a regra seja seguida**. O briefing (§4.3) pede que nenhuma frente importe
o módulo de outra; uma convenção escrita num README sobrevive até a
primeira semana de pressa.

## Decisão

Um pacote instalável (`src/edugraph`) com um subpacote por frente
(`data`, `community`, `centrality`, `api`), mais `contracts` e
`reporting`. **Exatamente dois arquivos** podem importar mais de uma
frente:

- `edugraph/__main__.py` — a raiz de composição;
- `edugraph/contracts/registry.py` — importa os estágios por nome.

`tests/contract/test_import_boundaries.py` analisa o código com `ast` e
falha se qualquer outro arquivo cruzar a fronteira. A lista de isenções
tem um teste próprio que quebra se ela crescer.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Três pacotes ou três repositórios | Overhead de versionamento e publicação para três pessoas com poucas semanas; a fronteira já é garantida pelo teste |
| Módulo compartilhado de `utils` | Vira o lugar onde a fronteira vaza: qualquer função útil migra para lá e as frentes voltam a se acoplar por dentro |
| Só convenção documentada | É o que se esperava do starter kit e não aconteceu; sem teste, a regra é uma boa intenção |

## Consequências

**Boas.** Um `pip install -e .` e está tudo disponível. Cada pessoa toca
essencialmente três pastas (`src/<frente>`, `tests/<frente>`,
`docs/specs/frente-X`), o que reduz conflito de merge a quase zero. E a
fronteira do briefing §4.3 vira um teste que roda na CI, não uma
convenção.

**Ruins.** O teste de fronteira é rígido de propósito: quando alguém
precisar legitimamente de algo de outra frente, o caminho é mover a peça
para `contracts` ou `reporting` — o que é mais trabalho do que importar,
e é justamente o ponto. Acrescentar um terceiro arquivo à lista de
isenções exige ADR.

**O que muda no código.** `pyproject.toml`; a estrutura inteira de
`src/edugraph`; `tests/contract/test_import_boundaries.py`.

## Impacto no artigo

Alimenta o parágrafo do capítulo 3 sobre organização do sistema: as
fronteiras não são só desenhadas no diagrama, são verificadas
automaticamente.
