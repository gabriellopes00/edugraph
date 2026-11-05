# ADR-0005: Front-end em React + Vite com Cytoscape.js

**Status:** aceita
**Data:** 2026-09-17
**Decidido por:** o grupo — **decisão D3 do plano de arquitetura**
**Frente:** [C]

## Contexto

O briefing (§7) deixa o front-end "a definir no plano", com preferência
por algo que renderize grafo interativo, e cita o Cytoscape.js como
candidato. A saída obrigatória da seção 6.2 é um relatório de uso
**interno**: não há público externo, não há requisito de SEO nem de
carga.

O plano de arquitetura recomendou uma página estática única, sem etapa de
build, pela economia de toolchain. **O grupo decidiu diferente:** React +
Vite, porque a defesa é uma apresentação, e animações e transições
controladas melhoram a legibilidade do que está sendo mostrado na banca.

## Decisão

Front-end em `frontend/`, com React 18, Vite 5, TypeScript, Cytoscape.js
(layout fcose) e `framer-motion` para as transições. Compilado para
`src/edugraph/api/static/` e servido pelo próprio FastAPI em `/`.

`src/edugraph/api/static/` fica **fora do git**: é artefato de build, não
fonte.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Página estática única com Cytoscape.js (recomendação original do plano) | Sem toolchain e sem build, mas as transições e o estado da interface ficariam em JavaScript imperativo à mão; o grupo preferiu pagar o custo do build pela qualidade da apresentação |
| Dash | Entrega rápido, mas é outro framework para citar e justificar no artigo, e amarra a visualização ao Python |
| Exportar para o Gephi | Ótimo para figuras estáticas do artigo — e continua disponível como conveniência — mas não é aplicação, e a seção 6.1 do briefing pede visualização interativa |

## Consequências

**Boas.** Estado da interface declarativo, o que torna "trocar de
projeção e ver o grafo transicionar" um efeito de estado e não um script.
Tipagem do lado do cliente contra os schemas pydantic, de modo que mudar
um schema sem avisar o front quebra o `tsc`. E espaço para crescer, se a
apresentação pedir mais.

**Ruins.** Entra uma toolchain Node no projeto, com `node_modules`, uma
etapa de build antes de servir, e **Node 18+ como requisito de máquina**.
Quem só quer rodar a análise não precisa de nada disso: a CLI e a API
funcionam sem o front compilado, e `GET /` explica como gerar um. A CI do
Python não depende do front.

**O que muda no código.** `frontend/` inteiro; `_mount_frontend` em
`edugraph/api/app.py`; entradas de `.gitignore`.

## Impacto no artigo

As capturas de tela do capítulo 3 saem desta interface. A escolha em si
vale uma frase na seção de ferramentas — não mais que isso, porque
visualização é meio, não resultado.
