# Como cada frente trabalha sem bloquear as outras

Este é o requisito central do briefing (§4) e o critério pelo qual o
plano foi avaliado. As dependências reais entre as frentes **existem** —
o que muda é que nenhuma delas bloqueia ninguém.

A regra é uma só: **toda dependência de outra frente é satisfeita no dia
0 por uma fixture ou por um contrato, e é fechada de verdade mais tarde
só com troca de `--root`.**

## As dependências e o que as neutraliza

| Dependência real | Quem sente | Neutralizada por | Fecha de verdade quando |
|---|---|---|---|
| Projeções aluno↔aluno e disciplina↔disciplina | `[B]` `[C]` | `synthetic_v1/projections/*` e `tiny_v1` | A-04 grava em `data/processed` e B/C apontam `--root` para lá |
| Grafo bipartido, para saber quais disciplinas predominam em cada comunidade | `[B]` | `synthetic_v1/bipartite/` | A-03 |
| Partição, para colorir o grafo e servir a API | `[C]` | `synthetic_v1/communities/louvain__*`, gerada pela biblioteca e marcada como referência | B-01 |
| Centralidades, para a API e o front | `[C]` (mesma pessoa) | `synthetic_v1/centrality/*`, idem | C-01 e C-02 |
| Desfecho real de cada matrícula | `[B]` `[C]` | `outcomes.csv` nas fixtures, com o grupo plantado | A-02, com o OULAD |
| OULAD baixado (~450 MB) | `[A]` | `tests/data/oulad_mini/`: sete arquivos minúsculos com o esquema real | download manual documentado no README |
| Contratos, leitura/escrita e validadores | todos | entregues prontos e testados no dia 0 | congelados; mudança por ADR |
| Tabelas do artigo com números do OULAD | todos | formato fixo em `metrics/`; cada spec gera sua tabela sobre fixtures primeiro | rodada final (onda 4) |

## O que há nas fixtures

### `tiny_v1` `[T]` — a fixture dos testes exatos

Seis alunos e três disciplinas. A projeção aluno↔aluno é um **K4** em
{S1, S2, S3, S6} colado a um **triângulo** {S3, S4, S5}: S3 é o único
vértice de corte.

Desenhada para que as duas ponderações **ordenem os pares de forma
diferente**: S1-S6 e S3-S4 empatam em 1 na projeção simples, mas ficam
0,25 e 1/3 na alocação de recursos. É o contraexemplo mínimo do viés que
Zhou et al. (2007) corrigem.

Vem com `expected/`, cujos valores foram **derivados no papel**, não
copiados da saída do NetworkX — é isso que faz dos testes que os consomem
uma verificação, e não uma tautologia. A derivação de cada um está
comentada em `scripts/make_fixtures.py` e em
[`../testes/estrategia.md`](../testes/estrategia.md).

### `synthetic_v1` `[T]` — a fixture de escala realista

Porta fiel do gerador do starter kit: seed 42, três grupos de 40 alunos,
sete disciplinas, ~30% em risco, 35% de ruído entre grupos. Traz o
bipartido, as quatro projeções, partições Louvain e centralidades de
referência, mais `outcomes.csv` com o grupo plantado.

Números recalculados na geração e registrados em
`data/fixtures/synthetic_v1/REFERENCE.md`: 98 alunos, 197 arestas,
Louvain com Q ≈ 0,467 e 3 comunidades na projeção aluno↔aluno simples.

Os testes usam **faixas**, não igualdade exata: Louvain é estocástico e
uma troca de versão da biblioteca move o quarto decimal sem que nada
esteja errado.

### `synthetic_v2` `[A]` — a fixture com esparsidade tipo OULAD

Mesma seed e mesmos três grupos de `synthetic_v1`, mas com
`sparsity = 0.7`: 70% dos alunos ficam com **uma** matrícula só — o
perfil do OULAD, onde a maioria dos alunos aparece uma única vez
(decisão D1). Criada pela spec A-01.

