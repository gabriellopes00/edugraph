# [C-04] API FastAPI somente leitura

**Frente:** C
**Status:** concluída (25/09/2026)

## Objetivo

Servir os artefatos em disco como JSON, para o front-end e para o uso
interno da instituição.

## Contexto

**Cumpre:** a API.
**Consome:** todos os bundles.

A API **não calcula nada** (ADR-0004): o cálculo acontece pela CLI. Se
calculasse, importaria `community` e `centrality`, e a fronteira da
ADR-0003 cairia no primeiro endpoint.

Ver `docs/contratos/` e `src/edugraph/api/schemas.py`.

## Dependências

- Nenhuma: a API sobe sobre `data/fixtures` desde o dia 0.
- **`/health` e `/datasets` já estão prontos** e testados.

## Escopo

### Incluído

- `GET /datasets/{dataset}/projections/{projection_id}` — com
  `?partition=` e `?metrics=` para embutir comunidade e centralidades,
  evitando uma segunda ida ao servidor.
- `GET /datasets/{dataset}/bipartite`
- `GET /datasets/{dataset}/communities/{artifact_id}`
- `GET /datasets/{dataset}/centrality/{projection_id}/{metric}`
- `GET /datasets/{dataset}/metrics/{name}`
- **Limite de arestas por resposta**, com o corte declarado no corpo, para
  que a interface possa avisar. Um grafo de um milhão de arestas não
  renderiza e não deve sequer ser transferido.
- 404 com a lista de raízes consultadas — o engano mais comum é esquecer
  o `--root`.

### Fora de escopo

- Qualquer `POST`. Um `POST /runs` pode ser acrescentado depois sem mudar
  os contratos, mas não entra no escopo inicial (ADR-0004).
- Autenticação: o sistema é de uso interno e não expõe dados a terceiros
  (briefing §6.2). Se um dia for exposto, isso vira spec própria.

## Critérios de aceite

- [x] Dada a fixture, cada rota responde 200 e o corpo valida contra o
      schema pydantic.
- [x] Dado um dataset inexistente, então 404 com a mensagem do contrato,
      citando as raízes consultadas.
- [x] Dada uma projeção com mais arestas que o limite, então a resposta
      traz o subconjunto **e** diz que cortou.
- [x] `?partition=louvain__student_simple` embute o `membership` na
      mesma resposta.
- [x] A API **não importa** `edugraph.community` nem `edugraph.data` — o
      teste de fronteira continua verde.
- [x] `edugraph api openapi` gera o esquema que tipa o front.

## Testes exigidos

- **Contrato:** `test_import_boundaries` continua verde.
- **API** (`tests/api/test_api.py`, implementados e passando): cada rota
  200 sobre a fixture; 404 para inexistente.
- Acrescentar: corte de arestas; embutir partição.

## Arquivos criados ou alterados

- `src/edugraph/api/routes.py` — as cinco rotas.
- `src/edugraph/api/schemas.py` — ajustar se preciso (com o front junto).
- `tests/api/test_api.py` — testes das rotas, schemas e erros de contrato.

## Impacto no artigo

Nenhum diretamente. Habilita a C-05, de onde saem as capturas do capítulo
3.

## Como ficou (25/09/2026)

- **Corte de arestas.** Padrão de 5.000 arestas por resposta (`?max_edges=`,
  teto de 50.000), e **todos os nós** permanecem — são eles que carregam
  comunidade e centralidade. Dois critérios (`?cut=`), com desempate
  determinístico:
  - `backbone` (**padrão**, acrescentado na C-05): as k arestas mais
    fortes de cada nó, com o maior k que cabe. No AVA do OULAD
    (`oulad_vle_bbb_2013j`/`student_simple`), k = 2 dá 3.732 arestas e
    **os 1.870 alunos continuam ligados**;
  - `top_weight`: as de maior peso do grafo inteiro. Na mesma projeção,
    as 5.000 mais pesadas tocam só **193** dos 1.870 alunos — o resto
    aparece solto, e a figura engana. Foi o que motivou a troca.

  O corpo traz o bloco `truncation` (`truncated`, `criterion`,
  `k_per_node`, `n_edges_total`, `n_edges_returned`…), que o front usa
  para avisar. Foi o único acréscimo aos schemas, e o
  `frontend/src/types.ts` mudou junto.
- **Números medidos no OULAD.** `oulad_module_presentation`/`discipline_simple`
  com as três centralidades embutidas: 0,1 s. `oulad_vle_bbb_2013j`/`student_simple`
  (1.870 nós, 1,75 M arestas), com o corte `backbone` padrão (k = 2,
  3.732 arestas): 6,3 s e 0,30 MB sem métricas; 6,7 s e 0,47 MB com as
  três embutidas (medido em 26/09/2026). Sem cache: o tempo é quase todo
  a leitura do CSV pelo `contracts.io`, e não compensou a memória de
  manter o grafo carregado.
- **Erros.** 404 cita o artefato e as raízes consultadas; métrica
  inexistente em `?metrics=` dá 422 com a lista das válidas.
