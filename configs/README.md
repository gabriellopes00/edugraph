# `configs/` — uma configuração por experimento

Cada arquivo é **uma linha das tabelas comparativas do capítulo 3**.
Tudo o que o artigo compara vive aqui, não no código: granularidade do
nó disciplina, critério de aresta, ponderação, algoritmo e orçamento de
tempo (ADR-0007).

```bash
python -m edugraph run configs/synthetic_v1.toml
python -m edugraph run configs/synthetic_v1.toml --only community
python -m edugraph run configs/synthetic_v1.toml --from community --dry-run
```

| Arquivo | Fonte | Granularidade | Para quê |
|---|---|---|---|
| `synthetic_v1.toml` | gerador | `module` | roda em qualquer máquina, sem download; é o que a CI usa |
| `oulad_module_presentation.toml` | OULAD | `module_presentation` | granularidade recomendada pela decisão D1 (22 nós) |
| `oulad_cohort_bbb_2013j.toml` | OULAD | `assessment` | uma coorte, para viabilizar o Girvan-Newman |
| `oulad_vle_bbb_2013j.toml` | OULAD | recurso do AVA | comunidades de alunos: o bipartido com sinal acima do modelo nulo (A-09) |

## Como acrescentar uma configuração

Copie a mais próxima, mude o que compara e **mude o `dataset`**: dois
TOML com o mesmo `bipartite.dataset` gravam na mesma pasta e um
sobrescreve o outro.

Configurações são versionadas junto com o resultado que produziram. Se um
número do artigo precisar ser refeito, o arquivo que o gerou está aqui.
