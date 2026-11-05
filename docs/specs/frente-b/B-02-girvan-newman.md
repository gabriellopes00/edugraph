# [B-02] Girvan-Newman com orçamento de tempo

**Frente:** B
**Status:** concluída (20/09/2026)

## Objetivo

Implementar Girvan-Newman com orçamento de tempo, critério de parada e
`status`, de modo que um estouro seja **resultado reportável** e não
falha de execução.

## Contexto

**Cumpre:** `Partition`.
**Consome:** `ProjectionBundle`.

O algoritmo recalcula a intermediação de todas as arestas a cada
remoção: O(m²n). O starter kit mediu **645×** o tempo do Louvain sobre
120 nós. Sobre o OULAD completo, não termina.

Decisão registrada na ADR-0006. O briefing §8 é explícito: tratar a
limitação como resultado.

## Dependências

- Projeções da Frente A.
- **Neutralizada por:** as fixtures.
- A-06 (amostragem) ajuda no OULAD, mas não bloqueia: `sample_nodes`
  pode ser implementado aqui de forma simples enquanto a A-06 não fecha.

## Escopo

### Incluído

- `GirvanNewmanAlgorithm.run` com `time_budget_s`,
  `target_communities`, `sample_nodes` e `seed`.
- Consumir `nx.community.girvan_newman` como iterador, checando o relógio
  **a cada corte** — não dá para interromper depois que o gerador entrou
  numa iteração longa. *(Na implementação foi possível ir além: o relógio
  é consultado também a cada remoção de aresta. Ver "Duas decisões de
  implementação", abaixo.)*
- Guardar a melhor partição por Q vista até o momento.
- Ao estourar: `status="timeout"`, melhor partição, e o número de cortes
  em `params`. **Não levantar exceção** — o contrato proíbe.
- Se nem o primeiro corte couber: `status="skipped"`, partição trivial,
  Q = 0.
- Comando `edugraph community girvan-newman --time-budget N`.

### Fora de escopo

- Paralelizar o cálculo de intermediação.
- Implementar Brandes à mão (ADR-0010 decidiu que não paga).

## Critérios de aceite

- [x] Dado `synthetic_v1` e `time_budget_s=0.01`, quando rodar, então
      devolve `status` em {`timeout`, `skipped`} **sem levantar exceção**
      e com `membership` não vazio. (Medido: `skipped`, 0 cortes,
      partição trivial, devolvida em 0,01 s.)
- [x] Dado `tiny_v1` e orçamento folgado com `target_communities=2`,
      então `status="ok"`, S4 e S5 juntos e separados de S1.
- [x] Dado `target_communities=None`, então para no melhor Q do
      dendrograma.
- [x] `validate_partition` passa nos três status.
- [x] O tempo relativo ao Louvain sobre a mesma projeção está medido — é
      o número que vai para o artigo.

## Testes exigidos

- **Contrato:** artefato com `status="timeout"` passa nos validadores
  como qualquer outro.
- **Unitários** (já escritos como `xfail`): orçamento estourado devolve
  timeout; separação da ponte em `tiny_v1`.
- **Lento:** `test_custo_relativo_do_girvan_newman_esta_medido`, marcado
  `slow` — dendrograma completo sobre `synthetic_v1` (36 s). É ele que
  mede o custo relativo ao Louvain, e roda com `pytest -m slow`.
  A execução sobre uma coorte do OULAD **fica pendente do download** da
  base; o comando é o mesmo com `--root data/processed --dataset
  oulad_bbb_2013j`, e a expectativa registrada na ADR-0006 é que não
  termine — caso em que o artefato sai com `status="timeout"` e vira
  linha da tabela.

## Arquivos criados ou alterados

- `src/edugraph/community/girvan_newman.py`.
- `src/edugraph/community/cli.py` — `cmd_girvan_newman`.
- `tests/community/test_louvain.py` — remover os `xfail` da B-02.

## Números medidos (20/09/2026, `synthetic_v1`)

**O número mais citável do trabalho.** Sobre `student_simple` (98 nós,
1.971 arestas), dendrograma completo:

| algoritmo | Q | k | tamanhos | tempo |
|---|---:|---:|---|---:|
| Louvain | 0,4666 | 3 | 39 / 30 / 29 | 0,024 s |
| Girvan-Newman | 0,4174 | 3 | 42 / 33 / 23 | 34,4 s (97 cortes) |

**1.453× mais lento, com Q menor e o mesmo número de comunidades** — a
mesma ordem de grandeza que o starter kit mediu (645× sobre 120 nós) e o
que sustenta a ADR-0006. As duas partições concordam: NMI 0,774 e Rand
ajustado 0,808; as três áreas plantadas aparecem nas duas.

O custo não é uniforme ao longo do dendrograma: o **primeiro** corte
custa ~15 s dos 34 s, porque é o que ainda tem 1.971 arestas para
recalcular. Depois que o grafo se parte, cada corte fica mais barato.

| orçamento | status | cortes | Q | o que aconteceu |
|---|---|---:|---:|---|
| 600 s | `ok` | 97 | 0,4174 | dendrograma inteiro |
| 5 s | `skipped` | 0 | 0 | nem o primeiro corte coube |
| 0,01 s | `skipped` | 0 | 0 | idem, e devolve em 0,01 s |

Em `discipline_simple` (7 nós) o dendrograma inteiro custa 0,003 s e dá
Q = 0,0331 com k = 4, **três delas unitárias** — o caso que a nota sobre
comunidades unitárias em `docs/contratos/partition.md` descreve, e um
bom contraexemplo para o texto: k maior não é partição melhor.

## Duas decisões de implementação que o texto precisa carregar

1. **A intermediação que escolhe a aresta é não ponderada**, enquanto o
   Q reportado é ponderado. Em NetworkX, peso em caminho mínimo é
   *distância*, e nas projeções peso alto significa afinidade — usá-lo
   inverteria o critério. O Q ponderado é o que torna a linha comparável
   com a do Louvain. As duas escolhas ficam em `params`.
2. **O relógio é consultado a cada remoção de aresta**, não só a cada
   corte, pela função `most_valuable_edge` que o gerador chama. A
   ADR-0006 previa a verificação por corte; como um único corte pode
   custar 15 s, o orçamento seria respeitado com folga grande demais. O
   comportamento observável continua o da ADR: `status="timeout"` com a
   melhor partição vista, nunca exceção.

## Impacto no artigo

**Decisão metodológica** (ADR-0006) e a coluna `status` da tabela
principal do capítulo 3. O tempo relativo ao Louvain é um dos números
mais citáveis do trabalho.
