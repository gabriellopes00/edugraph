# [B-06] Validação a posteriori das comunidades

**Frente:** B
**Status:** concluída (20/09/2026)

## Objetivo

Verificar se a estrutura descoberta **apenas pela topologia** guarda
relação com o grupo plantado (sintético) e com o desfecho histórico.

## Contexto

**Cumpre:** tabela de validação para o artigo.
**Consome:** `Partition`, `Outcomes`.

**Este é o único módulo da Frente B autorizado a ler `outcomes.csv`**
(ADR-0008). Um teste de contrato falha se `load_outcomes` for chamada de
qualquer outro lugar.

O que se mede **não é acurácia de um modelo** — não há modelo. NMI,
pureza e distribuição de desfechos são medidas entre partições e
categorias já conhecidas.

## Dependências

- B-01, para ter partições.
- `outcomes.csv`, que já existe nas fixtures **com o grupo plantado**.

> **Nota da Frente A (18/09/2026) — leia antes de reportar qualquer Q.**
> A spec **A-08** acrescentou réplicas do **modelo nulo**: o mesmo grafo
> com os mesmos graus e a estrutura embaralhada. Elas já estão em
> `data/processed` (`oulad_module_presentation_null0..2`) e saem de
> `edugraph data null --dataset X --replicas N`.
>
> Isso importa porque a modularidade encontra "comunidades" em qualquer
> grafo esparso. Medido: em `synthetic_v1` o Q real (0,4666) fica 15
> desvios acima do nulo (0,208 ± 0,017) — o método funciona; no OULAD
> `module_presentation` o Q real (0,7728) é **menor** que o das réplicas
> (0,781) — ali não há estrutura a reportar.
>
> **Atualização (A-09, mesmo dia).** O diagnóstico acima levou à troca do
> critério de aresta. Existe agora `oulad_vle_bbb_2013j`, em que o nó do
> lado V é o recurso do AVA e o grau mediano do aluno é 33 em vez de 1.
> Nele o Q real fica ~5× acima do nulo, com 4 comunidades de tamanhos
> 941, 480, 322 e 127. **É o dataset a usar para comunidades de alunos.**
> As réplicas nulas dele são `oulad_vle_bbb_2013j_null0..4`.
>
> A comparação é **desta spec**, não da A-08 (a Frente A só gera o
> artefato). `edugraph.data.nullmodel.is_null(bundle)` distingue uma
> réplica de um dataset real sem depender do nome. Sugestão de critério:
> reportar o z-score de Q contra ≥ 5 réplicas, e tratar z < 3 como
> "indistinguível do acaso". A Frente B decide o critério final — isto é
> apontamento, não alteração de escopo.

## Escopo

### Incluído

- `normalized_mutual_information(partition, planted_group)`.
- `purity(partition, planted_group)`.
- `outcome_profile(partition, outcomes)` — distribuição dos quatro
  desfechos por comunidade, em absoluto e relativo à base.
- Comando `edugraph community evaluate`.
- Tratar `planted_group is None` (caso OULAD) sem quebrar: só
  `outcome_profile` se aplica.

### Fora de escopo

- Qualquer uso do desfecho como entrada de algoritmo — é a restrição
  inegociável.
- Teste de significância estatística: fora do escopo do artigo e exigiria
  discussão metodológica que não cabe em 18 páginas.

## Critérios de aceite

- [x] Dada a partição de referência de `synthetic_v1` e o grupo plantado,
      então NMI ≥ 0,8.
- [x] Dada uma partição idêntica ao grupo plantado, então NMI = 1 e
      pureza = 1.
- [x] Dado o OULAD (sem `planted_group`), então `outcome_profile`
      funciona e NMI é pulado sem erro.
- [x] `outcome_profile` tem uma linha por comunidade, com a taxa de cada
      desfecho **e** a taxa da base para comparação.
- [x] Se uma comunidade concentra `Withdrawn` acima da base, isso é
      visível na tabela sem cálculo adicional.

## Testes exigidos

- **Contrato:** `test_outcomes_isolation` confirma que só este módulo (e
  o `evaluate.py` da Frente C) lê os rótulos.
- **Unitários** (já escritos como `xfail`): NMI contra o grupo plantado;
  cobertura de todas as comunidades no perfil de desfecho.

## Arquivos criados ou alterados

- `src/edugraph/community/evaluate.py`.
- `src/edugraph/community/cli.py` — `cmd_evaluate`.
- `tests/community/test_caracterizacao.py`.