O que muda, e por que ela existe: 81 alunos, 105 arestas, mediana de uma
matrícula por aluno. A projeção disciplina↔disciplina **deixa de ser
completa** (16 de 21 arestas) e a intermediação passa a discriminar —
em `synthetic_v1` ela é K₇ e toda intermediação é zero. A pureza do
Louvain de referência contra o grupo plantado cai para 0,86: as áreas
continuam recuperáveis, com perda. Números em
`data/fixtures/synthetic_v2/REFERENCE.md`.

É a fixture certa para a spec C-03 (disciplinas críticas) exercitar um
ranking que discrimina, e para a B-06 medir o custo da esparsidade na
recuperação das comunidades.

### Fixtures são imutáveis

Quem precisar de outra cria `synthetic_v3`. As versões anteriores
continuam existindo para os testes que dependem delas.

Isso elimina a classe inteira de conflitos "a fixture mudou e meu teste
quebrou".

## A segunda-feira de cada frente

Nenhum destes comandos executa código de outra frente.

### `[A]` Dados e Modelagem

```bash
python -m edugraph data synthetic --seed 7 --out data/processed
python -m edugraph data bipartite configs/synthetic_v1.toml
python -m edugraph data project --dataset synthetic_dev \
    --side discipline --weighting resource_allocation
pytest tests/data tests/contract
```

Desenvolve o ETL do OULAD contra `tests/data/oulad_mini/`; roda a base
completa só quando o download estiver feito.

### `[B]` Comunidades

```bash
python -m edugraph community louvain \
    --root data/fixtures --dataset synthetic_v1 --projection student_simple
python -m edugraph community girvan-newman \
    --root data/fixtures --dataset synthetic_v1 --projection student_simple \
    --time-budget 60
pytest tests/community tests/contract
```

Quando o OULAD chegar: `--root data/processed --dataset oulad_bbb_2013j`.
**Nada mais muda.**

### `[C]` Centralidade e Aplicação

```bash
python -m edugraph centrality all --root data/fixtures --dataset synthetic_v1
python -m edugraph api serve --root data/processed --root data/fixtures
cd frontend && npm run dev
pytest tests/centrality tests/api tests/contract
```

A API e a interface nascem sobre a fixture no dia 0 e **não sabem** se a
partição veio da Frente B ou da biblioteca.

## Onde as frentes se encontram no código

Em exatamente dois arquivos:

- `src/edugraph/__main__.py` — a raiz de composição, ~200 linhas, escrita
  no dia 0. Não precisa ser editada quando uma frente implementa o seu
  estágio.
- `src/edugraph/contracts/registry.py` — importa os estágios por nome
  para povoar o registro.

`tests/contract/test_import_boundaries.py` analisa os imports com `ast` e
falha se qualquer outro arquivo cruzar a fronteira. A lista de isenções
tem um teste próprio que quebra se ela crescer. A fronteira da seção 4.3
do briefing é, assim, um teste que roda na CI — não uma convenção.

## Ordem de entrega

**Dia 0** — o que destrava todo mundo, em `main` antes de qualquer spec.
É a entrega deste repositório: contratos testados, `tiny_v1` e
`synthetic_v1`, esqueleto das três frentes, testes de contrato verdes,
CI, documentação, ADRs e as 21 specs.

Depois, a onda N+1 de uma frente **nunca** depende da onda N de outra. As
ondas são sugestão de ritmo, não obrigação.

| Onda | `[A]` Dados e Modelagem | `[B]` Comunidades | `[C]` Centralidade e Aplicação |
|---|---|---|---|
| 1 | A-01 gerador · A-02 ETL OULAD | B-01 Louvain · B-03 Q à mão | C-01 grau e intermediação · C-04 API |
| 2 | A-03 bipartido · A-04 projeções manuais | B-02 Girvan-Newman · B-04 comparação | C-02 autovetor · C-03 disciplinas críticas · C-05 front-end |
| 3 | A-05 manual × NetworkX · A-06 escala e rodada OULAD | B-05 caracterização · B-06 validação | C-06 validação de centralidade |
| 4 | A-07 tabelas e figuras | B-07 figuras | C-07 relatório interno |

Na onda 4, as três frentes trocam `--root` para o OULAD e geram as saídas
finais em `results/`. É o único momento em que as três dependem de um
artefato real — e ele já existe desde a onda 3.
