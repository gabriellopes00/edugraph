# [A-02] ETL do OULAD: download, esquema e tabela normalizada

**Frente:** A
**Status:** concluída (18/09/2026), incluindo a rodada na base completa

## Objetivo

Transformar as sete tabelas do OULAD numa tabela normalizada com uma
linha por (aluno, disciplina, apresentação), com nota média, cliques no
AVA e desfecho.

## Contexto

**Cumpre:** a tabela normalizada (contrato interno da Frente A) e
`Outcomes`.
**Consome:** os sete CSV brutos.

Open University Learning Analytics Dataset (Kuzilek; Hlosta; Zdrahal,
2017), ~32 mil estudantes. `studentVle.csv` tem ~10,6 milhões de linhas.

**Pode ser dividida em duas specs** se ficar grande: (a) download +
esquema, (b) normalização.

## Dependências

- **Download do OULAD** (~450 MB), passo manual documentado no README.
- **Neutralizada por:** `tests/data/oulad_mini/` — sete arquivos
  minúsculos com o esquema real, já no repositório. O desenvolvimento
  inteiro acontece contra eles; a base completa só é necessária na
  rodada final.

## Escopo

### Incluído

- `download.py`: baixar, conferir SHA-256, extrair, não sobrescrever
  download válido sem `--force`.
- `schema.py`: completar `SCHEMAS` conferindo contra o dicionário de
  dados publicado; `validate_schema` falha cedo e com mensagem clara.
- `etl.py`: junções, agregação e a tabela normalizada; cache em
  `data/interim`.
- Decidir e **registrar** a regra para aluno com mais de uma matrícula no
  mesmo módulo.
- Leitura com `usecols` e `dtype` explícitos.

### Fora de escopo

- Construção do grafo — é a A-03.
- Imputação de dados faltantes por qualquer método aprendido.

## Critérios de aceite

- [x] Dado `tests/data/oulad_mini/`, quando rodar `normalize`, então a
      tabela tem as colunas de `NORMALIZED_COLUMNS` e nenhuma duplicata
      de (aluno, módulo, apresentação).
- [x] Dada uma tabela sem uma coluna esperada, quando ler, então falha
      com mensagem que nomeia a tabela e a coluna.
- [x] Dado o OULAD completo, quando rodar com `cache_dir`, então a
      segunda execução não relê `studentVle.csv`. *Mecanismo pronto e
      testado sobre `oulad_mini` (o teste remove o `studentVle.csv` entre
      as duas chamadas e a segunda ainda responde do cache; alterar a
      fonte expira o cache). Confirmado na base completa: 5,8 s na
      primeira execução, 0,03 s na segunda.*
- [x] Dado o OULAD completo, quando rodar, então o pico de memória cabe
      num notebook de 8 GB — **medido em 18/09/2026**: `normalize` leva
      **5,8 s** e `normalize_assessments` **0,5 s**, com **pico de 171 MB**
      de working set (base do processo: 79 MB). A segunda execução vem do
      cache em **0,03 s**. Cabe com folga: o gargalo de memória do projeto
      não é o ETL, é a projeção aluno↔aluno (ver A-06).
- [x] A nota média por matrícula é ponderada pelo `weight` da avaliação,
      e a escolha está registrada em `docs/artigo/`.
- [x] `to_outcomes` produz um desfecho por aluno, com a regra de
      desempate documentada.

## Testes exigidos

- **Contrato:** `outcomes.csv` gerado passa em `validate_outcomes`.
- **Unitários** (`tests/data/test_bipartite.py`, já esboçados): esquema
  de `oulad_mini` bate com `SCHEMAS`; `normalize` produz a tabela sem
  duplicatas; matrícula cancelada vira `Withdrawn`; avaliação sem data
  não quebra a leitura.
- **Lento** (`@pytest.mark.slow` + `@pytest.mark.oulad`): rodada sobre a
  base completa — *não escrito: exigiria a base de 450 MB na CI, e os
  números de referência já estão registrados aqui e em
  `docs/artigo/decisoes-metodologicas.md`. Se o grupo quiser o teste,
  ele é da onda 4.*
- **Escritos:** `tests/data/test_etl.py`, 17 testes sobre `oulad_mini` —
  esquema das sete tabelas, atributos demográficos não carregados,
  mensagens de erro, média ponderada (e simples quando Σpeso = 0),
  cliques, leitura em blocos, descarte sem evidência, cache e expiração,
  tabela por avaliação, regra de desfecho, `verify`/`download` sem rede,
  comando `data etl`.

## Arquivos criados ou alterados

- `src/edugraph/data/oulad/download.py`, `schema.py`, `etl.py`.
- `src/edugraph/data/cli.py` — `cmd_etl`.
- `scripts/download_oulad.py` (já existia; usa `download.py`).
- `src/edugraph/data/pipeline.py` — fonte `oulad` escolhe a tabela pelo grão
  (`assessment` → tabela por avaliação).
- `OULAD_SHA256` **preenchido** no download de 18/09/2026:
  `f2ed1902…e2c6d3e4` (46.748.244 bytes, espelho do UCI).

**Três correções que só a base real revelou** (o `oulad_mini` foi
corrigido para reproduzi-las, e os testes agora as cobrem):

1. **Ausente é `?`, não vazio**, na distribuição do UCI —
   `studentAssessment.score` traz `?`, e o `dtype=float64` explodia na
   leitura. `schema.NA_VALUES` aceita os dois.
2. **Cabeçalhos entre aspas** (`"code_module"`): `verify()` lia o
   cabeçalho com `split(",")` e via nomes com aspas; agora usa
   `csv.reader`.
3. **`cache_dir` como `str`** quebrava o `/` de `pathlib` — agora é
   convertido em `Path`.

**O link oficial está quebrado.** `analyse.kmi.open.ac.uk` redireciona
para `research.stem.open.ac.uk/ouanalyse`, cuja página do dataset aponta
para `schools.stem.open.ac.uk/cdn/files/anonymisedData.zip` — **404**. O
download passou a usar o espelho do UCI (id 349). A citação do artigo não
muda.
- `tests/data/test_bipartite.py`.

## Impacto no artigo

Estatísticas descritivas do dataset (seção de dados) e duas decisões
metodológicas a registrar: a regra de agregação de matrículas repetidas e
a ponderação da nota média.
