# [B-05] Caracterização: quais disciplinas predominam em cada comunidade

**Frente:** B
**Status:** concluída (20/09/2026)

## Objetivo

Para cada comunidade encontrada, dizer **o que ela é** — tamanho, densidade
interna e disciplinas predominantes.

## Contexto

**Cumpre:** `communities/<id>/profile.csv`.
**Consome:** `Partition`, `BipartiteBundle`.

**Saída obrigatória do TCC.** O briefing §6.2 exige "agrupamentos
interpretáveis de perfis de estudantes, com caracterização de quais
disciplinas predominam em cada comunidade". Uma partição sem esta etapa
diz *quem está junto*, não *por quê* — e não responde ao objetivo
declarado na Introdução.

É a única spec da Frente B que precisa do **bipartido**, além das
projeções.

## Dependências

- B-01, para ter partições.
- Bipartido da Frente A.
- **Neutralizada por:** `data/fixtures/synthetic_v1/bipartite/`.

## Escopo

### Incluído

- `characterize(partition, bipartite, top_k)` → linhas no formato de
  `PROFILE_COLUMNS`.
- **Frequência em excesso sobre a base, não em absoluto.** A disciplina
  obrigatória que todo mundo cursa aparece em todas as comunidades e não
  caracteriza nenhuma. Reportar a frequência relativa ao lado da
  absoluta.
- `community_sizes()` para a figura da B-07.
- Comando `edugraph community characterize`.

### Fora de escopo

- Cruzar com o desfecho — é a B-06, e misturar as duas coisas aqui
  arriscaria o vazamento que a ADR-0008 impede.

## Critérios de aceite

- [x] Dada a partição de referência de `synthetic_v1`, então há uma linha
      por comunidade, com as colunas de `PROFILE_COLUMNS`.
- [x] As comunidades grandes (≥10 alunos) têm **conjuntos diferentes** de
      disciplinas predominantes — se todas listarem as mesmas, a
      frequência está sendo medida em absoluto.
- [x] O gerador plantou três áreas (exatas, sistemas, humanas); as três
      comunidades grandes de `synthetic_v1` refletem isso.
- [x] `profile.csv` é escrito com escrita canônica e é legível por quem
      não programa — é o insumo do relatório interno (C-07).
- [x] Nenhum acesso a `outcomes.csv` neste módulo (verificado pelo teste
      de contrato).

## Testes exigidos

- **Contrato:** `test_outcomes_isolation` continua verde — este módulo
  não pode ler rótulo.
- **Unitários** (já escritos como `xfail`): colunas do perfil; comunidades
  grandes se distinguem.

## Arquivos criados ou alterados

- `src/edugraph/community/characterize.py`.
- `src/edugraph/community/cli.py` — `cmd_characterize`.
- `tests/community/test_caracterizacao.py` — remover os `xfail`.

## O perfil, como ele sai hoje (20/09/2026, `synthetic_v1`, Louvain)

| comunidade | tamanho | densidade interna | disciplinas predominantes |
|---:|---:|---:|---|
| 0 | 39 | 0,919 | EEE 84,6% (base 34,7%, n=33); DDD 74,4% (base 31,6%, n=29) |
| 1 | 29 | 0,921 | BBB 75,9% (base 25,5%, n=22); CCC 75,9% (base 27,6%, n=22) |
| 2 | 30 | 0,959 | GGG 90,0% (base 30,6%, n=27); FFF 80,0% (base 27,6%, n=24) |

**As três áreas plantadas pelo gerador aparecem inteiras**: sistemas
(DDD-EEE), exatas (AAA-BBB-CCC) e humanas (FFF-GGG), uma por comunidade
grande, descobertas **só pela topologia**. É a frase que a Conclusão
precisa poder escrever.

A terceira disciplina de cada linha, com `top_k = 3`, é sempre AAA —
5,1%, 62,1% e 10,0% contra 23,5% da base. Ela só caracteriza a
comunidade 1; nas outras duas aparece com frequência **abaixo** da base,
e é justamente por isso que a coluna mostra as duas frequências lado a
lado.

Sobre a partição do Girvan-Newman (42/33/23) o perfil aponta as mesmas
três áreas, com fronteiras diferentes — o que sustenta, no texto, que o
achado é da estrutura e não do algoritmo.

## Três definições que o texto precisa declarar

- **Excesso sobre a base.** A ordem das disciplinas é por
  `frequência na comunidade − frequência na base`, não por contagem. Sem
  isso, a disciplina obrigatória lidera todas as comunidades.
- **A base é a própria partição**, não o bipartido inteiro: é a
  população que foi dividida. A diferença só aparece em partição parcial
  (Girvan-Newman com amostra), e aí a base certa é o recorte.
- **`mean_degree` e `internal_density` saem do bipartido**, não da
  projeção: são "média de disciplinas por aluno" e "fração dos pares da
  comunidade que compartilham ao menos uma disciplina". Assim as colunas
  significam a mesma coisa para partições de projeções diferentes, que é
  o que torna as linhas comparáveis entre si.

## Impacto no artigo

**Saída obrigatória**: é a tabela que mostra que os agrupamentos são
interpretáveis, que é metade do que a Conclusão precisa responder.
