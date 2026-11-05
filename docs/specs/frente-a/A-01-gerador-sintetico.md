# [A-01] Gerador sintético determinístico com comunidades plantadas

**Frente:** A
**Status:** concluída (18/09/2026)

## Objetivo

Estender o gerador sintético do dia 0 para produzir datasets com número
de grupos configurável e com a esparsidade do OULAD, e gravar o resultado
como artefatos de contrato.

## Contexto

**Cumpre:** `BipartiteBundle`, `Outcomes`.
**Consome:** nada — é a origem do pipeline.

A base secundária declarada no briefing §8: comunidades plantadas de
propósito servem de *ground truth* para verificar se Louvain e
Girvan-Newman recuperam estrutura conhecida.

`edugraph/data/synthetic.py` **já funciona** para os parâmetros do
starter kit (seed 42, três grupos de 40, 30% em risco) — é dele que sai
`data/fixtures/synthetic_v1`. Esta spec acrescenta o que falta.

Ver `docs/contratos/bipartite.md` e `docs/contratos/outcomes.md`.

## Dependências

- Nenhuma de outra frente.
- Depende de A-03 (construção do bipartido) para gravar artefatos; até
  lá, é possível fechar o gerador e testá-lo só pelas matrículas.

## Escopo

### Incluído

- `SyntheticSpec.sparsity`: remoção determinística de matrículas para
  imitar o OULAD, onde a maior parte dos alunos aparece em uma única
  matrícula.
- Número de grupos e de módulos por grupo configuráveis.
- Uma fixture nova `synthetic_v2`, com esparsidade realista, gerada por
  `scripts/make_fixtures.py`.
- Comando `edugraph data synthetic --seed N --out DIR`.

### Fora de escopo

- Qualquer modelo generativo aprendido a partir do OULAD real — violaria
  a restrição do briefing §2.
- Alterar `synthetic_v1`: fixtures são imutáveis (ADR-0011).

## Critérios de aceite

- [x] Dado `SyntheticSpec(seed=42)`, quando gerar duas vezes, então as
      matrículas são idênticas.
- [x] Dado `sparsity`, quando gerar, então a fração de alunos com uma só
      matrícula acompanha o parâmetro e a mediana cai para 1 a partir de
      ~0,6. *Medido com seed 42: base tem mediana 2 e ninguém com uma só;
      0,5 deixa 48% com uma (mediana ainda 2, na fronteira); 0,7 leva a
      mediana a 1 com 68%. A estimativa original desta spec — "0,5 já
      baixa a mediana para 1" — estava errada, e é por isso que
      `synthetic_v2` usa 0,7. A comparação com o OULAD real fica para a
      A-02.*
- [x] Dado `sparsity` alto, quando gerar, então o grupo plantado continua
      recuperável — se a esparsidade destruir a estrutura, isso é achado
      e vai para o texto. *Em `synthetic_v2` (0,7), a pureza do Louvain de
      referência contra o grupo plantado é 0,86 (simples) e 0,84
      (alocação de recursos): recuperável, com perda. Registrado no
      `REFERENCE.md` da fixture.*
- [x] Dado `--seed 7 --out data/processed`, quando rodar o comando, então
      o dataset é gravado e passa em `edugraph validate`.
- [x] `synthetic_v2` existe, é imutável e tem `REFERENCE.md`.

## Testes exigidos

- **Contrato:** `synthetic_v2` passa em `validate_dataset`.
- **Unitários** (`tests/data/test_synthetic.py`, já existentes e a
  estender): determinismo; seeds diferentes geram dados diferentes;
  tamanhos de grupo; faixa de matrículas por aluno; existência de ruído;
  vocabulário de `final_result`.
- `test_esparsidade_ainda_nao_implementada` removido; +8 testes (esparsidade,
  determinismo, grupo plantado preservado, sinal das áreas, faixa do
  parâmetro, `make_groups`, número de grupos, comando `data synthetic`).

## Arquivos criados ou alterados

- `src/edugraph/data/synthetic.py` — implementar `sparsity`; generalizar
  grupos.
- `src/edugraph/data/cli.py` — `cmd_synthetic`.
- `scripts/make_fixtures.py` — `make_synthetic_v2`.
- `tests/data/test_synthetic.py`.

## Impacto no artigo

**Achado registrado.** Em `synthetic_v2`, a projeção disciplina↔disciplina
**deixa de ser completa** (16 de 21 arestas): a esparsidade remove pares de
disciplinas sem aluno em comum, e a intermediação passa a discriminar — ao
contrário de `synthetic_v1`, que é K₇. Ou seja, a degeneração da decisão D1
depende tanto da granularidade quanto da esparsidade, e o OULAD tem as duas
contra si. Ver `data/fixtures/synthetic_v2/REFERENCE.md`.


A esparsidade realista é o que permite mostrar, **antes do OULAD**, o
efeito da decisão D1 sobre a projeção. Rende uma figura comparando a
distribuição de matrículas por aluno em `synthetic_v1`, `synthetic_v2` e
OULAD, e um parágrafo na seção de dados.
