# ADR-0012: Acrescentar as granularidades do comportamento ao contrato

**Status:** aceita
**Data:** 2026-09-18
**Decidido por:** o grupo
**Frente:** [A]

## Contexto

A spec A-08 mediu o que ninguém tinha medido: na projeção aluno↔aluno do
OULAD, Q = 0,7728, e réplicas com os mesmos graus e as ligações sorteadas
dão 0,781. **O Q real é menor que o do acaso.** Não há estrutura de
comunidade a reportar com o nó de V sendo a disciplina.

A causa é conhecida e não é do método: **91,8% dos alunos do OULAD
cursam um único módulo**. Com grau 1, a projeção aluno↔aluno é uma união
de cliques quase disjuntas, e a modularidade alta que ela produz é
artefato da esparsidade (Guimerà et al., 2004). O mesmo pipeline, nas
fixtures sintéticas com grupos plantados, acha a estrutura com folga
(z = +15,4 em `synthetic_v1`) — o método funciona; falta sinal na base.

Nenhuma granularidade de matrícula resolve. Medido: com `assessment` na
coorte BBB 2013J a projeção fica com densidade 0,997 e Q = 0,021, porque
todos os alunos fazem as mesmas avaliações.

O OULAD tem uma segunda camada que o projeto não usava: `studentVle`
(~10,6 M linhas) e `vle` (6.364 recursos em 20 tipos). Ali o grau mediano
do aluno é **40**, não 1.

Três fatos dizem que isto **já estava previsto**, e nenhum deles é
interpretação nossa:

- O tema aprovado descreve o bipartido como **"Aluno → Comportamento"** e
  o peso da aresta como "interseção de atributos compartilhados".
- O briefing §8 lista "participação no AVA?" entre os critérios de aresta
  candidatos, e §7 cita "interações no AVA" entre os dados disponíveis.
- `EdgeCriterion` **já contém** `vle_activity` desde o dia 0 (ADR-0007).

O que faltava era o outro lado do par: `Granularity` não tinha valor que
pusesse o recurso do AVA no lado V.

## Decisão

`Granularity` ganha **`vle_site`** e **`vle_activity_type`**. O nó de V
passa a poder ser um recurso do ambiente virtual ou o tipo dele.

`NodeKind` **não muda**: o lado V continua marcado como `"discipline"`.
`kind` identifica o lado do bipartido, não a natureza do nó.

`SCHEMA_VERSION` **não sobe**. A mudança é aditiva: nenhum layout, nome
de coluna ou semântica de campo muda, e todo artefato já gravado continua
válido e legível. É o mesmo critério aplicado a `derive_outcomes()` na
A-06.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Renomear o lado V para algo genérico (`item`, `resource`) | Muda `NodeKind`, `nodes.csv` e todo consumidor das Frentes B e C. Quebraria as duas frentes antes de elas começarem, para ganhar só precisão de nomenclatura — que uma docstring resolve |
| Trocar de base (EdNet, ASSISTments) | Perde o OULAD, que é o citável em periódico (Kuzilek et al., *Scientific Data*, 2017), e custa um ETL do zero. Só se justificaria se o AVA não tivesse sinal — e tem |
| Reportar só o resultado negativo | O trabalho ficaria sem resultado positivo para o objetivo declarado. E é falso dizer que a base não tem estrutura: ela tem, em outro critério de aresta. A saída certa é reportar **as duas coisas** |
| Trocar a métrica de comunidade (CPM, percolação de cliques) | O problema é ausência de vizinhança, não escolha de métrica. Com grau 1, nenhum algoritmo cria relação que o dado não tem |
| Subir `SCHEMA_VERSION` por precaução | Invalidaria artefatos corretos e forçaria regravação sem nenhum ganho. Acrescentar valor a um `Literal` não muda layout nem semântica de campo existente |

## Consequências

**Boas.** O trabalho passa a ter resultado positivo: medido em três
coortes independentes, Q real de 5 a 9 vezes o do nulo, com partições de
tamanho interpretável. As Frentes B e C consomem os artefatos novos **sem
mudar uma linha**, porque `kind`, `nodes.csv` e o layout continuam
idênticos. A configuração por módulo não sai do trabalho — a projeção
disciplina↔disciplina dela funciona e segue servindo a C-03.

**Ruins.** O espaço de configurações cresce de novo, e agora há duas
famílias de granularidade que não se misturam: passar a tabela de
`normalize_vle` com `granularity="module"` produziria silenciosamente um
grafo por módulo sem cliques. Mitigado por `_INCOMPATIVEIS` em
`bipartite.py`, que levanta `ContractError` nomeando a causa nas
combinações sem sentido, e pela exigência de coluna em `discipline_ids`.

Há ainda um custo de leitura: `studentVle` tem 10,6 milhões de linhas, e
a coorte precisa ser aplicada **durante** a leitura em blocos, não
depois. `normalize_vle` recebe `cohort` por isso.

**O que muda no código.** `contracts/types.py` (`Granularity`);
`data/oulad/schema.py` (`id_site` em `studentVle`); `data/oulad/etl.py`
(`normalize_vle`, `VLE_COLUMNS`, `VLE_KEY`); `data/bipartite.py`
(`discipline_ids`, `_INCOMPATIVEIS`); `data/pipeline.py` (escolha da
tabela); `configs/oulad_vle_bbb_2013j.toml`; `tests/data/test_vle.py`.

## Impacto no artigo

**Parágrafo de fundamentação e tabela.** O texto precisa dizer que o
critério de aresta foi escolhido *depois* de medir, e por quê — é o que
transforma uma troca de parâmetro em decisão metodológica defensável. A
tabela de comparação entre critérios de aresta é resultado do capítulo 3.

Vai junto o achado sobre ponderação: sob extração de espinha, a contagem
simples cai **abaixo** do nulo enquanto a alocação de recursos se mantém
acima, porque a primeira premia volume de cliques. Registrado em
`docs/artigo/decisoes-metodologicas.md`.
