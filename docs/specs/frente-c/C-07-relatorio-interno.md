# [C-07] Relatório interno consolidado

**Frente:** C
**Status:** concluída (25/09/2026)

## Objetivo

Consolidar as saídas numa entrega que alguém da coordenação consiga ler —
sem ser do grupo e sem programar.

## Contexto

**Cumpre:** `results/`.
**Consome:** `metrics/`.

**Saída obrigatória** (briefing §6.2): "relatórios de uso exclusivamente
interno da instituição. O sistema não expõe dados a terceiros."

## Dependências

- B-04, B-05, C-03 e C-06, para ter o que consolidar.
- **Neutralizada por:** dá para construir o gerador sobre as métricas das
  fixtures e só trocar `--root` depois.

## Escopo

### Incluído

- `build_internal_report(dataset, roots, out, fmt)` — Markdown, a partir
  dos artefatos em disco.
- Conteúdo: as comunidades e o que as caracteriza; as disciplinas
  críticas e o que significam; os números comparativos.
- **Uma seção de limitações**, dizendo o que a análise **não** diz. Sem
  ela, o documento pode ser lido como ranking de alunos, que é
  exatamente o uso que o trabalho não se propõe a habilitar.
- `figure_centrality_ranking()` — ranking de disciplinas por
  intermediação.
- Comando `edugraph centrality report`.

### Fora de escopo

- Exportar dados individuais de aluno. O relatório fala de comunidades e
  disciplinas, não de pessoas.
- PDF gerado: Markdown basta e é versionável.

## Critérios de aceite

- [x] Dado um dataset com métricas, quando gerar, então sai um Markdown
      em `results/` legível por quem não programa.
- [x] O relatório traz a seção de limitações, com o que a centralidade
      estrutural **não** diz.
- [x] Nenhum aluno aparece nominalmente ou por id — só agregados.
- [x] Dado um dataset sem alguma métrica, então a seção correspondente é
      omitida com nota, em vez de quebrar.
- [x] Rodar duas vezes produz o mesmo arquivo.

## Testes exigidos

- **Unitários:** o relatório é escrito; a seção de limitações está
  presente; dataset incompleto não quebra.
- **Contrato:** nenhum id de aluno no texto gerado — teste simples e que
  protege a restrição de uso interno.

## Arquivos criados ou alterados

- `src/edugraph/centrality/report.py`.
- `src/edugraph/centrality/cli.py` — `cmd_report`.
- `tests/centrality/test_relatorio.py` (novo).

## Impacto no artigo

**Saída obrigatória**: é a evidência de aplicabilidade prática que a
Conclusão precisa citar, e o que sustenta a afirmação de que o trabalho
serve à gestão pedagógica.

## Como ficou (25/09/2026)

- `python -m edugraph centrality report --root data/processed --dataset <ds>`
  grava `results/relatorio-interno-<ds>.md` e a figura 7 em
  `results/figures/`, com caminho relativo.
- **Perfil de partição de disciplinas não entra.** O `profile.csv` da B-05
  caracteriza cada comunidade pelo outro lado do bipartido; numa partição
  de disciplinas, isso são **alunos** (no OULAD, números de matrícula).
  O relatório lista só as disciplinas de cada comunidade. Nas partições
  de alunos entra o perfil (disciplinas características), nunca os
  membros.
- **Guarda antes de gravar:** o texto é varrido atrás de ids de aluno
  (`S` + dígitos) e recusado se algum aparecer; o teste de contrato
  confere também os rótulos.
- A validação (C-06) entra só como taxas agregadas devolvidas por
  `centrality.evaluate` — o relatório não lê `outcomes.csv`.
- Seção sem artefato vira nota em itálico; rodar duas vezes dá o mesmo
  arquivo (sem data nem caminho absoluto).
