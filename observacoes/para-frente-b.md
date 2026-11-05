# Observações da Frente B — Detecção de Comunidades

Ver as regras em [`README.md`](README.md).

## Abertas

### B-OBS-01 · README cita `null0..2`, mas são cinco réplicas

- **De:** Frente C · **Data:** 26/09/2026
- **Onde:** `docs/specs/frente-b/README.md:100`
- **O quê:** diz `oulad_module_presentation_null0..2`; o disco tem `null0` a
  `null4` (a receita da Frente A usa `--replicas 5`).
- **Como resolver:** trocar para `null0..4`.

### B-OBS-02 · Q = 0,7728 atribuído à projeção inteira, mas veio de amostra

- **De:** Frente C · **Data:** 26/09/2026
- **Onde:** `docs/specs/frente-b/README.md:104`
- **O quê:** o aviso atribui o Q real de 0,7728 à projeção aluno↔aluno de
  `oulad_module_presentation`. Segundo a A-08, o número saiu de uma amostra
  de 3.000 alunos, porque a projeção inteira não cabe na memória. É a mesma
  imprecisão da observação A-OBS-04 da Frente A.
- **Como resolver:** dizer que é a amostra.

### B-OBS-03 · z = +15,4 não se reproduz só com o repositório

- **De:** Frente C · **Data:** 26/09/2026
- **Onde:** `docs/specs/frente-b/B-06-validacao.md:166`
- **O quê:** `community evaluate --null-baseline` sobre as fixtures responde
  "sem réplicas", porque as fixtures não têm réplicas nulas de
  `synthetic_v1`. O z = +15,4 veio de uma rodada da Frente A.
- **Como resolver:** dizer de onde veio o número e como regenerá-lo (quais
  réplicas, com que comando).

### B-OBS-04 · Comandos do README gravam em `data/processed` sem avisar

- **De:** Frente C · **Data:** 26/09/2026
- **Onde:** `docs/specs/frente-b/README.md` (seção "Como rodar a frente
  inteira") e `src/edugraph/community/cli.py:82,89`
- **O quê:** `characterize` e `compare` gravam em `--out`, que por padrão é
  `data/processed`, mesmo quando o `--root` é `data/fixtures`. Está
  documentado no docstring do `cli.py`, mas quem copia os comandos do README
  cria pastas em `data/processed` sem perceber (um revisor fez isso por
  engano durante a revisão final).
- **Como resolver:** citar o `--out` nos comandos do README, ou dizer onde
  eles gravam.

### B-OBS-05 · Informativo: `evaluate.py` ganhou `outcomes_by_group` e `rank_auc`

- **De:** Frente A, laboratório ao vivo · **Data:** 31/10/2026
- **Onde:** `src/edugraph/community/evaluate.py` (funções novas, antes de
  `unknown_outcomes`) e `tests/lab/test_signals.py`.
- **O quê:** a conferência dos sinais de risco de evasão e de talento
  (ADR-0013) cruza grupos de alunos qualquer com o desfecho, e isso mora em
  `evaluate.py` para respeitar a ADR-0008. `outcomes_by_group` é a versão
  de `outcome_profile` para grupos que não são comunidades; `rank_auc` é o
  AUC (Mann-Whitney, empate pela média de postos). Nada existente mudou.
  Medido: no AVA do OULAD inteiro, risco alto → 46% desistentes e 46%
  reprovados (AUC 0,79); na coorte, AUC 0,91.
- **Como resolver:** conferir se concorda com o lugar e a definição; se
  quiser, reaproveitar `rank_auc` na tabela de validação do capítulo 3.

## Resolvidas

Nenhuma ainda.
