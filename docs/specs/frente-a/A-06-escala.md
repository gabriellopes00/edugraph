# [A-06] Estratégia de escala e rodada completa do OULAD

**Frente:** A
**Status:** concluída (18/09/2026) — reduções testadas e rodada real feita

## Objetivo

Viabilizar o processamento do OULAD com reduções declaradas e
auditáveis, e gerar `data/processed` para as três frentes.

## Contexto

**Cumpre:** `BipartiteBundle` e `ProjectionBundle` em escala real.
**Consome:** a tabela normalizada.

O briefing §8 avisa: a projeção aluno↔aluno de uma coorte com dois mil
alunos chega a milhões de arestas, e o Girvan-Newman é O(m²n). A
limitação é **resultado a reportar**, não falha a esconder.

## Dependências

- A-02 (OULAD normalizado), A-03 e A-04.
- Esta é a spec que **fecha** as dependências de B e C: quando
  `data/processed` existir, eles só trocam `--root`.

## Escopo

### Incluído

- `filter_cohort` — recorte por apresentação. É a redução preferida:
  recorta por unidade com sentido pedagógico.
- `sample_students` — amostra com seed, registrada no `meta.json`.
- `k_core` — núcleo-k sobre a projeção, reportando quantos nós saíram.
- `prune_by_weight` — corte por peso mínimo, registrado em
  `ProjectionSpec.min_weight` e conferido pelo validador.
- Rodada completa gerando `data/processed`.

### Fora de escopo

- Paralelismo, Dask, computação distribuída — briefing §13.

## Critérios de aceite

- [x] Dado `cohort="BBB_2013J"`, quando filtrar, então só aquela
      apresentação sobra e o número de nós removidos vai para
      `meta.stats`.
- [x] Dada a mesma seed, quando amostrar duas vezes, então a amostra é
      idêntica.
- [x] Dado `min_weight=2.0`, quando podar, então `validate_projection`
      confere que nenhuma aresta abaixo do corte sobreviveu.
- [x] Dada a rodada completa, quando terminar, então `data/processed`
      passa em `edugraph validate` e a suíte de contrato roda sobre ela.
      **Feito**: `oulad_bbb_2013j` e `oulad_module_presentation` gravados
      e validados; `pytest tests/contract --artifacts-root data/processed`
      dá 43 passed, 8 skipped (os pulados dependem das fixtures).
- [x] Tempo e pico de memória da rodada completa estão medidos e
      registrados. **Medidos em 18/09/2026** (Windows, Python 3.13, 15,7 GB):

      | etapa | tempo | memória |
      |---|---:|---:|
      | ETL completo (`data etl`) | 6,3 s | pico 171 MB |
      | coorte BBB_2013J, estágio `data` | 22 s | — |
      | `module_presentation`, bipartido + 2 projeções de disciplina | 4 s | — |
      | projeção aluno↔aluno da base inteira | **não terminou em 10 min** | **> 5 GB** |

**O achado de escala, e ele muda a configuração.** A projeção aluno↔aluno
de `module_presentation` sobre os 22.425 alunos daria ~15,9 milhões de
pares. A construção passou de 5 GB de RAM sem terminar, e foi
interrompida.

**`min_weight` não resolve isso.** O corte acontece *depois* de acumular
os pares no dicionário, então ele reduz o artefato gravado, não o pico de
memória. Quem reduz o pico é a amostra (`sample_students`) ou o recorte
por coorte — que agem *antes* da projeção. Isso está agora dito no
docstring de `prune_by_weight` e nos comentários das configurações.

Consequência prática: `configs/oulad_module_presentation.toml` tem as
duas projeções de aluno **comentadas**, com o aviso; para comunidades de
alunos, use a configuração por coorte ou uma amostra.

## Testes exigidos

- **Contrato:** a suíte inteira roda com `--artifacts-root data/processed`.
- **Unitários:** `tests/data/test_scale.py`, 15 testes — coorte por
  apresentação e por período, erro orientado quando a granularidade não
  carrega apresentação, corte por peso auditável pelo validador, amostra
  determinística e seus limites, núcleo-k, reduções encadeadas no
  histórico, pipeline lendo `[source]` e os comandos `data sample`,
  `data cohort` e `data project --k-core`.
- **Lentos** (`slow` + `oulad`): a rodada completa.

## Arquivos criados ou alterados

- `src/edugraph/data/scale.py`.
- `configs/oulad_module_presentation.toml`,
  `configs/oulad_cohort_bbb_2013j.toml` — ajustar após medir.
- `tests/data/test_scale.py` (novo).
- `src/edugraph/data/pipeline.py` — `sample_students`/`sample_seed`/`k_core`
  lidos de `[source]` (RunConfig é contrato congelado; a decisão de
  escala é sobre a fonte).
- `src/edugraph/data/cli.py` — `data sample`, `data cohort`, `data project --k-core`.

## Impacto no artigo

**Limitação reportada como resultado** (seção de limitações): o que não
coube, por quê, e o que foi feito no lugar. Mais a tabela de tamanhos por
recorte.
