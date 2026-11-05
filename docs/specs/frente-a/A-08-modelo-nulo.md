# [A-08] Modelo nulo: a linha de base da modularidade

**Frente:** A
**Status:** concluída (18/09/2026)

## Objetivo

Gerar, a partir de um bipartido real, réplicas com os mesmos graus e
**sem nenhuma estrutura**, para que a Frente B possa dizer se um Q alto
significa alguma coisa.

## Contexto

**Cumpre:** `BipartiteBundle` (datasets `<nome>_null<seed>`).
**Consome:** `BipartiteBundle`.

Esta spec não estava no plano original. Ela nasceu de uma medição na
base real, em 18/09/2026, que mostrou que sem ela o trabalho concluiria
o contrário do certo.

**O problema.** A modularidade encontra "comunidades" em qualquer grafo
esparso, mesmo sem estrutura nenhuma — é um resultado conhecido
(Guimerà et al., 2004). Então `Q = 0,77` no OULAD, sozinho, não é
evidência de que existam perfis de alunos.

**A medição.** Projeção aluno↔aluno, Louvain com seed 42:

| dataset | Q real | Q nulo | veredito |
|---|---:|---|---|
| `synthetic_v1` | 0,4666 | 0,2079 ± 0,0168 (z = **+15,4**) | estrutura real |
| `synthetic_v2` | 0,5392 | 0,4611 ± 0,0202 (z = **+3,9**) | estrutura real, sinal fraco |
| OULAD `module_presentation`, amostra de 3.000 | 0,7728 | 0,7807 e 0,7816 | **indistinguível do acaso** |

Duas leituras, e as duas importam:

1. **O método funciona.** No sintético com grupos plantados, o Q real
   fica 15 desvios acima do nulo. Louvain recupera estrutura quando ela
   existe — isso valida o método.
2. **O OULAD não tem essa estrutura.** O Q de 0,77 é *menor* que o das
   réplicas embaralhadas. Reportá-lo como "encontramos 15 comunidades de
   perfis" seria falso.

Repare também que o Q nulo de `synthetic_v2` (0,46) é muito maior que o
de `synthetic_v1` (0,21): **a esparsidade sozinha infla a modularidade**.
É o mesmo mecanismo que produz o 0,78 do OULAD.

## Dependências

- A-03, para ter um bipartido. Nenhuma de outra frente.
- A Frente B consome os artefatos na spec B-06; a comparação de Q é
  dela, não desta (ADR-0003).

## Escopo

### Incluído

- `null_bipartite(bundle, seed)`: preserva os nós, o grau de cada aluno
  e o total de arestas; preserva o grau das disciplinas em expectativa,
  sorteando de uma urna ponderada por ele.
- `null_replicas(bundle, n, seed)`: réplicas com sementes consecutivas —
  uma só dá um número, a comparação honesta precisa de média e desvio.
- `is_null(bundle)`: a marca em `meta.stats["null_model"]`, para que a
  Frente B distinga nulo de real sem adivinhar pelo nome.
- Comando `edugraph data null --dataset X --replicas N [--projections]`.

### Fora de escopo

- **Calcular ou comparar Q** — é da Frente B (spec B-06). Aqui só se
  gera o artefato.
- Modelos nulos mais sofisticados (troca dupla de arestas preservando os
  dois graus exatamente). Tentado: `nx.double_edge_swap` não converge na
  coorte do OULAD, densa demais (1.418.000 tentativas sem completar as
  70.900 trocas). A urna ponderada é a aproximação que funciona, e o que
  ela não preserva exatamente está documentado.
- Misturar réplicas com dados reais. **Nunca.** Ver o impacto no artigo.

## Critérios de aceite

- [x] Dado um bipartido, quando gerar o nulo, então cada aluno mantém o
      grau exato e o total de arestas é o mesmo.
- [x] Dado o nulo, então o grau das disciplinas correlaciona com o real
      acima de 0,8 (preservação em expectativa).
- [x] Dada a mesma semente, duas execuções dão o mesmo grafo; sementes
      diferentes dão grafos diferentes.
- [x] Dado `synthetic_v1`, onde há grupos plantados, então a fração de
      arestas intragrupo cai de 0,5+ no real para perto do acaso (~1/3)
      no nulo — **o nulo de fato destrói a estrutura**.
- [x] Dado um grafo que já não tem estrutura, então o nulo tem o mesmo
      número de arestas na projeção (±15%) — contraprova.
- [x] Dada uma urna concentrada (uma disciplina dominante), o grau do
      aluno ainda é completado; o nulo nunca tem menos arestas que o
      real.
- [x] O artefato se identifica como nulo por `meta.stats`, e a marca
      sobrevive ao round-trip.
- [x] `validate_bipartite` e `validate_dataset` passam nas réplicas.

## Testes exigidos

- **Contrato:** réplicas passam em `validate_dataset`.
- **Unitários:** `tests/data/test_nullmodel.py`, 10 testes — os oito
  critérios acima, mais réplicas com sementes consecutivas e o comando
  `data null`.

## Arquivos criados ou alterados

- `src/edugraph/data/nullmodel.py` (novo).
- `src/edugraph/data/cli.py` — `data null`.
- `tests/data/test_nullmodel.py` (novo).
- `docs/artigo/decisoes-metodologicas.md` — o achado.

## Impacto no artigo

**Alto, e é o principal desta rodada.** Muda o que o capítulo 3 pode
afirmar e acrescenta uma seção de método:

- A comparação com o modelo nulo vira **tabela** e parágrafo de método:
  "a significância de Q foi avaliada contra réplicas que preservam a
  distribuição de grau".
- O resultado sobre o OULAD é **negativo e precisa ser reportado como
  tal**: a estrutura de comunidades encontrada na projeção aluno↔aluno
  não se distingue do acaso. Isso não é fracasso do trabalho — é o tipo
  de rigor que separa "rodamos Louvain" de "verificamos se o resultado
  significa algo", e responde antecipadamente à pergunta de banca mais
  provável.
- O contraste com o sintético sustenta a afirmação de que o **método**
  funciona, o que a Conclusão precisa para responder ao objetivo
  declarado.
