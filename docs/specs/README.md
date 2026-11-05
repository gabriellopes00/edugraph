# Specs — o quadro completo

Vinte e três specs, cada uma no template obrigatório da seção 12 do
briefing e **pronta para virar issue do GitHub**.

Cada spec é executável em uma sessão de trabalho. Se uma parecer grande
demais, quebre a spec — não o PR (ADR-0009).

**Toda spec declara qual fixture substitui a dependência de outra
frente.** É o que garante que ninguém espere por ninguém.

## Por frente

- [Frente A — Dados e Modelagem](frente-a/README.md) `[A]`
- [Frente B — Detecção de Comunidades](frente-b/README.md) `[B]`
- [Frente C — Centralidade e Aplicação](frente-c/README.md) `[C]`

## Quadro geral

| ID | Spec | Onda | Artigo |
|---|---|---|---|
| [A-01](frente-a/A-01-gerador-sintetico.md) | Gerador sintético determinístico | 1 | decisão metodológica |
| [A-02](frente-a/A-02-etl-oulad.md) | ETL do OULAD | 1 | estatísticas do dataset |
| [A-03](frente-a/A-03-bipartido-parametrizavel.md) | Bipartido parametrizável | 2 | critério de aresta |
| [A-04](frente-a/A-04-projecoes-manuais.md) | Projeções à mão | 2 | **algoritmo à mão** |
| [A-05](frente-a/A-05-comparacao-projecao.md) | Manual × NetworkX | 3 | tabela + figura |
| [A-06](frente-a/A-06-escala.md) | Escala e rodada do OULAD | 3 | limitação reportada |
| [A-07](frente-a/A-07-estatisticas-bipartido.md) | Estatísticas e figura | 4 | figura + tabela |
| [A-08](frente-a/A-08-modelo-nulo.md) | **Modelo nulo** (spec nova) | 3 | **tabela + método**: Q sem linha de base não é resultado |
| [A-09](frente-a/A-09-granularidades-do-ava.md) | **Granularidades do AVA** (spec nova) | 3 | **tabela**: o critério de aresta escolhido depois de medir |
| [B-01](frente-b/B-01-louvain.md) | Louvain | 1 | — |
| [B-02](frente-b/B-02-girvan-newman.md) | Girvan-Newman com orçamento | 2 | decisão metodológica |
| [B-03](frente-b/B-03-modularidade.md) | Q à mão | 1 | **algoritmo à mão** |
| [B-04](frente-b/B-04-comparacao.md) | Comparação de comunidades | 2 | **tabela principal** |
| [B-05](frente-b/B-05-caracterizacao.md) | Caracterização | 3 | **saída obrigatória** |
| [B-06](frente-b/B-06-validacao.md) | Validação a posteriori | 3 | tabela de validação |
| [B-07](frente-b/B-07-figuras.md) | Figuras de comunidades | 4 | figuras |
| [C-01](frente-c/C-01-grau-intermediacao.md) | Grau e intermediação | 1 | decisão sobre o peso |
| [C-02](frente-c/C-02-autovetor.md) | Autovetor à mão | 2 | **algoritmo à mão** |
| [C-03](frente-c/C-03-disciplinas-criticas.md) | Disciplinas críticas | 2 | **saída obrigatória** |
| [C-04](frente-c/C-04-api.md) | API somente leitura | 1 | — |
| [C-05](frente-c/C-05-frontend.md) | Front-end | 2 | capturas |
| [C-06](frente-c/C-06-validacao-centralidade.md) | Validação de centralidade | 3 | tabela + figura |
| [C-07](frente-c/C-07-relatorio-interno.md) | Relatório interno | 4 | **saída obrigatória** |

## As que o artigo não pode perder

Se o prazo apertar, estas quatro são as que respondem diretamente ao
objetivo declarado na Introdução, e nenhuma delas pode cair:

- **A-04** — a projeção implementada à mão. É o que o briefing §7 exige
  explicitamente.
- **B-05** — caracterização das comunidades. Sem ela, os agrupamentos não
  são "interpretáveis", que é a palavra do objetivo declarado.
- **C-03** — disciplinas críticas. É a outra metade do objetivo, e a
  seção 13 do briefing avisa que é fácil de esquecer.
- **C-07** — relatório interno. É a saída obrigatória da seção 6.2.

## Como virar issue

Título: `[A-04] Projeções implementadas à mão`. Corpo: o arquivo inteiro.
Labels sugeridas: `frente-a`/`frente-b`/`frente-c`, `onda-1`…`onda-4`,
`artigo` quando gerar figura ou tabela.

Branch: `a/A-04-projecao-manual`. Commit:
`A-04: projeções simples e de alocação de recursos`.

## Como fechar uma spec

1. Implementar; remover os `@pytest.mark.xfail` correspondentes.
2. `ruff check . && ruff format --check . && pytest -m "not slow"` verde.
3. Marcar **Status: concluída** no arquivo da spec, no mesmo PR.
4. Se gerou figura ou tabela, conferir que ela entrou nos índices de
   `docs/artigo/`.

Um `xfail(strict=True)` que passa **quebra a CI** de propósito: é o aviso
de que a spec fechou e o marcador pode sair.