## Números medidos (20/09/2026, `synthetic_v1`, Louvain sobre `student_simple`)

**Contra o grupo plantado:** NMI = **0,8188** (critério de aceite: ≥ 0,8)
e pureza = **0,9490**. A topologia sozinha recupera as três áreas
plantadas, apesar dos 35% de ruído do gerador.

**Contra o desfecho histórico:**

| comunidade | tam. | Distinction | Pass | Fail | Withdrawn | mais acima da base |
|---:|---:|---:|---:|---:|---:|---|
| 0 | 39 | 23,1% | 53,8% | 10,3% | 12,8% | Pass (+8,9 p.p.) |
| 1 | 29 | 27,6% | 27,6% | 27,6% | 17,2% | **Fail (+9,2 p.p.)** |
| 2 | 30 | 16,7% | 50,0% | 20,0% | 13,3% | Pass (+5,1 p.p.) |
| base | 98 | 22,4% | 44,9% | 18,4% | 14,3% | — |

A comunidade 1 — a área de exatas — concentra reprovação 9 pontos acima
da base e é a única com `Fail` acima de `Pass`. **É o achado de gestão
pedagógica que o briefing §6.2 pede, obtido sem nenhum classificador.**

Ressalva que vai junto no texto: `synthetic_v1` é sintético, e o gerador
distribui 30% de alunos "em risco" por área — o achado demonstra que o
método **encontra** o padrão quando ele existe, não que ele exista no
OULAD.

## Por que NMI **e** pureza, e não só uma (medido em `synthetic_v2`)

`synthetic_v2` tem os mesmos grupos plantados e a mesma semente de
`synthetic_v1`, com 70% dos alunos reduzidos a uma única matrícula — o
perfil de esparsidade do OULAD. Sobre ela:

| medida | `synthetic_v1` | `synthetic_v2` |
|---|---:|---:|
| pureza | 0,9490 | 0,8642 |
| NMI | 0,8188 | 0,4950 |

**A pureza mal se move; o NMI cai pela metade.** As comunidades
continuam internamente homogêneas (quase todo aluno de uma comunidade
vem do mesmo grupo plantado), mas deixaram de *corresponder* aos grupos:
a partição ficou mais fina, e a pureza sozinha não enxerga isso — ela
sobe quando se divide mais. É a razão de as duas medidas andarem juntas
na tabela de validação, e o texto precisa dizer isso.

Os 0,8642 e 0,8395 batem, na terceira casa, com os números que
`data/fixtures/synthetic_v2/REFERENCE.md` traz — calculados por
`scripts/make_fixtures.py`, por outro caminho e antes desta spec. Um
teste garante que continuem batendo.

## O critério da linha de base nula — a decisão que estava em aberto

A nota da Frente A deixou a escolha para esta spec. **Decidido:**

- Compara-se o Q real com o de **pelo menos cinco réplicas** nulas
  (`MIN_REPLICAS = 5`), usando o mesmo algoritmo e os mesmos parâmetros.
- `z = (Q_real − média(Q_nulo)) / desvio(Q_nulo)`, com desvio amostral.
- **z ≥ 3 → "estrutura"; z < 3 → "indistinguível do acaso"**
  (`Z_THRESHOLD = 3.0`). Com menos de cinco réplicas o veredito é
  `"poucas réplicas"` — nunca um z solto.
- Réplica que não tiver a projeção pedida é **pulada e contada**, não
  tratada como Q = 0: inventar um zero rebaixaria a média do nulo e
  inflaria o z.

Isso **não é teste de significância estatística** (fora de escopo pela
própria spec): é a distância, em desvios, até a distribuição do acaso.

Com os números que a A-08 mediu, o critério classifica `synthetic_v1`
(z = +15,4) como estrutura e o OULAD `module_presentation` (Q real
*abaixo* do nulo) como indistinguível do acaso — que é exatamente o
veredito que o artigo precisa dar.

**Como a Frente B acha as réplicas sem importar a Frente A:** pelo
artefato. `meta.stats["null_model"]["source_dataset"]` identifica a
réplica e a origem dela; nenhuma convenção de nome é assumida, e a
fronteira da ADR-0003 fica intacta.

## Impacto no artigo

**Tabela de validação.** E, se a relação **não** aparecer, isso também é
resultado: o artigo reporta que a estrutura topológica e o desfecho
histórico são dimensões independentes. Registrar a interpretação em
`docs/artigo/decisoes-metodologicas.md`.
